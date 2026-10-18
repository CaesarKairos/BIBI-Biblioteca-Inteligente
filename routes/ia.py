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

bp=Blueprint('ia',__name__)

@bp.errorhandler(ProviderError)
def provider_error(error):
    return jsonify(erro=str(error),codigo=error.code),503

@bp.route('/api/ia/config',methods=['GET','PUT'])
@admin_required
def settings():
    if request.method=='PUT':
        data=request.get_json();cfg=rt.config()
        allowed=set(rt.DEFAULTS)|{'chave','remover_chave','senha_atual'}
        if set(data)-allowed:
            raise BadRequest('Configuração desconhecida.')
        for field in ('ativa','privacidade_revisada','remover_chave'):
            if field in data and type(data[field]) is not bool:
                raise BadRequest('Opção inválida.')
        for field,low,high in [('por_hora',1,500),('por_dia',1,10000),('concorrencia',1,8),('max_tokens',128,4096)]:
            if field in data and (type(data[field]) is not int or not low<=data[field]<=high):
                raise BadRequest('Limite inválido: '+field)
        selected=data.get('provedor',cfg['provedor'])
        if selected not in PROVIDERS:
            raise BadRequest('Provedor inválido.')
        if 'modelo' in data and (not isinstance(data['modelo'],str) or len(data['modelo'])>200):
            raise BadRequest('Modelo inválido.')
        key=data.get('chave')
        if key is not None and (not isinstance(key,str) or not 1<=len(key.strip())<=4096):
            raise BadRequest('Chave inválida.')
        sensitive=bool(key or data.get('remover_chave') or data.get('ativa') or selected!=cfg['provedor'] or data.get('modelo',cfg['modelo'])!=cfg['modelo'])
        if sensitive and not verificar_senha_admin(data.get('senha_atual')):
            raise Forbidden('Confirme sua senha atual para alterar a configuração sensível.')
        new=cfg|{k:v for k,v in data.items() if k in rt.DEFAULTS}
        if selected!=cfg['provedor'] and 'modelo' not in data:
            new['modelo']=''
        store=current_app.extensions['secrets']
        if new['ativa'] and (not new['privacidade_revisada'] or (not key and not store.get('ia_'+selected)) or data.get('remover_chave')):
            raise BadRequest('Configure a chave e confirme a revisão institucional de privacidade.')
        if key:
            store.set('ia_'+selected,key.strip())
        if data.get('remover_chave'):
            store.set('ia_'+selected,None);new['ativa']=False
        with db_manager.connection() as conn:
            conn.execute("INSERT OR REPLACE INTO Configuracoes VALUES ('ia',?)",(json.dumps(new),))
            auditar(conn,'configurar_ia',selected);conn.commit()
        rt.runtime()['insights']=None
        rt.runtime().pop('connection_test',None)
    cfg=rt.config()
    with db_manager.connection() as conn:
        count=conn.execute('SELECT COUNT(*) FROM IAUtilizacao WHERE instante>?',(int(time.time())-86400,)).fetchone()[0]
        tokens=conn.execute('SELECT SUM(tokens) FROM IAUtilizacao WHERE instante>?',(int(time.time())-86400,)).fetchone()[0]
    return jsonify(**cfg,chave_configurada=bool(current_app.extensions['secrets'].get('ia_'+cfg['provedor'])),
        provedores=[{'id':k,'nome':v[0]} for k,v in PROVIDERS.items()],solicitacoes_24h=count,
        tokens_informados_24h=tokens,limites_provedor=rt.runtime().get('provider_limits',{}),teste=rt.runtime().get('connection_test'),
        custo='Não calculado. Consulte o painel do provedor; listagem não garante acesso nem gratuidade.')

@bp.post('/api/ia/modelos')
@admin_required
def models():
    cfg=rt.config()
    if not cfg['ativa']:
        raise ServiceUnavailable('Ative a IA com revisão institucional antes de consultar o provedor.')
    limitar('ia-modelos',str(g.conta['id']),limite=10)
    with rt.budget('modelos'),rt.external():
        key=current_app.extensions['secrets'].get('ia_'+cfg['provedor'])
        if not key:
            raise BadRequest('Configure uma chave para consultar modelos.')
        result=Provider(cfg['provedor'],key).models()
    return jsonify(modelos=result)

@bp.post('/api/ia/testar')
@admin_required
def test():
    try:
        with rt.budget('teste') as cfg, rt.external():
            text=''.join(rt.provider(cfg).stream(cfg['modelo'],'Responda apenas OK.',[{'role':'user','content':'Teste de conexão.'}],128))
    except ProviderError as error:
        rt.runtime()['connection_test']={'funcionou':False,'mensagem':str(error),'instante':int(time.time())}
        raise
    if not text:
        raise ProviderError('O provedor retornou uma resposta vazia.')
    rt.runtime()['connection_test']={'funcionou':True,'mensagem':'Conexão e geração confirmadas no último teste; sem garantia futura.','instante':int(time.time())}
    return jsonify(mensagem='Conexão e geração funcionaram neste teste. Solicitações futuras dependem de saldo, limites e disponibilidade.')

@bp.get('/api/minha-conta/ia/estado')
def status():
    cfg=rt.config()
    return jsonify(ativa=cfg['ativa'],provedor=PROVIDERS[cfg['provedor']][0] if cfg['ativa'] else None,
                   aviso='Mensagens e contexto literário são processados por um provedor externo. Não compartilhe dados pessoais. Conversas locais expiram após 30 minutos de inatividade.')

@bp.get('/api/minha-conta/ia/recomendacoes')
def recommendations():
    filters={k:request.args[k][:200] for k in ('genero','autor','prateleira','q') if request.args.get(k)}
    filters.update({k:request.args.get(k)=='true' for k in ('feminina','brasileira','disponivel','indisponivel')})
    return jsonify(livros=recommend(g.conta,filters),origem='Seleção personalizada por critérios do catálogo; sem geração por IA.')

@bp.delete('/api/minha-conta/ia/conversa/<cid>')
def clear(cid):
    cid,item=rt.conversation(cid)
    with rt.runtime()['lock']:
        del rt.runtime()['conversations'][cid]
    return jsonify(status='ok')

@bp.post('/api/minha-conta/ia/chat')
def chat():
    data=request.get_json();message=data.get('mensagem')
    if set(data)-{'mensagem','conversa_id','livro_id'} or not isinstance(message,str) or not 1<=len(message.strip())<=2000:
        raise BadRequest('Envie uma mensagem de até 2000 caracteres; provedor e modelo são definidos pela biblioteca.')
    if data.get('conversa_id') is not None and not isinstance(data['conversa_id'],str):
        raise BadRequest('Conversa inválida.')
    if not rt.config()['ativa']:
        raise ServiceUnavailable('A inteligência artificial está desativada. Explore as sugestões do acervo.')
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
        answer=[];completed=False
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
                    with rt.external(),closing(rt.provider(cfg).stream(cfg['modelo'],system,history,cfg['max_tokens'])) as source:
                        for delta in source:
                            if not rt.config()['ativa']:
                                raise ServiceUnavailable('A IA foi desativada pela biblioteca.')
                            answer.append(delta)
                            if sum(map(len,answer))>20000:
                                raise ProviderError('Limite de tamanho da resposta atingido.')
                            yield event('texto',texto=delta)
                if not answer:
                    raise ProviderError('A BIBI não recebeu uma resposta. Tente novamente mais tarde.')
                completed=True
        except (ProviderError,ServiceUnavailable,TooManyRequests) as error:
            yield event('erro',mensagem=str(error) if isinstance(error,ProviderError) else error.description)
        except Exception as error:
            from werkzeug.exceptions import HTTPException
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
    facts=aggregates();cfg=rt.config();state=rt.runtime()
    signature=json.dumps([facts,cfg],sort_keys=True,ensure_ascii=False)
    cached=state['insights']
    if cached and cached['signature']==signature and time.monotonic()-cached['time']<3600:
        return jsonify(cached['result'])
    result={'indicadores':facts,'origem':'Resumo calculado localmente','texto':f"Há {facts['emprestimos_registrados']} empréstimos registrados. Considere divulgar títulos de menor circulação e conferir a fila de reservas."}
    if cfg['ativa']:
        try:
            with rt.budget('insights') as active,rt.external():
                text=''.join(rt.provider(active).stream(active['modelo'],SYSTEM_PROMPT+'\nContexto administrativo. Use somente estes agregados reais: '+json.dumps(facts,ensure_ascii=False),
                    [{'role':'user','content':'Sugira até três ações de incentivo à leitura. Identifique possibilidades, sem repetir números.'}],active['max_tokens']))
            if text:
                result.update(texto=text,origem='Interpretação por IA de agregados reais; sujeita a revisão')
        except (ProviderError,ServiceUnavailable) as error:
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
    if set(data)-{'genero','pais','fonte'} or data.get('genero') not in (None,'feminina','masculina','mista'):
        raise BadRequest('Metadados de autoria inválidos.')
    if any(v is not None and (not isinstance(v,str) or len(v)>500) for v in data.values()):
        raise BadRequest('Use textos de até 500 caracteres.')
    if (data.get('genero') or data.get('pais')) and not data.get('fonte','').strip():
        raise BadRequest('Registre uma fonte confiável para a classificação.')
    with db_manager.connection() as conn:
        conn.execute('UPDATE Livros SET autoria_genero=?,autoria_pais=?,autoria_fonte=? WHERE id=?',
                     (data.get('genero'),data.get('pais'),data.get('fonte'),id))
        auditar(conn,'metadados_autoria',id);conn.commit()
    return jsonify(status='ok')
