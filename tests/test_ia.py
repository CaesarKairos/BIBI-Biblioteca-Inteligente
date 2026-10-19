"""Contratos e fluxos locais: nenhuma chamada paga, bancos e segredos temporários."""
import json
import time
from unittest.mock import patch, MagicMock
import requests
from tests.support import AppTest, authenticate, HASH
from services.ai.providers import Provider, PROVIDERS, ProviderError
from services.ai.recommendations import recommend

def deltas(chunks):
    yield from chunks


class AITests(AppTest):
    def test_preparation_then_activation_and_persistent_readiness(self):
        reader=self.reader_account()
        state=lambda:reader.get('/api/minha-conta/ia/estado').json
        self.assertFalse(state()['disponivel'])
        payload={'provedor':'openai','chave':'temporary-key','senha_atual':'senha forte de teste'}
        with patch('requests.request') as network:
            self.assertEqual(reader.post('/api/ia/modelos',json={}).status_code,403)
            self.assertEqual(reader.post('/api/ia/testar',json={}).status_code,403)
            self.assertEqual(self.client.put('/api/ia/config',json=payload).status_code,200)
            self.assertFalse(state()['disponivel'])
            self.assertEqual(reader.get('/api/minha-conta/ia/recomendacoes').status_code,503)
            network.assert_not_called()
        with patch.object(Provider,'models',return_value=[{'id':'test-model'}]):
            self.assertEqual(self.client.post('/api/ia/modelos',json={}).status_code,200)
        self.assertEqual(self.client.put('/api/ia/config',json={'modelo':'test-model'}).status_code,200)
        self.assertEqual(self.client.put('/api/ia/config',json={'ativa':True,'privacidade_revisada':True}).status_code,400)
        with patch.object(Provider,'stream',side_effect=lambda *args:deltas(['OK'])):
            self.assertEqual(self.client.post('/api/ia/testar',json={}).status_code,200)
        self.assertFalse(state()['disponivel'])
        self.assertEqual(self.client.put('/api/ia/config',json={'ativa':True,'privacidade_revisada':True}).status_code,200)
        self.assertTrue(state()['disponivel'])
        self.app.extensions.pop('ai_runtime',None)
        self.assertTrue(state()['disponivel'],'A prova de conexão deve sobreviver ao reinício do estado efêmero.')
        self.assertEqual(self.client.put('/api/ia/config',json={'ativa':False}).status_code,200)
        self.assertFalse(state()['disponivel'])

    def test_draft_failure_does_not_replace_working_provider(self):
        self.enable()
        from services.ai import runtime as rt
        self.client.put('/api/ia/config',json={'provedor':'groq','chave':'other-key','modelo':'other-model'})
        self.assertFalse(rt.draft()['privacidade_revisada'],'Outro provedor exige revisão institucional própria.')
        with patch.object(Provider,'stream',side_effect=ProviderError('Chave inválida','chave')):
            self.assertEqual(self.client.post('/api/ia/testar',json={}).status_code,503)
        self.assertEqual(rt.config()['provedor'],'openai')
        self.assertTrue(rt.availability()['disponivel'])
        self.assertEqual(self.client.put('/api/ia/config',json={'ativa':True}).status_code,400)
        self.client.put('/api/ia/config',json={'descartar':True})
        self.assertEqual(self.client.get('/api/ia/config').json['provedor'],'openai')

    def test_expired_confirmation_and_failed_active_connection(self):
        self.enable()
        with self.client.session_transaction() as session:session['ia_confirmacao']={'conta':1,'em':0}
        self.assertEqual(self.client.put('/api/ia/config',json={'chave':'replace-key'}).status_code,403)
        self.assertEqual(self.client.put('/api/ia/config',json={'modelo':'other-model'}).status_code,200)
        self.client.put('/api/ia/config',json={'descartar':True})
        with patch.object(Provider,'stream',side_effect=ProviderError('Não foi possível conectar.','rede')):
            self.client.post('/api/ia/testar',json={})
        self.assertEqual(self.client.get('/api/minha-conta/ia/estado').json['estado'],'indisponivel')
        with patch('requests.request') as network:
            self.assertEqual(self.client.post('/api/minha-conta/ia/chat',json={'mensagem':'Literatura'}).status_code,503)
            network.assert_not_called()

    def test_book_authorship_is_optional_atomic_and_preserved(self):
        payload={'manual':True,'titulo':'Obra documentada','autor':'Pessoa autora','quantidade':1,
                 'autoria_genero':'feminina','autoria_pais':'Brasil','autoria_fonte':'Biografia consultada'}
        response=self.client.post('/api/livros',json=payload)
        self.assertEqual(response.status_code,201)
        book=response.json['id']
        self.assertEqual(self.client.get(f'/api/ia/livros/{book}/autoria').json['pais'],'Brasil')
        edit={'titulo':payload['titulo'],'autor':payload['autor'],'estoque':1,'categoria':'Ficção'}
        self.assertEqual(self.client.put(f'/api/livros/{book}',json=edit).status_code,200)
        self.assertEqual(self.client.get(f'/api/ia/livros/{book}/autoria').json['genero'],'feminina')
        invalid=edit|{'titulo':'Não deve salvar','autoria_genero':'feminina','autoria_fonte':None}
        self.assertEqual(self.client.put(f'/api/livros/{book}',json=invalid).status_code,400)
        self.assertEqual(self.sql('SELECT nome FROM Livros WHERE id=?',(book,))[0][0],payload['titulo'])

    def test_legacy_saved_key_does_not_imply_ready_after_upgrade(self):
        from app import create_app
        from services.ai import runtime as rt
        self.app.extensions['secrets'].set('ia_openai','legacy-key')
        self.sql("INSERT INTO Configuracoes VALUES ('ia',?)",(json.dumps({'ativa':True,'provedor':'openai','modelo':'legacy-model'}),))
        updated=create_app({'TESTING':True,'DATA_DIR':str(self.directory)})
        with updated.app_context():
            self.assertFalse(rt.config()['ativa'])
            self.assertFalse(rt.availability()['disponivel'])
            self.assertEqual(updated.extensions['secrets'].get('ia_openai'),'legacy-key')

    def reader_account(self, id=2):
        reader=self.reader(name='Leitor '+str(id),email=f'reader{id}@example.test')
        self.sql("INSERT INTO Contas(id,leitor_id,nome,email,senha_hash,papel,ativacao,onboarding_concluido_em) VALUES (?,?,'Leitor',?,?,'leitor','presencial',CURRENT_TIMESTAMP)",(id,reader,f'reader{id}@example.test',HASH))
        return authenticate(self.app,self.app.test_client(),id)

    def enable(self, **changes):
        payload={'provedor':'openai','modelo':'test-model','chave':'SECRET-TEST-KEY','senha_atual':'senha forte de teste','privacidade_revisada':True}|changes
        payload.pop('ativa',None)
        response=self.client.put('/api/ia/config',json=payload)
        self.assertEqual(response.status_code,200,response.json)
        with patch.object(Provider,'stream',side_effect=lambda *args:deltas(['OK'])):
            self.assertEqual(self.client.post('/api/ia/testar',json={}).status_code,200)
        response=self.client.put('/api/ia/config',json={'ativa':True})
        self.assertEqual(response.status_code,200,response.json)
        self.sql('DELETE FROM IAUtilizacao')
        return response

    def events(self, response):
        return [json.loads(line) for line in response.get_data(as_text=True).splitlines()]

    def test_configuration_permissions_secret_and_disable_no_network(self):
        reader=self.reader_account()
        self.assertEqual(reader.get('/api/ia/config').status_code,403)
        self.assertEqual(reader.put('/api/ia/config',json={'ativa':True}).status_code,403)
        self.assertNotIn('ai-config-form',reader.get('/configuracoes?fragmento=1').get_data(as_text=True))
        self.assertEqual(self.client.put('/api/ia/config',json={'chave':'abc'}).status_code,403)
        saved=self.enable()
        self.assertNotIn('SECRET-TEST-KEY',saved.get_data(as_text=True))
        self.assertNotIn('SECRET-TEST-KEY',repr(self.sql('SELECT * FROM Configuracoes')))
        self.assertNotIn(b'SECRET-TEST-KEY',(self.directory/'segredos.dpapi').read_bytes())
        with patch('requests.request') as network:
            self.assertEqual(self.client.put('/api/ia/config',json={'ativa':False}).status_code,200)
            # Preparatory operations are authorized while disabled.
            with patch.object(Provider,'models',return_value=[]):
                self.assertEqual(self.client.post('/api/ia/modelos',json={}).status_code,200)
            with patch.object(Provider,'stream',side_effect=lambda *args:deltas(['OK'])):
                self.assertEqual(self.client.post('/api/ia/testar',json={}).status_code,200)
            self.assertEqual(reader.post('/api/minha-conta/ia/chat',json={'mensagem':'Olá'}).status_code,503)
            self.assertEqual(self.client.get('/api/ia/insights').status_code,503)
            self.assertEqual(reader.get('/api/minha-conta/ia/recomendacoes').status_code,503)
            network.assert_not_called()

    def test_priority_filters_unknown_and_invalidation(self):
        client=self.reader_account();self.enable()
        ids=[self.book() for _ in range(5)]
        self.sql('UPDATE Livros SET autoria_genero=?,autoria_pais=?,autoria_fonte=? WHERE id=?',('feminina','Brasil','Bibliografia',ids[3]))
        self.sql('UPDATE Livros SET autoria_genero=?,autoria_pais=?,autoria_fonte=? WHERE id=?',('feminina','Portugal','Bibliografia',ids[1]))
        self.sql('UPDATE Livros SET autoria_genero=?,autoria_pais=? WHERE id=?',('feminina','Brasil',ids[0]))
        get=lambda query='':client.get('/api/minha-conta/ia/recomendacoes'+query).json['livros']
        self.assertEqual(get()[0]['id'],ids[3])
        self.assertEqual([b['id'] for b in get('?feminina=true&brasileira=true')],[ids[3]])
        self.sql("UPDATE Livros SET categoria='Poesia',autor='Pessoa específica' WHERE id=?",(ids[4],))
        self.assertEqual([b['id'] for b in get('?genero=Poesia&autor=específica')],[ids[4]])
        self.sql('UPDATE Livros SET arquivado=1 WHERE id=?',(ids[3],))
        self.assertNotIn(ids[3],[b['id'] for b in get()])
        self.assertEqual(get()[0]['id'],ids[1])

    def test_personalization_uses_favorites_ratings_loans(self):
        client=self.reader_account();self.enable();ids=[self.book() for _ in range(3)]
        self.sql("UPDATE Livros SET categoria='Poesia',temas='natureza' WHERE id IN (?,?)",(ids[1],ids[2]))
        client.put('/api/minha-conta/favoritos',json={'livros':[ids[1]]})
        client.post('/api/minha-conta/avaliacoes/'+str(ids[1]),json={'estrelas':5,'comentario':'Gostei'})
        result=client.get('/api/minha-conta/ia/recomendacoes').json['livros']
        self.assertIn(result[0]['id'],ids[1:])
        self.assertIn('Temas em comum',result[0]['motivo'])
        self.sql("INSERT INTO Emprestimo(usuarios_id,livros_id,data_emprestimo,data_vencimento) VALUES (1,?,'2026-10-01','2026-10-08')",(ids[1],))
        self.assertEqual(client.get('/api/minha-conta/ia/recomendacoes').status_code,200)

    def test_chat_context_stream_isolation_and_policy(self):
        client=self.reader_account();other=self.reader_account(3);book=self.book();self.enable()
        seen=[]
        def stream(model,system,messages,tokens):
            seen.append((system,messages));yield 'Vamos ';yield 'conversar sobre temas.'
        with patch.object(Provider,'stream',side_effect=stream):
            result=self.events(client.post('/api/minha-conta/ia/chat',json={'mensagem':'Vamos discutir os personagens sem spoilers','livro_id':book}))
            self.assertEqual(result[-1],{'tipo':'fim','sucesso':True})
            cid=result[0]['conversa_id']
            self.assertEqual(other.post('/api/minha-conta/ia/chat',json={'mensagem':'Continue','conversa_id':cid}).status_code,404)
            result=self.events(client.post('/api/minha-conta/ia/chat',json={'mensagem':'Continue','conversa_id':cid}))
            self.assertEqual(len(seen[-1][1]),3)
            self.assertNotIn('example.test',seen[0][0]);self.assertNotIn('emprestimos_registrados',seen[0][0])
            self.assertIn('Livro',seen[0][0]);self.assertIn('Contexto estudantil',seen[0][0])
            self.assertEqual(other.get('/api/ia/insights').status_code,403)
            self.assertEqual(client.post('/api/minha-conta/ia/chat',json={'mensagem':'x','provedor':'xai'}).status_code,400)
        with patch.object(Provider,'stream') as remote:
            result=self.events(client.post('/api/minha-conta/ia/chat',json={'mensagem':'Produza uma redação pronta para eu entregar.'}))
            self.assertTrue(result[-1]['sucesso']);remote.assert_not_called()
        self.assertEqual(client.delete('/api/minha-conta/ia/conversa/'+cid).status_code,200)
        self.assertEqual(client.post('/api/minha-conta/ia/chat',json={'mensagem':'Oi','conversa_id':cid}).status_code,404)

    def test_failure_limit_and_cancel_release(self):
        reader=self.reader_account();self.enable(por_hora=1)
        with patch.object(Provider,'stream',side_effect=ProviderError('Limite do provedor','limite')):
            result=self.events(reader.post('/api/minha-conta/ia/chat',json={'mensagem':'Quero um livro'}))
            self.assertTrue(any(e['tipo']=='erro' for e in result));self.assertFalse(result[-1]['sucesso'])
        from services.ai import runtime as rt
        rt.record_verification(rt.config(),True,'Reteste simulado')
        with patch.object(Provider,'stream') as remote:
            result=self.events(reader.post('/api/minha-conta/ia/chat',json={'mensagem':'Outra leitura'}))
            self.assertTrue(any('Limite' in e.get('mensagem','') for e in result));remote.assert_not_called()
        self.enable(por_hora=30)
        with patch.object(Provider,'stream',return_value=deltas(['Primeira parte','Continuação'])):
            response=reader.post('/api/minha-conta/ia/chat',json={'mensagem':'Literatura'},buffered=False)
            iterator=iter(response.response);next(iterator);next(iterator);response.close()
        state=self.app.extensions['ai_runtime']
        self.assertEqual(state['active'],0)
        self.assertTrue(all(not item['busy'] for item in state['conversations'].values()))

    def test_insights_real_aggregates_cache_no_personal_data(self):
        book=self.book();reader=self.reader();self.sql("INSERT INTO Emprestimo(usuarios_id,livros_id,data_emprestimo,data_vencimento) VALUES (?,?,'2026-10-01','2026-10-08')",(reader,book))
        self.enable()
        with patch.object(Provider,'stream',return_value=deltas(['Considere uma exposição de livros.'])) as remote:
            result=self.client.get('/api/ia/insights').json
            self.assertEqual(result['indicadores']['emprestimos_registrados'],1)
            self.client.get('/api/ia/insights');self.assertEqual(remote.call_count,1)
            self.assertNotIn('ana@example.test',repr(remote.call_args));self.assertNotIn('usuarios_id',repr(remote.call_args))

    def test_model_listing_connection_and_removal(self):
        self.enable()
        with patch.object(Provider,'models',return_value=[{'id':'test-model','nome':'Modelo de teste'}]):
            self.assertEqual(self.client.post('/api/ia/modelos',json={}).json['modelos'][0]['id'],'test-model')
        with patch.object(Provider,'stream',return_value=deltas(['OK'])):
            self.assertEqual(self.client.post('/api/ia/testar',json={}).status_code,200)
        self.assertEqual(self.client.put('/api/ia/config',json={'ativa':False,'remover_chave':True,'senha_atual':'senha forte de teste'}).status_code,200)
        self.assertIsNone(self.app.extensions['secrets'].get('ia_openai'))

    def test_explicit_chat_preferences_limit_candidates(self):
        client=self.reader_account();first=self.book();female=self.book();self.enable()
        self.sql("UPDATE Livros SET autoria_genero='feminina',autoria_pais='Brasil',autoria_fonte='Fonte' WHERE id=?",(female,))
        with patch.object(Provider,'stream',return_value=deltas(['Sugestão'])) as remote:
            self.events(client.post('/api/minha-conta/ia/chat',json={'mensagem':'Recomende uma autora brasileira'}))
            context=remote.call_args.args[1].split('CONTEXTO_DO_CATÁLOGO: ')[1]
            self.assertEqual([b['id'] for b in json.loads(context)],[female])

    def test_review_author_edit_delete_published_privacy_and_local_moderation(self):
        author=self.reader_account();other=self.reader_account(3);book=self.book();path='/api/minha-conta/avaliacoes/'+str(book)
        self.assertEqual(author.post(path,json={'estrelas':5,'comentario':'Excelente leitura'}).status_code,200)
        public=other.get(path).json
        self.assertEqual(public[0]['comentario'],'Excelente leitura')
        self.assertNotIn('leitor_id',public[0]);self.assertNotIn('email',public[0])
        self.assertEqual(other.delete(path).status_code,200)
        self.assertEqual(len(author.get(path).json),1)
        with patch('requests.request') as external:
            author.post(path,json={'estrelas':2,'comentario':'idiota'})
            self.assertEqual(other.get(path).json,[])
            self.assertEqual(author.get('/api/minha-conta/avaliacoes').json[0]['estado'],'revisao')
            external.assert_not_called()
        author.post(path,json={'estrelas':4,'comentario':'Agora uma reflexão respeitosa'})
        self.assertEqual(other.get(path).json[0]['estrelas'],4)
        author.delete(path);self.assertEqual(other.get(path).json,[])

    def test_usage_persistence_restart_and_backup_excludes_keys(self):
        import io,zipfile
        from app import create_app
        self.enable()
        with patch.object(Provider,'stream',return_value=deltas(['OK'])):
            self.client.post('/api/ia/testar',json={})
        self.assertEqual(self.client.get('/api/ia/config').json['solicitacoes_24h'],1)
        restarted=create_app({'TESTING':True,'DATA_DIR':str(self.directory)})
        with restarted.app_context():
            from services.ai.runtime import config
            self.assertEqual(config()['modelo'],'test-model')
            self.assertTrue(restarted.extensions['secrets'].get('ia_openai'))
        backup=self.client.post('/api/gestao/backup')
        self.addCleanup(backup.close)
        self.assertEqual(backup.status_code,200)
        with zipfile.ZipFile(io.BytesIO(backup.data)) as archive:
            self.assertFalse(any('segredos' in name for name in archive.namelist()))
            self.assertFalse(any(b'SECRET-TEST-KEY' in archive.read(name) for name in archive.namelist()))

    def test_conversation_expiry_and_concurrency(self):
        client=self.reader_account();self.enable(concorrencia=1)
        with patch.object(Provider,'stream',return_value=deltas(['Olá'])):
            events=self.events(client.post('/api/minha-conta/ia/chat',json={'mensagem':'Literatura'}))
        cid=events[0]['conversa_id'];state=self.app.extensions['ai_runtime']
        state['conversations'][cid]['touched']-=1900
        self.assertEqual(client.post('/api/minha-conta/ia/chat',json={'mensagem':'Continue','conversa_id':cid}).status_code,404)
        state['active']=1
        with patch.object(Provider,'stream') as remote:
            result=self.events(client.post('/api/minha-conta/ia/chat',json={'mensagem':'Literatura'}))
            self.assertFalse(result[-1]['sucesso']);remote.assert_not_called()
        state['active']=0

    def test_concurrent_cloud_does_not_block_catalog_or_disable(self):
        import threading
        first=self.reader_account();second=self.reader_account(3);self.enable(concorrencia=2)
        started=[];results=[];ready=threading.Event();release=threading.Event();mutex=threading.Lock()
        def stream(*args):
            with mutex:
                started.append(True)
                if len(started)==2:ready.set()
            if not release.wait(10):raise ProviderError('Tempo de teste excedido')
            yield 'Resposta'
        def request(client):
            results.append(self.events(client.post('/api/minha-conta/ia/chat',json={'mensagem':'Vamos falar de literatura'})))
        with patch.object(Provider,'stream',side_effect=stream):
            workers=[threading.Thread(target=request,args=(client,)) for client in (first,second)]
            for worker in workers:worker.start()
            try:
                self.assertTrue(ready.wait(10),'As duas chamadas devem executar simultaneamente.')
                self.assertEqual(self.client.get('/api/livros').status_code,200)
                result=self.events(self.client.post('/api/minha-conta/ia/chat',json={'mensagem':'Uma terceira conversa'}))
                self.assertFalse(result[-1]['sucesso'])
                self.assertEqual(self.client.put('/api/ia/config',json={'ativa':False}).status_code,200)
            finally:
                release.set()
                for worker in workers:worker.join(10)
            self.assertTrue(all(not worker.is_alive() for worker in workers))
            self.assertEqual(len(results),2)
            self.assertTrue(all(not events[-1]['sucesso'] for events in results))
            self.assertEqual(self.app.extensions['ai_runtime']['active'],0)

class ProviderContracts(__import__('unittest').TestCase):
    def response(self,data=None,lines=None,status=200):
        response=MagicMock();response.status_code=status
        response.__enter__.return_value=response;response.json.return_value=data
        response.iter_lines.return_value=[('data: '+json.dumps(e)).encode() for e in (lines or [])]
        return response

    def test_all_provider_auth_model_listing_and_stream_contracts(self):
        events={
            'openai':{'type':'response.output_text.delta','delta':'Olá'},
            'xai':{'type':'response.output_text.delta','delta':'Olá'},
            'anthropic':{'type':'content_block_delta','delta':{'type':'text_delta','text':'Olá'}},
            'google':{'candidates':[{'content':{'parts':[{'text':'secreto','thought':True},{'text':'Olá'}]}}]},
            'groq':{'choices':[{'delta':{'content':'Olá'}}]},
            'openrouter':{'choices':[{'delta':{'content':'Olá'}}]},
        }
        for name in PROVIDERS:
            with self.subTest(provider=name):
                data={'models':[{'name':'models/test-model','supportedGenerationMethods':['generateContent']}]} if name=='google' else {'data':[{'id':'test-model'}]}
                with patch('requests.request',return_value=self.response(data=data)) as call:
                    self.assertEqual(Provider(name,'secret').models()[0]['id'],'test-model')
                    self.assertNotIn('secret',call.call_args.args[1])
                    headers=call.call_args.kwargs['headers'];self.assertIn('x-goog-api-key' if name=='google' else 'x-api-key' if name=='anthropic' else 'Authorization',headers)
                terminal={'openai':{'type':'response.completed'},'xai':{'type':'response.completed'},'anthropic':{'type':'message_stop'},'google':{'candidates':[{'finishReason':'STOP'}]},'groq':{},'openrouter':{}}[name]
                response=self.response(lines=[events[name],terminal])
                if name in ('groq','openrouter'):
                    response.iter_lines.return_value += [b'data: [DONE]']
                with patch('requests.request',return_value=response) as call:
                    self.assertEqual(''.join(Provider(name,'secret').stream('test-model','system',[{'role':'user','content':'Olá'}],128)),'Olá')
                    body=call.call_args.kwargs['json'];self.assertNotIn('tools',body)
                    if name in ('openai','xai'):self.assertFalse(body['store'])
                    if name=='xai':
                        self.assertEqual(body['input'][0],{'role':'system','content':'system'})
                        self.assertNotIn('instructions',body)

    def test_errors_redact_credentials_and_do_not_retry(self):
        for name in PROVIDERS:
            for status in (401,403,404,429,500):
                with self.subTest(provider=name,status=status),patch('requests.request',return_value=self.response(status=status)) as remote:
                    with self.assertRaises(ProviderError) as error:Provider(name,'secret').models()
                    self.assertNotIn('secret',str(error.exception));self.assertEqual(remote.call_count,1)
        with patch('requests.request',side_effect=requests.Timeout('secret')):
            with self.assertRaises(ProviderError) as error:Provider('openai','secret').models()
            self.assertNotIn('secret',str(error.exception))

    def test_truncated_stream_is_not_success_and_thinking_is_hidden(self):
        for name in ('openai','anthropic','google'):
            with self.subTest(provider=name),patch('requests.request',return_value=self.response(lines=[{'type':'reasoning.delta','delta':'Segredo'}])):
                with self.assertRaises(ProviderError):list(Provider(name,'secret').stream('test','system',[],128))
