"""Administrative service management; secrets never enter a JSON response."""
import json
import math
import time
from flask import current_app,g,session
from werkzeug.exceptions import BadRequest,NotFound
from database.database import db_manager,operation_lock
from services.ai import routing as router,runtime as rt
from services.ai.providers import PROVIDERS,Provider,ProviderError
from services.ai.settings import confirm_identity
from services.contas_service import auditar,limitar


def view():
    router.migrate();reg=router.read();cfg=rt.config();store=current_app.extensions['secrets']
    services=[]
    for name,item in reg['servicos'].items():
        models=item.get('modelos',[])
        pending=item.get('pendente',False)
        ready=any(c['provedor']==name for c in router.candidates())
        state='disponivel' if ready else ('desativado' if not item.get('habilitado') else 'verificacao_necessaria')
        services.append({k:v for k,v in item.items() if k not in ('assinatura','modelos','modelos_pendentes')} |
            {'id':name,'nome':PROVIDERS[name][0],'chave_salva':bool(store.get('ia_'+name)),
             'chave_pendente':pending,'estado':state,'modelos':models,
             'modelos_pendentes':item.get('modelos_pendentes',[])})
    with db_manager.connection() as conn:
        count,total=conn.execute('SELECT COUNT(*),SUM(tokens) FROM IAUtilizacao WHERE instante>?',(int(time.time())-86400,)).fetchone()
        attempts=[dict(zip(['provedor','modelo','estado','operacao','tokens','custo_estimado_usd','custo_informado_usd'],row)) for row in conn.execute('SELECT provedor,modelo,estado,operacao,tokens,custo_estimado_usd,custo_informado_usd FROM IATentativas ORDER BY id DESC LIMIT 20')]
    proof=session.get('ia_confirmacao',{})
    return {'servicos':services,'provedores':[{'id':k,'nome':v[0]} for k,v in PROVIDERS.items()],
        'ativa':cfg['ativa'],'disponivel':rt.availability()['disponivel'],'pode_ativar':router.ready(),
        'limites':{k:cfg[k] for k in ('por_hora','por_dia','concorrencia','max_tokens')},'politica':reg['politica'],
        'migracao':reg.get('migracao'),'pendencias':reg.get('pendencias',[]),'solicitacoes_24h':count,'tokens_24h':total,'tentativas':attempts,
        'identidade_confirmada':proof.get('conta')==g.conta['id'] and time.time()-proof.get('em',0)<600}


def save(name,data):
    router.migrate()
    if name not in PROVIDERS:raise NotFound('Serviço não encontrado.')
    if not isinstance(data,dict) or set(data)-{'chave','senha_atual','habilitado','custos_autorizados','privacidade_revisada','limite_diario'}:
        raise BadRequest('Configuração de serviço inválida.')
    key=data.get('chave')
    if name not in router.read()['servicos'] and not key:raise BadRequest('Informe a chave de API para adicionar o serviço.')
    if key is not None and (not isinstance(key,str) or not 1<=len(key.strip())<=4096):raise BadRequest('Informe uma chave de API válida.')
    for keyname in ('habilitado','custos_autorizados','privacidade_revisada'):
        if keyname in data and type(data[keyname]) is not bool:raise BadRequest('Opção inválida.')
    if 'limite_diario' in data and (type(data['limite_diario']) is not int or not 1<=data['limite_diario']<=10000):raise BadRequest('Limite diário inválido.')
    if key or data.get('custos_autorizados'):confirm_identity(data.get('senha_atual'))
    with operation_lock:
        if key:current_app.extensions['secrets'].set('ia_pendente_'+name,key.strip())
        def apply(reg):
            svc=reg['servicos'].setdefault(name,{'habilitado':True,'custos_autorizados':False,'privacidade_revisada':False,'verificado':False,'modelos':[],'limite_diario':200})
            svc.update({k:v for k,v in data.items() if k not in ('chave','senha_atual')})
            if data.get('custos_autorizados') is False:
                for model in svc.get('modelos',[]):model.pop('legado_autorizado',None)
            if key:svc.update(pendente=True,modelos_pendentes=[])
        router.mutate(apply)
    with db_manager.connection() as conn:
        auditar(conn,'configurar_servico_ia',name)
        if data.get('privacidade_revisada'):auditar(conn,'confirmar_privacidade_ia',name)
        conn.commit()
    rt.runtime()['insights']=None


def remove(name,data):
    if name not in PROVIDERS:raise NotFound('Serviço não encontrado.')
    confirm_identity(data.get('senha_atual'))
    router.mutate(lambda reg:reg['servicos'].pop(name,None))
    for prefix in ('ia_','ia_pendente_','ia_rascunho_'):current_app.extensions['secrets'].set(prefix+name,None)
    with db_manager.connection() as conn:auditar(conn,'remover_servico_ia',name);conn.commit()
    rt.runtime()['insights']=None


def discover(name):
    svc=(router.read() or {}).get('servicos',{}).get(name)
    if svc is None:raise NotFound('Salve o serviço antes de consultar os modelos.')
    limitar('ia-descoberta',str(g.conta['id']),limite=10)
    key=current_app.extensions['secrets'].get(('ia_pendente_' if svc.get('pendente') else 'ia_')+name)
    if not key:raise BadRequest('Salve uma chave de API.')
    cfg=rt.config()|{'provedor':name,'modelo':''}
    with rt.budget('modelos',True,cfg),rt.external():models=Provider(name,key).models()
    with operation_lock:
        def apply(reg):
            current=reg['servicos'].get(name)
            if not current:return
            current_key=current_app.extensions['secrets'].get(('ia_pendente_' if current.get('pendente') else 'ia_')+name)
            if current_key!=key:raise BadRequest('A chave mudou durante a consulta. Tente novamente.')
            field='modelos_pendentes' if current.get('pendente') else 'modelos'
            old={row['id']:row for row in current.get(field,[])}
            updated=[]
            for row in models[:500]:
                previous=old.get(row['id'],{});model=previous|row
                if previous.get('verificado') and not row.get('retirado'):
                    model.update(compativel=True,estado=previous.get('estado','verificado'))
                    model['tarefas']=previous.get('tarefas',['chat','insights'])
                if previous.get('revisado'):
                    for fieldname in ('portugues','tarefas','pausado'):
                        if fieldname in previous:model[fieldname]=previous[fieldname]
                updated.append(model)
            current[field]=updated
        router.mutate(apply)
    return models


def verify(name):
    limitar('ia-verificar-servico',str(g.conta['id']),limite=6)
    svc=(router.read() or {}).get('servicos',{}).get(name)
    if not svc:raise NotFound('Serviço não encontrado.')
    if not svc.get('modelos_pendentes' if svc.get('pendente') else 'modelos'):discover(name)
    # A failed candidate may be explicitly retested, without enabling automatic retry.
    router.mutate(lambda reg:[model.update(retomar_em=0) for model in reg['servicos'][name].get('modelos_pendentes' if svc.get('pendente') else 'modelos',[])])
    choices=router.candidates(preparation=True,only=name,output_tokens=128)
    if not choices:raise BadRequest('Nenhum modelo compatível autorizado. Confira a revisão de privacidade e a permissão de custos deste serviço.')
    item=choices[0];store=current_app.extensions['secrets'];key=store.get(('ia_pendente_' if svc.get('pendente') else 'ia_')+name)
    cfg=rt.config()|{'provedor':name,'modelo':item['id']}
    instance=Provider(name,key)
    try:
        with rt.budget('teste',True,cfg),rt.external():
            g.ai_provider=instance
            answer=''.join(instance.stream(item['id'],'Responda em português. Não use ferramentas.',[{'role':'user','content':'Responda apenas: conexão verificada.'}],128))
            if not answer:raise ProviderError('O serviço não retornou texto.')
    except ProviderError as error:
        def fail(reg):
            current=reg['servicos'].get(name)
            if not current:return
            current['ultimo_erro']=str(error)
            if not svc.get('pendente'):
                if error.code in ('chave','permissao'):current['verificado']=False
                for model in current.get('modelos',[]):
                    if model['id']==item['id']:model.update(estado='indisponivel',retomar_em=int(time.time())+60)
        router.mutate(fail)
        raise
    with operation_lock:
        def apply(reg):
            current=reg['servicos'].get(name)
            if not current:raise BadRequest('O serviço foi removido durante o teste.')
            pending=current.get('pendente')
            current_key=store.get(('ia_pendente_' if pending else 'ia_')+name)
            if current_key!=key:raise BadRequest('A chave mudou durante o teste. Verifique novamente.')
            if pending:
                store.set('ia_'+name,key)
                current['modelos']=current.pop('modelos_pendentes',[])
                current['pendente']=False
                store.set('ia_pendente_'+name,None)
            current.update(verificado=True,assinatura=router.signature(key),ultimo_erro=None)
            for model in current['modelos']:
                if model['id']==item['id']:model.update(verificado=True,estado='verificado',falhas=0,retomar_em=0)
        router.mutate(apply)
    return {'mensagem':'Conexão e geração verificadas. A disponibilidade futura depende do serviço.','modelo':item['id']}


def configure(data):
    router.migrate()
    if not isinstance(data,dict) or set(data)-{'ativa','senha_atual','por_hora','por_dia','concorrencia','max_tokens','politica'}:raise BadRequest('Configuração inválida.')
    cfg=rt.config()
    for field,low,high in [('por_hora',1,500),('por_dia',1,10000),('concorrencia',1,8),('max_tokens',128,4096)]:
        if field in data:
            if type(data[field]) is not int or not low<=data[field]<=high:raise BadRequest('Limite inválido.')
            cfg[field]=data[field]
    if 'ativa' in data:
        if type(data['ativa']) is not bool:raise BadRequest('Opção inválida.')
        if data['ativa']:
            confirm_identity(data.get('senha_atual'))
            if not router.ready():raise BadRequest('Verifique ao menos um serviço autorizado antes de ativar a IA.')
        cfg['ativa']=data['ativa']
    policy=data.get('politica')
    if policy is not None:
        if not isinstance(policy,dict) or set(policy)-set(router.POLICY):raise BadRequest('Política inválida.')
        if policy.get('preferencia','equilibrado') not in ('equilibrado','economia'):raise BadRequest('Preferência inválida.')
        cap=policy.get('max_estimado_usd')
        if cap is not None and (type(cap) not in (float,int) or not math.isfinite(cap) or not 0<=cap<=100):raise BadRequest('Teto estimado inválido.')
        preferred=policy.get('preferidos',{})
        known={name+'/'+m['id'] for name,s in router.read()['servicos'].items() for m in s.get('modelos',[])}
        if not isinstance(preferred,dict) or set(preferred)-{'chat','insights'} or any(v not in known for v in preferred.values()):raise BadRequest('Modelo preferencial inválido.')
        router.mutate(lambda reg:reg['politica'].update(policy))
    with db_manager.connection() as conn:
        conn.execute("INSERT OR REPLACE INTO Configuracoes VALUES ('ia',?)",(json.dumps(cfg),))
        auditar(conn,'configurar_roteamento_ia','instalacao');conn.commit()
    rt.runtime()['insights']=None


def review_model(name,mid,data):
    if not isinstance(data,dict) or set(data)-{'portugues','pausado','tarefas'}:raise BadRequest('Revisão inválida.')
    if 'portugues' in data and data['portugues'] not in ('nao_avaliado','aprovado','rejeitado'):raise BadRequest('Avaliação inválida.')
    if 'pausado' in data and type(data['pausado']) is not bool:raise BadRequest('Opção inválida.')
    if 'tarefas' in data and (not isinstance(data['tarefas'],list) or any(t not in ('chat','insights') for t in data['tarefas'])):raise BadRequest('Tarefa inválida.')
    def apply(reg):
        model=next((m for m in reg['servicos'].get(name,{}).get('modelos',[]) if m['id']==mid),None)
        if model is None:raise NotFound('Modelo não encontrado.')
        model.update(data,revisado=True)
    router.mutate(apply)
    rt.runtime()['insights']=None
    with db_manager.connection() as conn:auditar(conn,'revisar_modelo_ia',name+'/'+mid);conn.commit()
