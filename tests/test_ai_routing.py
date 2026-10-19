"""Temporary DB and simulated providers: no paid connectivity checks."""
import json
from unittest.mock import patch
from tests.support import AppTest,authenticate,HASH
from services.ai import routing as router,runtime as rt
from services.ai.providers import Provider,ProviderError


def models(*args):
    return [{'id':'fixture-text','nome':'Modelo sintético','compativel':True,'tarefas':['chat','insights'],
             'contexto':32000,'precos':{'prompt':'0','completion':'0'},'portugues':'nao_avaliado'}]


class RoutingTests(AppTest):
    def test_insights_cache_survives_health_and_latency_updates(self):
        self.connect();self.activate()
        with patch.object(Provider,'stream',side_effect=lambda *args:(text for text in ['Ação baseada nos agregados'])) as stream:
            self.assertEqual(self.client.get('/api/ia/insights').status_code,200)
            self.assertEqual(self.client.get('/api/ia/insights').status_code,200)
            self.assertEqual(stream.call_count,1)

    def test_revocation_interrupts_stream_without_authorization_cache_leak(self):
        self.connect();self.activate()
        def stream(instance,*args):
            yield 'Primeira parte'
            router.mutate(lambda reg:reg['servicos']['openai'].update(habilitado=False))
            yield 'Trecho que deve ser bloqueado'
        with patch.object(Provider,'stream',stream):result=self.chat()
        self.assertIn('Primeira parte',result)
        self.assertNotIn('Trecho que deve ser bloqueado',result)
        self.assertFalse(rt.availability()['disponivel'])

    def test_catalog_rejects_unknown_and_internal_routers_without_inventing_quality(self):
        from services.ai.model_catalog import describe
        self.assertFalse(describe('openai',{'id':'invented-model'})['compativel'])
        self.assertFalse(describe('openrouter',{'id':'openrouter/auto','architecture':{'input_modalities':['text'],'output_modalities':['text']},'supported_parameters':['max_tokens']})['compativel'])
        self.assertTrue(describe('openai',{'id':'gpt-4.1-mini'})['compativel'])
        self.assertEqual(describe('openai',{'id':'gpt-4.1-mini'})['portugues'],'nao_avaliado')

    def test_school_portuguese_review_is_recorded_and_controls_eligibility(self):
        self.connect('openai');self.connect('groq')
        url='/api/ia/servicos/openai/modelos/fixture-text'
        self.assertEqual(self.client.put(url,json={'portugues':'rejeitado'}).status_code,200)
        self.assertEqual([r['provedor'] for r in router.candidates()],['groq'])
        self.assertEqual(self.client.put(url,json={'portugues':'aprovado','tarefas':['insights']}).status_code,200)
        self.assertEqual([r['provedor'] for r in router.candidates('chat')],['groq'])
        self.assertEqual(router.candidates('insights')[0]['provedor'],'openai')
        with patch.object(Provider,'models',side_effect=models):
            self.assertEqual(self.client.post('/api/ia/servicos/openai/modelos',json={}).status_code,200)
        self.assertEqual(router.candidates('insights')[0]['provedor'],'openai','Discovery must preserve the school review')
        self.assertEqual([r['provedor'] for r in router.candidates('chat')],['groq'])

    def test_fallback_is_bounded_to_two_network_calls(self):
        for name in ('openai','groq','anthropic'):self.connect(name)
        self.activate()
        with patch.object(Provider,'stream',side_effect=ProviderError('Limite','limite',True)) as stream:self.chat()
        self.assertEqual(stream.call_count,2)

    def connect(self,name='openai',paid=False):
        data={'chave':'synthetic-'+name,'senha_atual':'senha forte de teste','privacidade_revisada':True,'custos_autorizados':paid}
        result=self.client.put('/api/ia/servicos/'+name,json=data)
        self.assertEqual(result.status_code,200,result.json)
        with patch.object(Provider,'models',side_effect=models),patch.object(Provider,'stream',side_effect=lambda *args:(x for x in ['OK'])):
            self.assertEqual(self.client.post('/api/ia/servicos/'+name+'/testar',json={}).status_code,200)
        return self.client.get('/api/ia/servicos').json

    def activate(self):
        result=self.client.put('/api/ia/servicos',json={'ativa':True,'senha_atual':'senha forte de teste'})
        self.assertEqual(result.status_code,200,result.json)

    def chat(self):
        return self.client.post('/api/minha-conta/ia/chat',json={'mensagem':'Quero conversar sobre literatura.'}).get_data(as_text=True)

    def test_single_service_no_model_selection_and_global_disable(self):
        self.connect();self.assertFalse(rt.availability()['disponivel']);self.activate()
        with patch.object(Provider,'stream',side_effect=lambda *args:(x for x in ['Resposta'])):
            self.assertIn('Resposta',self.chat())
        self.assertEqual(self.sql('SELECT provedor,modelo FROM IATentativas'),[('openai','fixture-text')])
        self.assertEqual(self.sql("SELECT provedor,modelo FROM IAUtilizacao WHERE operacao='chat'"),[('openai','fixture-text')])
        self.client.put('/api/ia/servicos',json={'ativa':False})
        with patch.object(Provider,'stream') as stream:
            self.assertEqual(self.client.post('/api/minha-conta/ia/chat',json={'mensagem':'Literatura'}).status_code,503)
            stream.assert_not_called()

    def test_costs_unknown_and_paid_are_not_implicitly_authorized(self):
        self.connect();self.activate()
        router.mutate(lambda reg:reg['servicos']['openai']['modelos'][0].update(precos=None))
        self.assertFalse(rt.availability()['disponivel'])
        self.assertFalse(router.candidates())
        self.client.put('/api/ia/servicos/openai',json={'custos_autorizados':True})
        self.assertTrue(router.candidates())
        self.client.put('/api/ia/servicos',json={'politica':{'max_estimado_usd':0.01}})
        self.assertFalse(router.candidates(),'Unknown costs cannot satisfy a numeric ceiling')

    def test_task_specific_ranking_and_school_preference(self):
        self.connect('openai',True);self.connect('groq',True)
        def apply(reg):
            a=reg['servicos']['openai']['modelos'][0];b=reg['servicos']['groq']['modelos'][0]
            a.update(primeiro_token_ms=10,precos={'prompt':'0.001','completion':'0.001'})
            b.update(primeiro_token_ms=100,precos={'prompt':'0.0001','completion':'0.0001'})
        router.mutate(apply)
        self.assertEqual(router.candidates('chat')[0]['provedor'],'openai')
        self.assertEqual(router.candidates('insights')[0]['provedor'],'groq')
        self.client.put('/api/ia/servicos',json={'politica':{'preferidos':{'chat':'groq/fixture-text'}}})
        self.assertEqual(router.candidates('chat')[0]['provedor'],'groq')
        router.mutate(lambda reg:reg['servicos']['groq']['modelos'][0].update(pausado=True))
        self.assertEqual(router.candidates('chat')[0]['provedor'],'openai')

    def test_safe_rejection_fallback_records_both_attempts(self):
        self.connect('openai');self.connect('groq');self.activate()
        self.client.put('/api/ia/servicos',json={'politica':{'preferidos':{'chat':'openai/fixture-text'}}})
        calls=[]
        def stream(instance,*args):
            calls.append(instance.name)
            if instance.name=='openai':raise ProviderError('Modelo indisponível','modelo',safe_retry=True)
            yield 'Alternativa autorizada'
        with patch.object(Provider,'stream',stream):self.assertIn('Alternativa autorizada',self.chat())
        self.assertEqual(calls,['openai','groq'])
        self.assertEqual(self.sql('SELECT estado FROM IATentativas ORDER BY id'),[('interrompida',),('concluida',)])

    def test_no_fallback_after_partial_output_or_uncertain_network(self):
        self.connect('openai');self.connect('groq');self.activate()
        self.client.put('/api/ia/servicos',json={'politica':{'preferidos':{'chat':'openai/fixture-text'}}})
        calls=[]
        def partial(instance,*args):
            calls.append(instance.name);yield 'Parcial';raise ProviderError('Interrompida','modelo',safe_retry=True)
        with patch.object(Provider,'stream',partial):self.assertIn('Parcial',self.chat())
        self.assertEqual(calls,['openai'])
        router.mutate(lambda reg:[m.update(retomar_em=0) for s in reg['servicos'].values() for m in s['modelos']])
        calls.clear()
        def network(instance,*args):
            calls.append(instance.name);raise ProviderError('Rede incerta','rede');yield
        with patch.object(Provider,'stream',network):self.chat()
        self.assertEqual(len(calls),1)

    def test_paid_service_is_not_used_as_fallback_without_permission(self):
        self.connect('openai');self.connect('groq');self.activate()
        router.mutate(lambda reg:reg['servicos']['groq']['modelos'][0].update(precos=None))
        with patch.object(Provider,'stream',side_effect=ProviderError('Indisponível','modelo',True)) as stream:self.chat()
        self.assertEqual(stream.call_count,1)

    def test_replacement_is_staged_and_removal_destroys_only_requested_key(self):
        self.connect('openai');self.connect('groq');self.activate();store=self.app.extensions['secrets']
        self.client.put('/api/ia/servicos/openai',json={'chave':'replacement'})
        self.assertEqual(store.get('ia_openai'),'synthetic-openai')
        with patch.object(Provider,'models',side_effect=models),patch.object(Provider,'stream',side_effect=ProviderError('Chave inválida','chave')):
            self.assertEqual(self.client.post('/api/ia/servicos/openai/testar',json={}).status_code,503)
        self.assertTrue(rt.availability()['disponivel'])
        self.assertEqual(store.get('ia_openai'),'synthetic-openai')
        self.client.delete('/api/ia/servicos/openai',json={})
        self.assertIsNone(store.get('ia_openai'));self.assertIsNone(store.get('ia_pendente_openai'))
        self.assertEqual(store.get('ia_groq'),'synthetic-groq')

    def test_permissions_confirmation_expiration_and_no_secret_in_responses(self):
        self.connect()
        result=self.client.get('/api/ia/servicos')
        self.assertNotIn('synthetic-openai',result.get_data(as_text=True))
        self.assertNotIn('synthetic-openai',repr(self.sql('SELECT * FROM Configuracoes')))
        with self.client.session_transaction() as session:session['ia_confirmacao']={'conta':1,'em':0}
        self.assertEqual(self.client.put('/api/ia/servicos/openai',json={'chave':'new'}).status_code,403)
        self.assertEqual(self.client.put('/api/ia/servicos/openai',json={'habilitado':False}).status_code,200)
        reader=self.reader()
        self.sql("INSERT INTO Contas(id,leitor_id,nome,email,senha_hash,papel,ativacao) VALUES (2,?,'Leitor','reader@example.test',?,'leitor','presencial')",(reader,HASH))
        client=authenticate(self.app,self.app.test_client(),2)
        self.assertEqual(client.get('/api/ia/servicos').status_code,403)
        self.assertEqual(client.put('/api/ia/servicos',json={'ativa':True}).status_code,403)

    def test_limits_and_current_request_at_daily_boundary(self):
        self.connect();self.activate()
        self.client.put('/api/ia/servicos/openai',json={'limite_diario':1})
        with patch.object(Provider,'stream',side_effect=lambda *args:(x for x in ['Permitida'])):self.assertIn('Permitida',self.chat())
        self.assertFalse(rt.availability()['disponivel'])
        self.client.put('/api/ia/servicos/openai',json={'limite_diario':20})
        rt.runtime()['active']=8
        with patch.object(Provider,'stream') as stream:
            self.assertIn('outras conversas',self.chat());stream.assert_not_called()
        rt.runtime()['active']=0

    def test_migration_preserves_active_and_unused_credentials_without_network(self):
        cfg=rt.config()|{'ativa':True,'provedor':'openai','modelo':'legacy','privacidade_revisada':True}
        self.app.extensions['secrets'].set('ia_openai','old-key')
        self.app.extensions['secrets'].set('ia_anthropic','unused-key')
        self.sql("INSERT INTO Configuracoes VALUES ('ia',?)",(json.dumps(cfg),))
        rt.record_verification(cfg,True,'OK')
        with patch('requests.request',side_effect=AssertionError('No migration network')):router.migrate();router.migrate()
        self.assertTrue(rt.availability()['disponivel'])
        reg=router.read();self.assertIn('anthropic',reg['servicos'])
        self.assertFalse(reg['servicos']['openai']['custos_autorizados'])
        self.assertTrue(reg['servicos']['openai']['modelos'][0]['legado_autorizado'])
        self.assertEqual(self.app.extensions['secrets'].get('ia_anthropic'),'unused-key')
        self.client.put('/api/ia/servicos/openai',json={'custos_autorizados':False})
        self.assertFalse(rt.availability()['disponivel'],'Explicitly declining costs revokes migrated permission too')
