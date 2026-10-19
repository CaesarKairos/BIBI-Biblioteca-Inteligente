"""Compatibility is documented or supplied by the API, never guessed from a name.

The catalog is an allowlist, not a claim of access or a Portuguese quality ranking.
An ID must also occur in the school's actual /models response.
"""
SOURCES={
    'openai':'https://developers.openai.com/api/docs/models/gpt-4.1-mini',
    'anthropic':'https://platform.claude.com/docs/en/api/models/list',
    'google':'https://ai.google.dev/gemini-api/docs/models',
    'xai':'https://docs.x.ai/developers/models',
    'groq':'https://console.groq.com/docs/models',
    'openrouter':'https://openrouter.ai/docs/api/api-reference/models/get-models',
}
DOCUMENTED={
    'openai':{'gpt-4.1-mini','gpt-4.1','gpt-4.1-nano'},
    'groq':{'llama-3.3-70b-versatile','llama-3.1-8b-instant','openai/gpt-oss-120b','openai/gpt-oss-20b'},
    'xai':{'grok-4.3','grok-4.6'},
    'google':{'gemini-2.5-flash','gemini-2.5-flash-lite','gemini-2.5-pro'},
}


def describe(provider,row):
    mid=row.get('id') or row.get('name','').removeprefix('models/')
    compatible=mid in DOCUMENTED.get(provider,set())
    if provider=='anthropic':
        compatible=row.get('type')=='model' and row.get('lifecycle','active')=='active'
    elif provider=='google':
        compatible='generateContent' in row.get('supportedGenerationMethods',[]) and (mid in DOCUMENTED['google'] or 'TEXT' in row.get('supportedResponseModalities',[]))
    elif provider=='openrouter':
        architecture=row.get('architecture') or {}
        compatible='text' in architecture.get('input_modalities',[]) and 'text' in architecture.get('output_modalities',[]) and 'max_tokens' in row.get('supported_parameters',[])
        if mid in ('openrouter/auto','openrouter/free','openrouter/bodybuilder','openrouter/healer-alpha'):compatible=False
    retired=row.get('active') is False or row.get('lifecycle') in ('retired','deprecated')
    if retired:
        compatible=False
    return {'compativel':compatible,'retirado':retired,'fonte':SOURCES[provider],
            'tarefas':['chat','insights'] if compatible else [],'portugues':'nao_avaliado',
            'max_saida':row.get('outputTokenLimit') or row.get('max_tokens')}
