"""Registry, deterministic routing and conservative failover. No prompts in audit logs."""
import hashlib
import json
import math
import time
from contextlib import closing
from flask import current_app,g
from werkzeug.exceptions import BadRequest,ServiceUnavailable,TooManyRequests
from database.database import db_manager,operation_lock
from services.ai.providers import Provider,ProviderError,PROVIDERS

KEY='ia_servicos_v1'
POLICY={'preferencia':'equilibrado','max_estimado_usd':None,'preferidos':{}}


def signature(key):
    return hashlib.sha256((key or '').encode()).hexdigest()


def read():
    with db_manager.connection() as conn:
        row=conn.execute('SELECT valor FROM Configuracoes WHERE chave=?',(KEY,)).fetchone()
    return json.loads(row[0]) if row else None


def mutate(action):
    with operation_lock,db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT valor FROM Configuracoes WHERE chave=?',(KEY,)).fetchone()
        value=json.loads(row[0]) if row else {'versao':1,'servicos':{},'politica':POLICY.copy()}
        result=action(value)
        conn.execute('INSERT OR REPLACE INTO Configuracoes VALUES (?,?)',(KEY,json.dumps(value)))
        conn.commit()
        from services.ai import runtime as rt
        state=rt.runtime()
        with state['lock']:state['routing_revision']=state.get('routing_revision',0)+1
        return result


def migrate():
    """Idempotent. Keep active and draft secrets in place, with no network calls."""
    if read() is not None:return
    from services.ai import runtime as rt
    active=rt.config();draft=rt.draft();store=current_app.extensions['secrets']
    def apply(reg):
        for cfg,preparation in [(active,False),(draft,True)]:
            name=cfg['provedor'];key=rt.credential(cfg,preparation)
            if name not in PROVIDERS:
                reg.setdefault('pendencias',[]).append('Serviço anterior não reconhecido. Cadastre novamente a integração; as credenciais originais foram preservadas.')
                continue
            if not key:continue
            check=rt.verification(cfg,preparation)
            service=reg['servicos'].setdefault(name,{'habilitado':True,'custos_autorizados':False,'privacidade_revisada':False,'modelos':[],'limite_diario':200})
            if not preparation or not store.get('ia_'+name):
                if not store.get('ia_'+name):store.set('ia_'+name,key)
                service.update(assinatura=signature(key),privacidade_revisada=cfg['privacidade_revisada'])
                if cfg['modelo'] and not service['modelos']:
                    verified=bool(check and check['funcionou'])
                    service['modelos']=[{'id':cfg['modelo'],'nome':cfg['modelo'],'compativel':verified,
                        'tarefas':['chat','insights'] if verified else [],'portugues':'nao_avaliado',
                        'verificado':verified,'estado':'verificado' if verified else 'pendente',
                        'legado_autorizado':bool(verified and active['ativa'] and not preparation)}]
                    service['verificado']=verified
            if preparation and signature(key)!=service.get('assinatura'):
                store.set('ia_pendente_'+name,key)
                service['pendente']=True
        for name in PROVIDERS:
            key=store.get('ia_'+name)
            pending=store.get('ia_rascunho_'+name)
            if name not in reg['servicos'] and (key or pending):
                service={'habilitado':True,'custos_autorizados':False,'privacidade_revisada':False,'verificado':False,'modelos':[],'limite_diario':200}
                if key:service['assinatura']=signature(key)
                if pending:
                    store.set('ia_pendente_'+name,pending)
                    service.update(pendente=True,modelos_pendentes=[])
                reg['servicos'][name]=service
        reg['migracao']='Credenciais preservadas. Serviços sem teste válido precisam de verificação.'
    mutate(apply)
    if read().get('pendencias') and active['ativa']:
        active['ativa']=False
        with db_manager.connection() as conn:
            conn.execute("INSERT OR REPLACE INTO Configuracoes VALUES ('ia',?)",(json.dumps(active),));conn.commit()


def estimate(model,input_tokens,output_tokens):
    prices=model.get('precos') or {}
    try:
        a,b=float(prices['prompt']),float(prices['completion'])
        other=[float(v) for k,v in prices.items() if k not in ('prompt','completion') and v not in (None,'')]
        if any(not math.isfinite(v) or v<0 for v in [a,b,*other]):return None
        # Additional request/image/etc charges prevent treating a model as free.
        if any(other):return None
        return input_tokens*a+output_tokens*b
    except (KeyError,ValueError,TypeError):return None


def candidates(task='chat',input_tokens=0,output_tokens=800,preparation=False,only=None):
    reg=read()
    if reg is None:
        # Compatibility for installations not yet migrated; one previously approved model.
        from services.ai import runtime as rt
        cfg=rt.config();check=rt.verification(cfg)
        if check and check['funcionou'] and rt.credential(cfg):
            return [{'provedor':cfg['provedor'],'id':cfg['modelo'],'legado':True,'motivo':'Configuração anterior verificada','estimativa':None}]
        return []
    result=[];now=int(time.time());store=current_app.extensions['secrets']
    with db_manager.connection() as conn:
        counts=dict(conn.execute('SELECT provedor,COUNT(*) FROM IATentativas WHERE instante>? GROUP BY provedor',(now-86400,)))
    for name,svc in reg['servicos'].items():
        if only and name!=only:continue
        if not svc.get('habilitado') or not svc.get('privacidade_revisada'):continue
        if not preparation and not svc.get('verificado'):continue
        key=store.get(('ia_pendente_' if preparation and svc.get('pendente') else 'ia_')+name)
        if not key or (not preparation and signature(key)!=svc.get('assinatura')):continue
        if counts.get(name,0)>=svc.get('limite_diario',200):continue
        for model in svc.get('modelos_pendentes' if preparation and svc.get('pendente') else 'modelos',[]):
            if not model.get('compativel') or task not in model.get('tarefas',[]) or model.get('portugues')=='rejeitado':continue
            if model.get('pausado') or model.get('retomar_em',0)>now:continue
            if model.get('contexto') and model['contexto']<input_tokens+output_tokens:continue
            if model.get('max_saida') and model['max_saida']<output_tokens:continue
            cost=estimate(model,input_tokens,output_tokens)
            if not svc.get('custos_autorizados') and cost!=0 and not model.get('legado_autorizado'):continue
            ceiling=reg['politica'].get('max_estimado_usd')
            if ceiling is not None and (cost is None or cost>ceiling):continue
            item=dict(model,provedor=name,estimativa=cost)
            preferred=reg['politica'].get('preferidos',{}).get(task)==name+'/'+model['id']
            latency=model.get('primeiro_token_ms')
            # No invented Portuguese scores. A school's recorded review is categorical.
            quality=0 if model.get('portugues')=='aprovado' else 1
            cost_order=(cost is None,cost or 0)
            speed_order=(latency is None,latency or 0)
            economy=task=='insights' or reg['politica'].get('preferencia')=='economia'
            item['_rank']=(not preferred,quality,model.get('falhas',0),*(cost_order+speed_order if economy else speed_order+cost_order),name,model['id'])
            item['motivo']='Preferência administrativa' if preferred else ('Custo estimado, falhas e latência observada' if economy else 'Falhas, latência observada e custo estimado')
            result.append(item)
    return sorted(result,key=lambda item:item['_rank'])


def ready():
    return bool(candidates())


def cache_signature():
    """Operational timings must not turn the dashboard cache into a paid loop."""
    reg=read()
    if reg is None:return None
    fields=('id','compativel','tarefas','portugues','pausado','precos','contexto','max_saida')
    return {'politica':reg['politica'],'servicos':{
        name:{key:svc.get(key) for key in ('habilitado','custos_autorizados','privacidade_revisada','assinatura')} |
             {'modelos':[{key:model.get(key) for key in fields} for model in svc.get('modelos',[])]}
        for name,svc in reg['servicos'].items()}}


def allowed(item):
    from services.ai import runtime as rt
    if not rt.config()['ativa']:return False
    revision=rt.runtime().get('routing_revision',0)
    cache=getattr(g,'ai_authorization_cache',{})
    cache_key=(item['provedor'],item['id'],revision)
    if cache_key in cache:return cache[cache_key]
    reg=read()
    if reg is None:return rt.availability()['disponivel']
    svc=reg['servicos'].get(item['provedor'],{})
    key=current_app.extensions['secrets'].get('ia_'+item['provedor'])
    if not svc.get('habilitado') or not svc.get('verificado') or not svc.get('privacidade_revisada') or signature(key)!=svc.get('assinatura'):return False
    model=next((m for m in svc.get('modelos',[]) if m['id']==item['id']),None)
    if not model or model.get('pausado') or not model.get('compativel'):return False
    if not svc.get('custos_autorizados') and estimate(model,1,1)!=0 and not model.get('legado_autorizado'):return False
    cap=reg['politica'].get('max_estimado_usd')
    result=cap is None or (item.get('estimativa') is not None and item['estimativa']<=cap)
    cache[cache_key]=result;g.ai_authorization_cache=cache
    return result


def tokens(usage):
    return usage.get('total_tokens') or usage.get('totalTokenCount') or (usage.get('input_tokens',0)+usage.get('output_tokens',0) or None)


def stream(task,system,messages,max_tokens):
    from services.ai import runtime as rt
    size=math.ceil((len(system)+sum(len(m['content']) for m in messages))/3)
    choices=candidates(task,size,max_tokens)
    if not choices:raise ServiceUnavailable('Nenhum modelo autorizado está disponível para esta solicitação.')
    attempts=0;last_error=None
    for item in choices:
        if attempts>=2:break
        if not allowed(item):
            if not rt.config()['ativa']:raise ServiceUnavailable('A integração foi desativada.')
            continue
        attempts+=1
        instance=Provider(item['provedor'],current_app.extensions['secrets'].get('ia_'+item['provedor']))
        g.ai_provider=instance;g.ai_selected=item
        start=time.monotonic();first=None;state='interrompida';error=None
        with db_manager.connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            svc=(read() or {}).get('servicos',{}).get(item['provedor'],{})
            count=conn.execute('SELECT COUNT(*) FROM IATentativas WHERE provedor=? AND instante>?',(item['provedor'],int(time.time())-86400)).fetchone()[0]
            if count>=svc.get('limite_diario',10000):raise TooManyRequests('Limite diário deste serviço atingido.')
            attempt=conn.execute('INSERT INTO IATentativas(utilizacao_id,instante,operacao,provedor,modelo,estado,motivo,custo_estimado_usd) VALUES (?,?,?,?,?,?,?,?)',
                (getattr(g,'ai_use_id',None),int(time.time()),task,item['provedor'],item['id'],'iniciada',item['motivo'],item.get('estimativa'))).lastrowid
            conn.commit()
        try:
            with closing(instance.stream(item['id'],system,messages,max_tokens)) as source:
                for delta in source:
                    if not allowed(item):raise ServiceUnavailable('A integração foi desativada.')
                    if first is None:first=int((time.monotonic()-start)*1000)
                    yield delta
            if first is None:raise ProviderError('O serviço não retornou texto.')
            state='concluida'
            return
        except ProviderError as exc:
            error=last_error=exc
            if first is not None or not exc.safe_retry or attempts>=2:raise
        finally:
            elapsed=int((time.monotonic()-start)*1000)
            with db_manager.connection() as conn:
                actual=instance.usage.get('cost') if instance.name=='openrouter' else None
                actual=actual if type(actual) in (float,int) and math.isfinite(actual) else None
                conn.execute('UPDATE IATentativas SET estado=?,duracao_ms=?,primeiro_token_ms=?,tokens=?,custo_informado_usd=? WHERE id=?',
                    (state,elapsed,first,tokens(instance.usage),actual,attempt));conn.commit()
            if read() is not None:
                def update(reg):
                    svc=reg['servicos'].get(item['provedor'],{})
                    if svc.get('assinatura')!=signature(instance.key):return
                    for model in svc.get('modelos',[]):
                        if model['id']!=item['id']:continue
                        if state=='concluida':
                            model.update(estado='verificado',verificado=True,falhas=0,retomar_em=0)
                            if first is not None:model['primeiro_token_ms']=first
                        elif error:
                            model.update(estado='indisponivel',falhas=model.get('falhas',0)+1,retomar_em=int(time.time())+(300 if error.code=='limite' else 60))
                            if error.code in ('chave','permissao'):svc['verificado']=False
                    svc['limites_informados']=instance.limits
                mutate(update)
    if last_error:raise last_error
    raise ServiceUnavailable('Nenhum serviço autorizado está disponível.')
