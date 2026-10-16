"""Integração, isolamento e migração dos fluxos de conta e shell."""
import sqlite3
import io
import json
import zipfile
import hashlib
from unittest.mock import patch
from tests.support import AppTest, authenticate, HASH, ROOT
from services.recuperacao_local import RecuperacaoDesktop
from services.avatar_service import default
from database.database import DatabaseManager


class IntegracaoBibiTests(AppTest):
    def reader_account(self):
        reader=self.reader()
        self.sql("INSERT INTO Contas(id,leitor_id,nome,email,senha_hash,papel,ativacao,onboarding_concluido_em) VALUES (2,?,'Ana','ana@example.test',?,'leitor','presencial',CURRENT_TIMESTAMP)",(reader,HASH))
        return authenticate(self.app,self.app.test_client(),2)

    def test_favorites_order_limits_archive_and_isolation(self):
        client=self.reader_account()
        books=[self.book() for _ in range(5)]
        put=lambda ids:client.put('/api/minha-conta/favoritos',json={'livros':ids})
        self.assertEqual(put(books[:4]).status_code,200)
        self.assertEqual(put(books).status_code,400)
        self.assertEqual(put([books[0],books[0]]).status_code,400)
        self.assertEqual(put([99999]).status_code,400)
        self.sql('UPDATE Livros SET arquivado=1 WHERE id IN (?,?)',(books[0],books[4]))
        self.assertEqual(put(list(reversed(books[:4]))).status_code,200)
        self.assertEqual([r['id'] for r in client.get('/api/minha-conta/favoritos').json],list(reversed(books[:4])))
        self.assertEqual(put([books[4]]).status_code,400)
        self.assertEqual(client.get('/api/minha-conta/quero-ler').json,[])
        self.assertEqual(self.client.get('/api/minha-conta/favoritos').status_code,403)
        self.assertEqual(put([]).status_code,200)
        self.assertEqual(put([books[0]]).status_code,400)
        self.assertEqual(self.sql('PRAGMA foreign_key_check'),[])

    def test_shell_roles_and_preferences(self):
        client=self.reader_account()
        for url in ('/perfil',):
            html=client.get(url).get_data(as_text=True)
            self.assertIn('resize-sidebar',html)
            self.assertIn('resize-details',html)
            self.assertNotIn('id="m-dash"',html)
            self.assertNotIn('id="m-age"',html)
            self.assertNotIn('smtp-form',html)
            self.assertNotIn('restore-form',html)
        for url in ('/api/gestao/saude','/api/contas','/api/config/email/status','/leitores/contas'):
            self.assertEqual(client.get(url).status_code,403)
        self.assertEqual(client.get('/api/minha-conta?conta_id=1').json['id'],2)
        self.assertEqual(client.put('/api/minha-conta/preferencias',json={'tema':'escuro','conta_id':1}).status_code,200)
        self.assertEqual(self.client.get('/api/minha-conta/preferencias').json['tema'],'claro')
        self.assertEqual(self.client.get('/gestao').location,'/configuracoes#gestao-config')
        self.assertEqual(self.client.get('/configuracoes?fragmento=1').get_data(as_text=True).count('id="smtp-form"'),1)

    def test_settings_fragment_roles_and_legacy_context(self):
        reader=self.reader_account()
        public=reader.get('/configuracoes?fragmento=1').get_data(as_text=True)
        self.assertIn('id="password-form"',public)
        self.assertIn('id="confirm-email-form"',public)
        for protected in ('invite-form','smtp-form','occurrence-form','csv-form','restore-form','audit-list'):
            self.assertNotIn('id="'+protected+'"',public)
        profile=reader.get('/perfil').get_data(as_text=True)
        self.assertNotIn('id="password-form"',profile)
        self.assertIn('id="settings-dialog"',profile)
        self.assertEqual(reader.get('/leitores/contas?leitor=7').status_code,403)
        self.assertEqual(self.client.get('/leitores/contas?leitor=7').location,'/app?config=gestao-convites&leitor=7')
        self.assertEqual(self.client.get('/leitores/importacao').location,'/app?config=dados&tipo=leitores')
        self.assertEqual(self.client.get('/acervo/importacao').location,'/app?config=dados&tipo=livros')
        self.assertEqual(self.client.get('/emprestimos/circulacao').location,'/app?config=circulacao')

    def test_onboarding_only_once(self):
        self.sql('UPDATE Contas SET onboarding_concluido_em=NULL WHERE id=1')
        self.assertEqual(self.client.get('/app').location,'/boas-vindas')
        self.assertEqual(self.client.get('/boas-vindas').status_code,200)
        self.assertEqual(self.client.put('/api/minha-conta/avatar',json=default()).status_code,200)
        self.assertEqual(self.client.get('/boas-vindas').location,'/app')
        self.assertEqual(self.client.get('/app').status_code,200)

    def test_desktop_capability_session_expiry_once_and_no_logs(self):
        payload={'email':'admin@example.test','senha':'nova senha protegida','confirmacao':'nova senha protegida'}
        self.assertEqual(self.client.post('/api/acesso/recuperacao-local',json=payload).status_code,403)
        manager=RecuperacaoDesktop(self.app.extensions['secrets'])
        self.app.extensions['desktop_recovery']=manager
        token=manager.abrir();payload['token']=token
        self.assertEqual(self.client.post('/api/acesso/recuperacao-local',json=payload).status_code,403)
        self.assertEqual(self.client.post('/api/acesso/recuperacao-desktop/sessao',json={'token':token},environ_overrides={'REMOTE_ADDR':'10.0.0.2'}).status_code,403)
        self.assertEqual(self.client.post('/api/acesso/recuperacao-desktop/sessao',json={'token':token}).status_code,200)
        other=self.app.test_client();other.get('/api/acesso/csrf')
        self.assertEqual(other.post('/api/acesso/recuperacao-local',json=payload).status_code,403)
        self.sql("INSERT INTO Codigos(conta_id,email,finalidade,entrega,hash,expira) VALUES (1,'admin@example.test','recuperacao','presencial','old',9999999999)")
        self.assertEqual(self.client.post('/api/acesso/recuperacao-local',json=payload).status_code,200)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM Sessoes'),[(0,)])
        self.assertEqual(self.sql('SELECT consumido FROM Codigos'),[(1,)])
        audit=repr(self.sql('SELECT * FROM Auditoria'))
        self.assertNotIn(token,audit);self.assertNotIn(payload['senha'],audit)
        self.client.get('/api/acesso/csrf')
        self.assertEqual(self.client.post('/api/acesso/recuperacao-local',json=payload).status_code,403)
        token=manager.abrir()
        manager.pending['expires']=0
        self.assertEqual(self.client.post('/api/acesso/recuperacao-desktop/sessao',json={'token':token}).status_code,403)

    def test_recovery_rate_and_pin_rejected(self):
        for _ in range(5):
            self.assertEqual(self.client.post('/api/acesso/recuperacao-local',json={}).status_code,403)
        self.assertEqual(self.client.post('/api/acesso/recuperacao-local',json={}).status_code,429)
        self.assertEqual(self.client.post('/api/config/senha/definir',json={'senha':'1234'}).status_code,410)
        self.assertFalse(self.client.post('/api/config/senha/verificar',json={'senha':'1234'}).json['valido'])
        self.assertTrue(self.client.post('/api/config/senha/verificar',json={'senha':'senha forte de teste'}).json['valido'])
        self.assertEqual(self.client.post('/api/config/email/set',json={'remover_credencial':True}).status_code,403)

    def test_smtp_single_contract_keeps_and_removes_protected_secret(self):
        payload={'smtp_host':'smtp.example.test','smtp_port':'587','email_organizacao':'biblioteca@example.test','email_app_password':'segredo-sintetico'}
        self.assertEqual(self.client.post('/api/config/email/set',json=payload).status_code,200)
        self.assertEqual(self.app.extensions['secrets'].get('smtp_password'),'segredo-sintetico')
        self.assertNotIn('segredo-sintetico',repr(self.client.get('/api/config/email/status').json))
        self.assertEqual(self.client.post('/api/config/email/set',json={**payload,'email_app_password':''}).status_code,200)
        self.assertEqual(self.app.extensions['secrets'].get('smtp_password'),'segredo-sintetico')
        with patch('services.mensagens_service.enviar',return_value=True):
            self.assertEqual(self.client.post('/api/gestao/email/testar',json={}).status_code,200)
        self.assertEqual(self.client.post('/api/config/email/set',json={**payload,'remover_credencial':True,'senha_atual':'senha forte de teste'}).status_code,200)
        self.assertIsNone(self.app.extensions['secrets'].get('smtp_password'))

    def test_restore_previous_version_migrates_without_manual_secret(self):
        old=self.directory/'before.db'
        conn=sqlite3.connect(old)
        conn.executescript((ROOT/'database/schema.sql').read_text(encoding='utf-8'))
        conn.execute('CREATE TABLE Migracoes(versao TEXT PRIMARY KEY,aplicada_em TEXT DEFAULT CURRENT_TIMESTAMP)')
        for version in ('001_contas','002_circulacao'):
            conn.executescript((ROOT/'database/migrations'/f'{version}.sql').read_text(encoding='utf-8'))
            conn.execute('INSERT INTO Migracoes(versao) VALUES (?)',(version,))
        conn.execute("INSERT INTO Contas(nome,email,senha_hash,papel,ativacao) VALUES ('Original','original@test',?,'bibliotecario','inicial')",(HASH,))
        conn.execute("INSERT INTO Livros(nome,autor,estoque,quantidade_disponivel) VALUES ('Histórico preservado','A',1,1)")
        conn.commit();conn.close()
        raw=old.read_bytes();upload=io.BytesIO()
        with zipfile.ZipFile(upload,'w') as archive:
            archive.writestr('Biblioteca.db',raw)
            archive.writestr('manifesto.json',json.dumps({'formato':1,'arquivos':{'Biblioteca.db':hashlib.sha256(raw).hexdigest()}}))
        upload.seek(0)
        before=self.app.extensions['secrets'].recovery_key()
        result=self.client.post('/api/gestao/restaurar',data={'arquivo':(upload,'old.zip'),'confirmado':'true','senha_atual':'senha forte de teste'})
        self.assertEqual(result.status_code,200,result.json)
        self.assertNotIn('recuperacao_offline',result.json)
        self.assertNotEqual(before,self.app.extensions['secrets'].recovery_key())
        self.assertEqual(self.sql('SELECT nome FROM Livros'),[('Histórico preservado',)])
        self.assertEqual(self.sql('SELECT recuperacao_hash FROM Contas'),[(None,)])
        self.assertTrue(list((self.directory/'backups').glob('antes-restauracao-migracao-*')))

    def test_old_accounts_migration_preserves_dates_avatar_and_recovery(self):
        path=self.directory/'old-accounts.db'
        conn=sqlite3.connect(path)
        conn.executescript((ROOT/'database/schema.sql').read_text(encoding='utf-8'))
        conn.execute('CREATE TABLE Migracoes(versao TEXT PRIMARY KEY,aplicada_em TEXT DEFAULT CURRENT_TIMESTAMP)')
        for version in ('001_contas','002_circulacao'):
            conn.executescript((ROOT/'database/migrations'/f'{version}.sql').read_text(encoding='utf-8'))
            conn.execute('INSERT INTO Migracoes(versao) VALUES (?)',(version,))
        conn.execute("INSERT INTO Contas(nome,email,senha_hash,papel,ativacao,avatar,criada_em,recuperacao_hash) VALUES ('A','a@test',?,'bibliotecario','inicial','{}','2025-01-02','legacy')",(HASH,))
        conn.execute("INSERT INTO Contas(nome,email,senha_hash,papel,ativacao) VALUES ('B','b@test',?,'bibliotecario','inicial')",(HASH,))
        conn.commit();conn.close()
        manager=DatabaseManager(path);manager.init_database()
        with manager.connection() as conn:
            self.assertEqual(conn.execute('SELECT onboarding_concluido_em,recuperacao_hash FROM Contas WHERE id=1').fetchone(),('2025-01-02','legacy'))
            self.assertIsNone(conn.execute('SELECT onboarding_concluido_em FROM Contas WHERE id=2').fetchone()[0])
            self.assertEqual(conn.execute("SELECT valor FROM Configuracoes WHERE chave='instalacao_criada_em'").fetchone()[0],'2025-01-02')
            self.assertEqual(conn.execute("SELECT valor FROM Configuracoes WHERE chave='instalacao_data_estimada'").fetchone()[0],'true')
        self.assertTrue(list((self.directory/'backups').glob('antes-migracao-*')))
