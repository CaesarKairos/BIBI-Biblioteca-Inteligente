"""Estado efêmero por instalação: conversas expiram, sem persistir no backup."""
import hashlib
import json
import secrets
import threading
import time
from contextlib import contextmanager
from flask import current_app, g
from werkzeug.exceptions import BadRequest, Forbidden, ServiceUnavailable, TooManyRequests, NotFound, Conflict
from database.database import db_manager, operation_lock
from services.ai.providers import Provider

DEFAULTS = {'ativa':False,'provedor':'openai','modelo':'','por_hora':30,'por_dia':200,
            'concorrencia':2,'max_tokens':800,'privacidade_revisada':False}

def config():
    with db_manager.connection() as conn:
        row=conn.execute("SELECT valor FROM Configuracoes WHERE chave='ia'").fetchone()
    return DEFAULTS | (json.loads(row[0]) if row else {})

def runtime():
    return current_app.extensions.setdefault('ai_runtime', {'lock':threading.RLock(),'active':0,'conversations':{},'insights':None})

def draft():
    with db_manager.connection() as conn:
        row=conn.execute("SELECT valor FROM Configuracoes WHERE chave='ia_rascunho'").fetchone()
    return DEFAULTS | (json.loads(row[0]) if row else config())

def credential(cfg, preparation=False):
    store=current_app.extensions['secrets']
    if preparation:
        key=store.get('ia_rascunho_'+cfg['provedor'])
        if key is not None:
            return key
    return store.get('ia_'+cfg['provedor'])

def fingerprint(cfg, preparation=False):
    return hashlib.sha256(json.dumps([cfg['provedor'],cfg['modelo'],credential(cfg,preparation)],ensure_ascii=False).encode()).hexdigest()

def verification(cfg, preparation=False):
    with db_manager.connection() as conn:
        row=conn.execute("SELECT valor FROM Configuracoes WHERE chave='ia_validacoes'").fetchone()
    return (json.loads(row[0]) if row else {}).get(fingerprint(cfg,preparation))

def record_verification(cfg, success, message, preparation=False, signature=None):
    with db_manager.connection() as conn:
        row=conn.execute("SELECT valor FROM Configuracoes WHERE chave='ia_validacoes'").fetchone()
        checks=json.loads(row[0]) if row else {}
        checks[signature or fingerprint(cfg,preparation)]={'funcionou':success,'mensagem':message,'instante':int(time.time())}
        checks=dict(sorted(checks.items(),key=lambda pair:pair[1]['instante'])[-20:])
        conn.execute("INSERT OR REPLACE INTO Configuracoes VALUES ('ia_validacoes',?)",(json.dumps(checks),));conn.commit()

def availability(cfg=None):
    cfg=cfg or config()
    from services.ai import routing
    registry=routing.read()
    if registry is not None:
        usable=routing.ready()
        state='pronta' if cfg['ativa'] and usable else 'desativada'
        if not registry['servicos']:state='nao_configurada'
        elif cfg['ativa'] and not usable:state='indisponivel'
        return {'estado':state,'disponivel':bool(cfg['ativa'] and usable),'ativa':cfg['ativa']}
    check=verification(cfg)
    state='desativada'
    if not credential(cfg) or not cfg['modelo']:state='nao_configurada'
    elif fingerprint(cfg) in runtime().get('verifying',set()):state='verificando'
    elif cfg['ativa']:state='pronta' if check and check['funcionou'] else 'indisponivel'
    return {'estado':state,'disponivel':state=='pronta','ativa':cfg['ativa']}

def require_ready():
    if not availability()['disponivel']:
        raise ServiceUnavailable('A BIBI está sem uma integração de IA disponível. A biblioteca continua funcionando normalmente.')

def provider(cfg, preparation=False):
    key=credential(cfg,preparation)
    if not key or not cfg['modelo']:
        raise ServiceUnavailable('A BIBI está sem configuração de IA. A biblioteca continua disponível.')
    instance=Provider(cfg['provedor'],key)
    g.ai_provider=instance
    return instance

@contextmanager
def external():
    # guard() prende este RLock durante a requisição. Rede não pode bloquear circulação.
    held=getattr(g,'operation_locked',False)
    if held:
        g.operation_locked=False;operation_lock.release()
    try:
        yield
    finally:
        if held:
            operation_lock.acquire();g.operation_locked=True

@contextmanager
def budget(operation, preparation=False, cfg=None):
    cfg=cfg or config()
    if not preparation:
        require_ready()
    state=runtime();now=int(time.time())
    with operation_lock,state['lock']:
        if state['active']>=cfg['concorrencia']:
            raise TooManyRequests('A BIBI está atendendo outras conversas. Tente em instantes.')
        with db_manager.connection() as conn:
            hour=conn.execute('SELECT COUNT(*) FROM IAUtilizacao WHERE conta_id=? AND instante>?',(g.conta['id'],now-3600)).fetchone()[0]
            day=conn.execute('SELECT COUNT(*) FROM IAUtilizacao WHERE instante>?',(now-86400,)).fetchone()[0]
            if hour>=cfg['por_hora'] or day>=cfg['por_dia']:
                raise TooManyRequests('Limite de utilização da biblioteca atingido.')
            conn.execute('DELETE FROM IAUtilizacao WHERE instante<?',(now-90*86400,))
            use=conn.execute('INSERT INTO IAUtilizacao(conta_id,instante,operacao,provedor,modelo) VALUES (?,?,?,?,?)',
                (g.conta['id'],now,operation,cfg['provedor'],cfg['modelo'])).lastrowid
            conn.commit()
        state['active']+=1
    completed=False
    g.ai_use_id=use
    try:
        yield cfg
        completed=True
    finally:
        with state['lock']:
            state['active']-=1
        with db_manager.connection() as conn:
            instance=getattr(g,'ai_provider',None)
            usage=instance.usage if instance else {}
            tokens=usage.get('total_tokens') or usage.get('totalTokenCount')
            if tokens is None and ('input_tokens' in usage or 'output_tokens' in usage):
                tokens=usage.get('input_tokens',0)+usage.get('output_tokens',0)
            if instance:
                state['provider_limits']=instance.limits
            selected=getattr(g,'ai_selected',{})
            conn.execute('UPDATE IAUtilizacao SET estado=?,tokens=?,provedor=?,modelo=? WHERE id=?',('concluida' if completed else 'interrompida',tokens,selected.get('provedor',cfg['provedor']),selected.get('id',cfg['modelo']),use));conn.commit()

def owner():
    from flask import session
    return (g.conta['id'],hashlib.sha256(session['sid'].encode()).hexdigest())

def conversation(cid=None):
    state=runtime();now=time.monotonic()
    with state['lock']:
        for key,item in list(state['conversations'].items()):
            if now-item['touched']>1800 and not item['busy']:
                del state['conversations'][key]
        if cid:
            item=state['conversations'].get(cid)
            if not item or item['owner']!=owner():
                raise NotFound('Conversa não encontrada. Inicie uma nova conversa.')
        else:
            if len(state['conversations'])>=200:
                raise TooManyRequests('Limite de conversas abertas atingido.')
            if sum(item['owner'][0]==g.conta['id'] for item in state['conversations'].values())>=10:
                raise TooManyRequests('Encerre uma das suas conversas antes de iniciar outra.')
            cid=secrets.token_urlsafe(24)
            item={'owner':owner(),'history':[],'touched':now,'busy':False}
            state['conversations'][cid]=item
        if item['busy']:
            raise Conflict('Aguarde a resposta atual terminar.')
        item['busy']=True;item['touched']=now
        return cid,item
