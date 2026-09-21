"""Integração de políticas, revogação e restauração, sempre com dados sintéticos."""
import io
import hashlib
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch,Mock
from tests.support import AppTest,authenticate,HASH
from services.contas_service import digest


class IntegrationTests(AppTest):
    def test_expired_revoked_and_concurrent_invite(self):
        reader=self.reader()
        path=f'/api/contas/leitores/{reader}/codigo'
        def activate(code):
            client=self.app.test_client();client.get('/api/acesso/csrf')
            return client.post('/api/acesso/ativar',json={'email':'ana@example.test','codigo':code,'senha':'senha de teste leitor','confirmacao':'senha de teste leitor'}).status_code
        code=self.client.post(path,json={}).json['codigo']
        self.sql('UPDATE Codigos SET expira=1')
        self.assertEqual(activate(code),400)
        code=self.client.post(path,json={}).json['codigo']
        self.client.delete(path)
        self.assertEqual(activate(code),400)
        code=self.client.post(path,json={}).json['codigo']
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(activate,[code,code])),[200,400])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM Contas WHERE leitor_id=?',(reader,)),[(1,)])

    def test_role_change_and_block_revoke_current_sessions(self):
        reader=self.reader()
        self.sql("INSERT INTO Contas(leitor_id,nome,email,senha_hash,papel,ativacao) VALUES (?,'Ana','ana@example.test',?,'leitor','presencial')",(reader,HASH))
        client=authenticate(self.app,self.app.test_client(),2)
        payload={'papel':'bibliotecario','ativa':True,'motivo':'Equipe','senha_atual':'senha forte de teste'}
        self.assertEqual(self.client.put('/api/contas/2',json=payload).status_code,200)
        self.assertEqual(client.get('/api/minha-conta').status_code,401)
        authenticate(self.app,client,2)
        self.assertEqual(client.get('/api/leitores').status_code,200)
        payload['ativa']=False
        self.assertEqual(self.client.put('/api/contas/2',json=payload).status_code,200)
        self.assertEqual(client.get('/api/leitores').status_code,401)

    def test_network_host_https_cookie_and_public_text(self):
        guest=self.app.test_client()
        self.assertEqual(guest.get('/acesso',environ_overrides={'REMOTE_ADDR':'10.1.1.2'}).status_code,403)
        self.assertEqual(guest.get('/acesso',base_url='https://evil.test').status_code,400)
        self.sql("INSERT INTO Configuracoes VALUES ('endereco_rede','https://biblioteca.example.test')")
        response=guest.get('/acesso',base_url='https://biblioteca.example.test',environ_overrides={'REMOTE_ADDR':'10.1.1.2'})
        self.assertEqual(response.status_code,200)
        self.assertIn('Secure;',response.headers.get('Set-Cookie',''))
        self.sql("INSERT INTO Configuracoes VALUES ('termos_uso','<script>segredo</script>')")
        response=guest.get('/instituicao')
        self.assertEqual(response.status_code,200)
        self.assertIn(b'&lt;script&gt;',response.data)
        self.assertEqual(guest.get('/api/leitores').status_code,401)

    def test_optional_pin_enforced_server_side(self):
        book=self.book();reader=self.reader()
        self.sql("INSERT OR REPLACE INTO Configuracoes VALUES ('exigir_senha_emprestimo','true')")
        self.sql("INSERT OR REPLACE INTO Configuracoes VALUES ('senha_hash',?)",(hashlib.sha256(b'123456').hexdigest(),))
        payload={'leitor_id':reader,'livros':[{'id':book}]}
        self.assertEqual(self.client.post('/api/emprestimos',json=payload).status_code,400)
        self.assertEqual(self.sql('SELECT quantidade_disponivel FROM Livros'),[(1,)])
        payload['senha']='123456'
        self.assertEqual(self.client.post('/api/emprestimos',json=payload).status_code,200)

    def test_restore_invalidates_codes_and_rotates_offline(self):
        reader=self.reader()
        self.client.post(f'/api/contas/leitores/{reader}/codigo',json={})
        self.sql('UPDATE Contas SET recuperacao_hash=? WHERE id=1',(digest('old-code'),))
        response=self.client.post('/api/gestao/backup');raw=response.data;response.close()
        self.app.extensions['secrets'].set('smtp_password','old credential')
        result=self.client.post('/api/gestao/restaurar',data={'arquivo':(io.BytesIO(raw),'backup.zip'),'confirmado':'true'})
        self.assertEqual(result.status_code,200,result.json)
        self.assertEqual(self.sql('SELECT DISTINCT consumido FROM Codigos'),[(1,)])
        self.assertEqual(self.sql('SELECT recuperacao_hash FROM Contas WHERE id=1'),[(digest(result.json['recuperacao_offline']),)])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM Sessoes'),[(0,)])
        self.assertIsNone(self.app.extensions['secrets'].get('smtp_password'))

    def test_restore_failure_rolls_back_database(self):
        self.book()
        response=self.client.post('/api/gestao/backup');raw=response.data;response.close()
        self.sql("UPDATE Livros SET nome='Estado atual'")
        # Falha depois de copiar o banco: o snapshot original precisa voltar intacto.
        from services.dados_service import auditar as actual
        def fail(conn,action,*args,**kwargs):
            if action=='restaurar':
                raise RuntimeError('Falha simulada')
            return actual(conn,action,*args,**kwargs)
        with patch('services.dados_service.auditar',side_effect=fail):
            result=self.client.post('/api/gestao/restaurar',data={'arquivo':(io.BytesIO(raw),'backup.zip'),'confirmado':'true'})
        self.assertEqual(result.status_code,500)
        self.assertEqual(self.sql('SELECT nome FROM Livros'),[('Estado atual',)])
        self.assertEqual(self.client.get('/api/leitores').status_code,200)

    def test_desktop_explicit_start_and_close(self):
        import desktop
        server=Mock();window=Mock()
        with patch.dict('sys.modules',{'webview':window}),patch.object(desktop,'create_server',return_value=server),patch('services.email_service.iniciar_verificacao_notificacoes') as worker,patch.object(desktop.threading,'Thread'):
            desktop.run_desktop(self.app)
        worker.assert_called_once_with(self.app)
        window.create_window.assert_called_once()
        server.close.assert_called_once()
