"""Controles determinísticos que não dependem da obediência do LLM."""
import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyDecision:
    blocked: bool = False
    response: str = ''
    reason: str = ''


def normalize(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    text = ''.join(char for char in unicodedata.normalize('NFKD', text)
                   if not unicodedata.combining(char) and unicodedata.category(char) != 'Cf')
    return re.sub(r'\s+', ' ', text).strip()


INJECTION_PATTERNS = (
    r'ignor(e|a|ar).{0,35}(instruc|regr|prompt|mensage)',
    r'(revele|mostre|copie|repita|imprima|transcreva|resuma|traduza).{0,45}(system prompt|prompt do sistema|instruc.{0,8}intern)',
    r'(finja|aja|assuma|ative|habilite).{0,40}(sem regras|sem restric|modo desenvolvedor|developer mode|dan\b)',
    r'(instruc|regr).{0,25}(anteriores|acima).{0,20}(nao valem|foram cancel|devem ser ignor)',
    r'(codifique|encode|base64|rot13).{0,35}(prompt|instruc.{0,8}intern)',
    r'(nova|prioridade maior|mais importante).{0,20}(instruc|regra)',
    r'ignore.{0,35}(previous|prior|system).{0,20}(instruction|message|prompt)',
    r'(reveal|show|print|repeat|translate|encode|summarize).{0,40}(system prompt|hidden instruction|system message)',
    r'(act|pretend|roleplay).{0,35}(without rules|unrestricted|developer mode|as dan)',
    r'(quais|qual|conte).{0,30}(suas instrucoes|regras internas|prompt interno)',
    r'prioridade.{0,25}(sobre|acima).{0,35}(defin|instruc|comport|mensage)',
    r'(teste interno|modo de diagnostico).{0,80}(restric|nao se aplic|prioridade|camada publica)',
    r'(assuma|ative|modo|papel).{0,30}[a-z0-9]*_test_core',
    r'nao avalie.{0,20}(intencao|mensagem)',
)

ACTION = r'(fac|escrev|elabor|produz|ger|resolv|complet|respond|entreg|mont|write|solve|complete|produce|do)\w*'
DELIVERABLE = r'(trabalho|redacao|resenha|resumo|atividade|dever|lista|exercici|prova|avaliacao|homework|essay|assignment|exam|worksheet)\w*'
COMPLETION = r'(inteir|complet|pront|por mim|para entregar|so a resposta|sem explicar|nota maxima|entire|finished|for me|submit|answers only)\w*'
OUT_OF_SCOPE = r'(matemat|fisic|quimic|biolog|geograf|programa|codigo|equacao|calculo|math|physics|chemistry|coding)\w*'


def evaluate(message):
    text = normalize(message)
    if any(re.search(pattern, text) for pattern in INJECTION_PATTERNS):
        return PolicyDecision(
            True,
            'Não posso ignorar, revelar ou transformar minhas instruções internas. '
            'Posso ajudar você a encontrar um livro no catálogo ou conversar sobre uma leitura.',
            'prompt_injection',
        )

    guided_help = (re.search(r'(como posso|ajude.?me|me ajude).{0,45}(estrutur|revis|entend|comec)', text)
                   and re.search(r'(sem voce.{0,20}por mim|nao fac.{0,20}por mim|minha tentativa)', text))
    if guided_help:
        return PolicyDecision()

    asks_action = re.search(ACTION, text)
    has_deliverable = re.search(DELIVERABLE, text)
    wants_finished = re.search(COMPLETION, text)
    if has_deliverable and (asks_action or wants_finished):
        if re.search(OUT_OF_SCOPE, text):
            return PolicyDecision(
                True,
                'Essa atividade está fora da finalidade da BIBI, e não posso resolvê-la para entrega. '
                'Sou voltada à biblioteca e à mediação de leitura.',
                'out_of_scope_assignment',
            )
        return PolicyDecision(
            True,
            'Posso ajudar você a construir a atividade, mas não entregar uma versão pronta. '
            'Podemos identificar temas, formular perguntas, montar uma estrutura ou revisar uma tentativa sua.',
            'school_assignment',
        )
    return PolicyDecision()
