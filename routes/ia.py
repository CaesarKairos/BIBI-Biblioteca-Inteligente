"""Configuração administrativa e mediação dentro da aplicação existente."""
import json
import time
from contextlib import closing
from flask import Blueprint, request, jsonify, current_app, g, Response, stream_with_context
from werkzeug.exceptions import BadRequest, Forbidden, ServiceUnavailable, NotFound, TooManyRequests
from utils.auth import admin_required, verificar_senha_admin
from database.database import db_manager
from services.contas_service import auditar, limitar
from services.ai import runtime as rt
from services.ai.providers import PROVIDERS, Provider, ProviderError
from services.ai.recommendations import recommend, aggregates, message_filters
from services.ai.prompts import SYSTEM_PROMPT
from services.ai.policy import evaluate
from services.ai import routing

bp=Blueprint('ia',__name__)

@bp.route('/api/ia/servicos',methods=['GET','PUT'])
@admin_required
def connected_services():
    from services.ai import connections
    if request.method=='PUT':connections.configure(request.get_json())
    return jsonify(connections.view())

@bp.route('/api/ia/servicos/<name>',methods=['PUT','DELETE'])
@admin_required
def connected_service(name):
    from services.ai import connections
    data=request.get_json() or {}
    if request.method=='DELETE':connections.remove(name,data)
    else:connections.save(name,data)
    return jsonify(connections.view())

@bp.post('/api/ia/servicos/<name>/modelos')
@admin_required
def connected_models(name):
    from services.ai.connections import discover
    return jsonify(modelos=discover(name))

@bp.post('/api/ia/servicos/<name>/testar')
@admin_required
def connected_test(name):
    from services.ai.connections import verify
    return jsonify(verify(name))

@bp.put('/api/ia/servicos/<name>/modelos/<path:mid>')
@admin_required
def review_connected_model(name,mid):
    from services.ai.connections import review_model
    review_model(name,mid,request.get_json())
    return jsonify(status='ok')

@bp.errorhandler(ProviderError)
def provider_error(error):
    return jsonify(erro=str(error),codigo=error.code),503

@bp.route('/api/ia/config',methods=['GET','PUT'])
@admin_required
def settings():
    from services.ai.settings import save,view
    if request.method=='PUT':save(request.get_json())
    return jsonify(view())

@bp.post('/api/ia/modelos')
@admin_required
def models():
    cfg=rt.draft()
    limitar('ia-modelos',str(g.conta['id']),limite=10)
    with rt.budget('modelos',preparation=True,cfg=cfg),rt.external():
        key=rt.credential(cfg,True)
        if not key:
            raise BadRequest('Configure uma chave para consultar modelos.')
        signature=rt.fingerprint(cfg,True)
        try:result=Provider(cfg['provedor'],key).models()
        except ProviderError as error:
            rt.record_verification(cfg,False,str(error),True,signature)
            raise
    return jsonify(modelos=result)

@bp.post('/api/ia/testar')
@admin_required
def test():
    cfg=rt.draft()
    instance=rt.provider(cfg,True)
    signature=rt.fingerprint(cfg,True)
    rt.runtime().setdefault('verifying',set()).add(signature)
    try:
        with rt.budget('teste',preparation=True,cfg=cfg), rt.external():
            text=''.join(instance.stream(cfg['modelo'],'Responda apenas OK.',[{'role':'user','content':'Teste de conexão.'}],128))
            if not text:raise ProviderError('O provedor retornou uma resposta vazia.')
    except ProviderError as error:
        rt.record_verification(cfg,False,str(error),True,signature)
        raise
    finally:
        rt.runtime()['verifying'].discard(signature)
    rt.record_verification(cfg,True,'Conexão verificada. Pronto para ativar.',True,signature)
    return jsonify(mensagem='Conexão e geração funcionaram neste teste. Solicitações futuras dependem de saldo, limites e disponibilidade.')

@bp.get('/api/minha-conta/ia/estado')
def status():
    cfg=rt.config()
    return jsonify(**rt.availability(cfg),provedor='Seleção automática' if routing.read() is not None else (PROVIDERS[cfg['provedor']][0] if cfg['ativa'] else None),
                   aviso='Mensagens e contexto literário são processados por um provedor externo. Não compartilhe dados pessoais. Conversas locais expiram após 30 minutos de inatividade.')

@bp.get('/api/minha-conta/ia/recomendacoes')
def recommendations():
    rt.require_ready()
    filters={k:request.args[k][:200] for k in ('genero','autor','prateleira','q') if request.args.get(k)}
    filters.update({k:request.args.get(k)=='true' for k in ('feminina','brasileira','disponivel','indisponivel')})
    return jsonify(livros=recommend(g.conta,filters),origem='Seleção personalizada por critérios do catálogo; sem geração por IA.')

@bp.delete('/api/minha-conta/ia/conversa/<cid>')
def clear(cid):
    with rt.runtime()['lock']:
        item=rt.runtime()['conversations'].get(cid)
        if not item or item['owner']!=rt.owner():raise NotFound('Conversa não encontrada.')
        del rt.runtime()['conversations'][cid]
    return jsonify(status='ok')

@bp.post('/api/minha-conta/ia/chat')
def chat():
    data=request.get_json();message=data.get('mensagem')
    if set(data)-{'mensagem','conversa_id','livro_id'} or not isinstance(message,str) or not 1<=len(message.strip())<=2000:
        raise BadRequest('Envie uma mensagem de até 2000 caracteres; provedor e modelo são definidos pela biblioteca.')
    if data.get('conversa_id') is not None and not isinstance(data['conversa_id'],str):
        raise BadRequest('Conversa inválida.')
    rt.require_ready()
    books=recommend(g.conta,message_filters(message))
    if data.get('livro_id') is not None:
        if type(data['livro_id']) is not int:
            raise BadRequest('Livro inválido.')
        from services.catalogo_service import detail
        books=[detail(data['livro_id'])]+[b for b in books if b['id']!=data['livro_id']]
    # Contexto mínimo: sem nomes de leitores, IDs de conta, emails ou histórico identificável.
    context=[{k:b[k] for k in ('id','titulo','autor','categoria','temas','descricao','disponivel','autoria_genero','autoria_pais','autoria_fonte','motivo') if k in b} for b in books[:12]]
    cid,item=rt.conversation(data.get('conversa_id'))
    def event(kind,**values):
        return json.dumps({'tipo':kind,**values},ensure_ascii=False)+'\n'
    @stream_with_context
    def generate():
        answer=[];completed=False;signature=None
        try:
            with rt.budget('chat') as cfg:
                yield event('inicio',conversa_id=cid)
                decision=evaluate(message)
                if decision.blocked:
                    answer.append(decision.response);yield event('texto',texto=decision.response)
                else:
                    system=SYSTEM_PROMPT+'\nContexto estudantil. CONTEXTO_DO_CATÁLOGO: '+json.dumps(context,ensure_ascii=False)[:12000]
                    history=item['history'][-12:]+[{'role':'user','content':message}]
                    while len(history)>1 and sum(len(m['content']) for m in history)>12000:
                        history=history[2:]
                    signature=rt.fingerprint(cfg)
                    with rt.external(),closing(routing.stream('chat',system,history,cfg['max_tokens'])) as source:
                        for delta in source:
                            if not rt.config()['ativa'] or cid not in rt.runtime()['conversations']:
                                raise ServiceUnavailable('A IA foi desativada pela biblioteca.')
                            answer.append(delta)
                            if sum(map(len,answer))>20000:
                                raise ProviderError('Limite de tamanho da resposta atingido.')
                            yield event('texto',texto=delta)
                if not answer:
                    raise ProviderError('A BIBI não recebeu uma resposta. Tente novamente mais tarde.')
                completed=True
        except (ProviderError,ServiceUnavailable,TooManyRequests) as error:
            if isinstance(error,ProviderError) and routing.read() is None:rt.record_verification(cfg,False,str(error),signature=signature)
            yield event('erro',mensagem=str(error) if isinstance(error,ProviderError) else error.description)
        except Exception as error:
            from werkzeug.exceptions import HTTPException
            current_app.logger.error('Falha interna na conversa BIBI: %s',type(error).__name__)
            yield event('erro',mensagem=error.description if isinstance(error,HTTPException) else 'Não foi possível concluir a resposta.')
        finally:
            with rt.runtime()['lock']:
                if completed:
                    item['history']=(item['history']+[{'role':'user','content':message},{'role':'assistant','content':''.join(answer)}])[-12:]
                elif not item['history']:
                    rt.runtime()['conversations'].pop(cid,None)
                item['busy']=False;item['touched']=time.monotonic()
        yield event('fim',sucesso=completed)
    return Response(generate(),mimetype='application/x-ndjson',headers={'X-Accel-Buffering':'no'})

@bp.get('/api/ia/insights')
@admin_required
def insights():
    rt.require_ready()
    facts=aggregates();cfg=rt.config();state=rt.runtime()
    signature=json.dumps([facts,cfg,routing.cache_signature()],sort_keys=True,ensure_ascii=False)
    cached=state['insights']
    if cached and cached['signature']==signature and time.monotonic()-cached['time']<3600:
        return jsonify(cached['result'])
    result={'indicadores':facts,'origem':'Resumo calculado localmente','texto':f"Há {facts['emprestimos_registrados']} empréstimos registrados. Considere divulgar títulos de menor circulação e conferir a fila de reservas."}
    if cfg['ativa']:
        try:
            with rt.budget('insights') as active,rt.external():
                text=''.join(routing.stream('insights',SYSTEM_PROMPT+'\nContexto administrativo. Use somente estes agregados reais: '+json.dumps(facts,ensure_ascii=False),
                    [{'role':'user','content':'Sugira até três ações de incentivo à leitura. Identifique possibilidades, sem repetir números.'}],active['max_tokens']))
            if text:
                result.update(texto=text,origem='Interpretação por IA de agregados reais; sujeita a revisão')
        except (ProviderError,ServiceUnavailable,TooManyRequests) as error:
            if isinstance(error,ProviderError) and routing.read() is None:rt.record_verification(cfg,False,str(error))
            result['aviso']='IA indisponível; resumo local preservado.'
    state['insights']={'signature':signature,'time':time.monotonic(),'result':result}
    return jsonify(result)

@bp.route('/api/ia/livros/<int:id>/autoria',methods=['GET','PUT'])
@admin_required
def metadata(id):
    with db_manager.connection() as conn:
        row=conn.execute('SELECT autoria_genero,autoria_pais,autoria_fonte FROM Livros WHERE id=? AND arquivado=0',(id,)).fetchone()
    if not row:
        raise NotFound('Livro ativo não encontrado.')
    if request.method=='GET':
        return jsonify(genero=row[0],pais=row[1],fonte=row[2])
    data=request.get_json()
    if set(data)-{'genero','pais','fonte'}:
        raise BadRequest('Metadados de autoria inválidos.')
    from services.autoria_service import validate
    values=validate({'autoria_'+field:data.get(field) for field in ('genero','pais','fonte')})
    with db_manager.connection() as conn:
        conn.execute('UPDATE Livros SET autoria_genero=?,autoria_pais=?,autoria_fonte=? WHERE id=?',
                     (*values,id))
        auditar(conn,'metadados_autoria',id);conn.commit()
    return jsonify(status='ok')
