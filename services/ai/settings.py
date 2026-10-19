"""Preparação isolada da configuração em uso, sem chamadas externas implícitas."""
import json
import time
from flask import current_app,g,session
from werkzeug.exceptions import BadRequest,Forbidden
from database.database import db_manager
from utils.auth import verificar_senha_admin
from services.contas_service import auditar
from services.ai import runtime as rt
from services.ai.providers import PROVIDERS

def confirm_identity(password):
    if password:
        if not verificar_senha_admin(password):
            raise Forbidden('Confira sua senha atual para proteger a chave da biblioteca.')
        session['ia_confirmacao']={'conta':g.conta['id'],'em':int(time.time())}
    proof=session.get('ia_confirmacao',{})
    if proof.get('conta')!=g.conta['id'] or time.time()-proof.get('em',0)>600:
        raise Forbidden('Confirme sua senha uma vez para configurar a IA. A confirmação vale por dez minutos nesta sessão.')

def save(data):
    from services.ai import routing
    if routing.read() is not None:
        if data=={'ativa':False}:
            from services.ai.connections import configure
            return configure(data)
        raise BadRequest('Use Serviços conectados nas Configurações. A seleção de modelos agora é automática.')
    active=rt.config();cfg=rt.draft()
    if set(data)-set(rt.DEFAULTS)-{'chave','remover_chave','senha_atual','descartar'}:
        raise BadRequest('Configuração desconhecida.')
    for name in ('ativa','privacidade_revisada','remover_chave','descartar'):
        if name in data and type(data[name]) is not bool:raise BadRequest('Opção inválida.')
    for name,low,high in [('por_hora',1,500),('por_dia',1,10000),('concorrencia',1,8),('max_tokens',128,4096)]:
        if name in data and (type(data[name]) is not int or not low<=data[name]<=high):raise BadRequest('Limite inválido.')
    if data.get('provedor',cfg['provedor']) not in PROVIDERS:raise BadRequest('Escolha um provedor disponível.')
    if 'modelo' in data and (not isinstance(data['modelo'],str) or len(data['modelo'])>200):raise BadRequest('Modelo inválido.')
    key=data.get('chave')
    if key is not None and (not isinstance(key,str) or not 1<=len(key.strip())<=4096):raise BadRequest('Informe uma chave válida.')
    if key or data.get('remover_chave') or data.get('ativa'):
        confirm_identity(data.get('senha_atual'))
    if data.get('descartar'):
        cfg=active.copy()
        current_app.extensions['secrets'].set('ia_rascunho_'+cfg['provedor'],None)
    new=cfg|{k:v for k,v in data.items() if k in rt.DEFAULTS and k!='ativa'}
    if new['provedor']!=cfg['provedor']:
        if 'modelo' not in data:new['modelo']=''
        if 'privacidade_revisada' not in data:new['privacidade_revisada']=False
    store=current_app.extensions['secrets']
    if key:store.set('ia_rascunho_'+new['provedor'],key.strip())
    if data.get('remover_chave'):
        store.set('ia_rascunho_'+new['provedor'],'')
        if new['provedor']==active['provedor']:
            store.set('ia_'+new['provedor'],None);active['ativa']=False
    if data.get('ativa'):
        check=rt.verification(new,True)
        if not rt.credential(new,True) or not new['modelo'] or not check or not check['funcionou']:
            raise BadRequest('Escolha o modelo e teste a conexão antes de ativar para a biblioteca.')
        if not new['privacidade_revisada']:
            raise BadRequest('Antes de ativar, confirme que a escola verificou as condições de uso e privacidade do provedor.')
        store.set('ia_'+new['provedor'],rt.credential(new,True))
        active=new|{'ativa':True}
    elif data.get('ativa') is False:
        active['ativa']=False
    with db_manager.connection() as conn:
        conn.execute("INSERT OR REPLACE INTO Configuracoes VALUES ('ia_rascunho',?)",(json.dumps(new|{'ativa':False}),))
        conn.execute("INSERT OR REPLACE INTO Configuracoes VALUES ('ia',?)",(json.dumps(active),))
        auditar(conn,'ativar_ia' if data.get('ativa') else 'preparar_ia',new['provedor'])
        if data.get('ativa'):auditar(conn,'confirmar_privacidade_ia',new['provedor'])
        conn.commit()
    rt.runtime()['insights']=None

def view():
    cfg=rt.draft();active=rt.config();check=rt.verification(cfg,True)
    configured=bool(rt.credential(cfg,True))
    verifying=rt.fingerprint(cfg,True) in rt.runtime().get('verifying',set())
    if verifying:message='Verificando a conexão…'
    elif check and check['funcionou']:message='Conexão verificada. Pronto para ativar.'
    elif check:message='Não foi possível conectar. Confira sua chave e tente novamente.'
    elif not configured:message='Configure um provedor para começar.'
    elif not cfg['modelo']:message='Chave salva. Escolha um modelo.'
    else:message='Modelo escolhido. Teste a conexão antes de ativar.'
    available=rt.availability()
    same=rt.fingerprint(cfg,True)==rt.fingerprint(active)
    if available['disponivel'] and same:message='IA ativa para a biblioteca'
    with db_manager.connection() as conn:
        count,tokens=conn.execute('SELECT COUNT(*),SUM(tokens) FROM IAUtilizacao WHERE instante>?',(int(time.time())-86400,)).fetchone()
    return cfg|{'ativa':active['ativa'],'disponivel':available['disponivel'],'estado':available['estado'],
        'mensagem':message,'chave_configurada':configured,'teste':check,'verificando':verifying,
        'pode_ativar':bool(check and check['funcionou'] and configured and cfg['modelo']),
        'em_uso':{'provedor':active['provedor'],'modelo':active['modelo']},
        'provedores':[{'id':k,'nome':v[0]} for k,v in PROVIDERS.items()],
        'solicitacoes_24h':count,'tokens_informados_24h':tokens}
