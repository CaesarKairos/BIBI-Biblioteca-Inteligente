"""Transportes REST oficiais. Endpoints fixos, sem retries ou fallback pago."""
import json
import time
from urllib.parse import quote
import requests

PROVIDERS = {
    'openai': ('OpenAI', 'https://api.openai.com/v1'),
    'anthropic': ('Anthropic', 'https://api.anthropic.com/v1'),
    'google': ('Google Gemini', 'https://generativelanguage.googleapis.com/v1beta'),
    'xai': ('xAI — Grok', 'https://api.x.ai/v1'),
    'groq': ('GroqCloud', 'https://api.groq.com/openai/v1'),
    'openrouter': ('OpenRouter', 'https://openrouter.ai/api/v1'),
}

class ProviderError(Exception):
    def __init__(self, message, code='provedor', safe_retry=False):
        super().__init__(message)
        self.code = code
        # Only an explicit HTTP rejection establishes that generation did not start.
        self.safe_retry = safe_retry

class Provider:
    def __init__(self, name, key):
        self.name, self.key = name, key
        self.base = PROVIDERS[name][1]
        self.usage = {}
        self.limits = {}

    def request(self, method, path, **kwargs):
        headers = {'Authorization': 'Bearer '+self.key}
        if self.name == 'anthropic':
            headers = {'x-api-key': self.key, 'anthropic-version': '2023-06-01'}
        elif self.name == 'google':
            headers = {'x-goog-api-key': self.key}
        try:
            response = requests.request(method, self.base+path, headers=headers,
                                        timeout=(5, 35), allow_redirects=False, **kwargs)
        except requests.RequestException:
            raise ProviderError('O provedor demorou ou a rede está indisponível.', 'rede') from None
        if not 200 <= response.status_code < 300:
            status = response.status_code
            response.close()
            code, message = {
                401: ('chave', 'Chave inválida. Revise a credencial.'),
                403: ('permissao', 'A chave não possui permissão para esta operação.'),
                404: ('modelo', 'Modelo ou recurso indisponível.'),
                429: ('limite', 'Limite de utilização ou saldo do provedor atingido.'),
            }.get(status, ('provedor', 'O provedor não concluiu a solicitação. Confira o modelo e o plano.'))
            raise ProviderError(message, code, safe_retry=status in (401,403,404,429))
        self.limits = {k:v for k,v in response.headers.items() if k.lower().startswith(('x-ratelimit-', 'anthropic-ratelimit-'))}
        return response

    def models(self):
        result, after = [], None
        started=time.monotonic()
        for _ in range(20):
            if time.monotonic()-started>45:
                raise ProviderError('Tempo máximo para listar modelos atingido.', 'tempo')
            params = {}
            if after:
                params = {'pageToken': after} if self.name == 'google' else {'after_id': after}
            with self.request('GET', '/models', params=params) as r:
                data = r.json()
            rows = data.get('models', []) if self.name == 'google' else data.get('data', [])
            for row in rows:
                if self.name == 'google' and 'generateContent' not in row.get('supportedGenerationMethods', []):
                    continue
                from services.ai.model_catalog import describe
                result.append(describe(self.name, row) | {'id': row.get('id') or row['name'].removeprefix('models/'),
                               'nome': row.get('display_name') or row.get('displayName') or row.get('name') or row['id'],
                               'estado': 'listado; geração ainda não verificada',
                               'precos': row.get('pricing'), 'contexto': row.get('context_length') or row.get('context_window') or row.get('inputTokenLimit') or row.get('max_input_tokens')})
            after = data.get('nextPageToken') if self.name == 'google' else (data.get('last_id') if data.get('has_more') else None)
            if not after:
                break
        return sorted(result, key=lambda x: x['id'])

    def stream(self, model, system, messages, max_tokens):
        path, body = '/chat/completions', {'model': model, 'messages': [{'role':'system','content':system}]+messages, 'stream':True}
        if self.name in ('openai', 'xai'):
            path = '/responses'
            body = {'model': model, 'instructions': system, 'input': messages, 'max_output_tokens': max_tokens, 'stream':True, 'store':False}
            if self.name == 'xai':
                body.pop('instructions')
                body['input']=[{'role':'system','content':system}]+messages
        elif self.name == 'anthropic':
            path, body = '/messages', {'model':model, 'system':system, 'messages':messages, 'max_tokens':max_tokens, 'stream':True}
        elif self.name == 'google':
            path = '/models/'+quote(model, safe='')+':streamGenerateContent?alt=sse'
            body = {'systemInstruction': {'parts':[{'text':system}]}, 'contents':[
                {'role':'model' if m['role']=='assistant' else 'user', 'parts':[{'text':m['content']}]} for m in messages],
                'generationConfig': {'maxOutputTokens':max_tokens}}
        else:
            body['max_tokens'] = max_tokens
            if self.name == 'openrouter':
                body['provider'] = {'allow_fallbacks':False, 'data_collection':'deny'}
        start = time.monotonic()
        complete = False
        characters = 0
        try:
            with self.request('POST', path, json=body, stream=True) as r:
                for line in r.iter_lines(chunk_size=1):
                    if time.monotonic()-start > 60:
                        raise ProviderError('Tempo máximo de resposta atingido.', 'tempo')
                    if not line or not line.startswith(b'data:'):
                        continue
                    raw = line[5:].strip()
                    if raw == b'[DONE]':
                        complete = True
                        break
                    event = json.loads(raw)
                    usage = event.get('usage') or event.get('response',{}).get('usage') or event.get('message',{}).get('usage') or event.get('usageMetadata') or {}
                    self.usage.update(usage)
                    if event.get('error') or event.get('type') == 'error':
                        raise ProviderError('O provedor interrompeu a resposta.')
                    text = ''
                    if self.name in ('openai','xai'):
                        if event.get('type') == 'response.completed':
                            complete = True
                        if event.get('type') == 'response.output_text.delta':
                            text = event.get('delta','')
                        if event.get('type') in ('response.failed','response.incomplete'):
                            raise ProviderError('A resposta foi interrompida pelo provedor.')
                    elif self.name == 'anthropic':
                        if event.get('type') == 'message_stop':
                            complete = True
                        if event.get('delta',{}).get('type') == 'text_delta':
                            text = event['delta'].get('text','')
                    elif self.name == 'google':
                        complete = any(c.get('finishReason')=='STOP' for c in event.get('candidates',[])) or complete
                        text = ''.join(p.get('text','') for c in event.get('candidates',[]) for p in c.get('content',{}).get('parts',[]) if not p.get('thought'))
                    else:
                        text = ''.join(c.get('delta',{}).get('content') or '' for c in event.get('choices',[]))
                    if text:
                        characters += len(text)
                        if characters>20000:
                            raise ProviderError('Limite de tamanho da resposta atingido.', 'limite')
                        yield text
                if not complete:
                    raise ProviderError('A conexão terminou antes de confirmar uma resposta completa.', 'interrompida')
        except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError):
            raise ProviderError('Não foi possível ler a resposta do provedor.', 'rede') from None
