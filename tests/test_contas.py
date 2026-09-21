"""Autenticação real em bancos temporários, sem SMTP nem dados pessoais."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from app import create_app
from services.contas_service import digest


class ContaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = create_app({'DATA_DIR':self.temp.name,'TESTING':True})
        self.client = self.app.test_client()
        self.client.get('/configuracao-inicial')
        self.db = self.app.extensions['database']
        self.smtp = patch('smtplib.SMTP',side_effect=AssertionError('SMTP real proibido')).start()
        self.addCleanup(patch.stopall)

    def post(self,path,data,client=None,**kwargs):
        client = client or self.client
        csrf = client.get('/api/acesso/csrf').json['csrf']
        return client.post(path,json=data,headers={'X-CSRF-Token':csrf},**kwargs)

    def setup_library(self):
        response = self.post('/api/acesso/configurar',dict(nome='Bibliotecária',biblioteca='Escola',email='admin@example.test',senha='senha forte de teste',confirmacao='senha forte de teste'))
        self.assertEqual(response.status_code,200,response.json)
        return response.json['recuperacao_offline']

    def reader(self):
        with self.db.connection() as conn:
            cur=conn.execute("INSERT INTO Usuarios(nome,tipo,email) VALUES ('Leitor','professor','leitor@example.test')")
            conn.commit()
            return cur.lastrowid

    def activate(self,code,client=None,**extra):
        return self.post('/api/acesso/ativar',dict(email='leitor@example.test',codigo=code,senha='senha do leitor teste',confirmacao='senha do leitor teste',**extra),client)

    def test_setup_guard_and_offline(self):
        self.assertEqual(self.client.get('/configuracao-inicial',environ_overrides={'REMOTE_ADDR':'10.0.0.2'}).status_code,403)
        self.assertEqual(self.post('/api/leitores',{}).status_code,503)
        self.assertEqual(self.client.post('/api/acesso/configurar',json={}).status_code,403)
        code=self.setup_library()
        self.assertEqual(self.post('/api/acesso/configurar',{}).status_code,403)
        anonymous=self.app.test_client()
        self.assertEqual(anonymous.get('/api/leitores').status_code,401)
        self.assertEqual(anonymous.get('/app').status_code,302)
        self.assertEqual(self.client.get('/api/admin/status').json,{'admin':True})
        payload=dict(email='admin@example.test',codigo=code,senha='outra senha de teste',confirmacao='outra senha de teste')
        result=self.post('/api/acesso/recuperacao-local',payload)
        self.assertEqual(result.status_code,200,result.json)
        self.assertNotEqual(code,result.json['recuperacao_offline'])
        self.assertEqual(self.client.get('/api/leitores').status_code,401)
        self.assertEqual(self.post('/api/acesso/recuperacao-local',payload).status_code,400)

    def test_invite_identity_permissions_and_reissue(self):
        self.setup_library(); reader=self.reader()
        path=f'/api/contas/leitores/{reader}/codigo'
        first=self.post(path,{}).json['codigo']
        second=self.post(path,{}).json['codigo']
        guest=self.app.test_client()
        self.assertEqual(self.activate(first,guest).status_code,400)
        bad=dict(email='other@example.test',codigo=second,senha='senha do leitor teste',confirmacao='senha do leitor teste')
        self.assertEqual(self.post('/api/acesso/ativar',bad,guest).status_code,400)
        self.assertEqual(self.activate(second,guest,papel='bibliotecario',tipo='estudante').status_code,200)
        self.assertEqual(self.activate(second,guest).status_code,400)
        self.assertEqual(self.post('/api/acesso/entrar',dict(email='LEITOR@example.test',senha='senha do leitor teste'),guest).status_code,200)
        self.assertEqual(guest.get('/api/leitores').status_code,403)
        self.assertEqual(guest.get('/api/emprestimos/ranking-leitores').status_code,403)
        self.assertEqual(guest.get('/api/livros').status_code,200)
        with self.db.connection() as conn:
            self.assertEqual(conn.execute('SELECT papel,email_verificado,ativacao FROM Contas WHERE leitor_id=?',(reader,)).fetchone(),('leitor',0,'presencial'))
            self.assertEqual(conn.execute('SELECT tipo FROM Usuarios WHERE id=?',(reader,)).fetchone()[0],'professor')
            self.assertNotIn(second,repr(conn.execute('SELECT * FROM Codigos').fetchall()))
        reset=self.post(path,{'finalidade':'recuperacao'}).json['codigo']
        self.assertEqual(self.activate(reset,guest).status_code,400)
        result=self.post('/api/acesso/redefinir',dict(email='leitor@example.test',codigo=reset,senha='senha alterada teste',confirmacao='senha alterada teste'),guest)
        self.assertEqual(result.status_code,200,result.json)
        self.assertEqual(guest.get('/api/livros').status_code,401)

    def test_atomic_setup(self):
        def attempt(_):
            client=self.app.test_client()
            return self.post('/api/acesso/configurar',dict(nome='Admin',biblioteca='Escola',email='admin@example.test',senha='senha forte de teste',confirmacao='senha forte de teste'),client).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(attempt,range(2))),[200,403])
        with self.db.connection() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM Contas').fetchone()[0],1)

    def test_csrf_origin_logout_and_rate(self):
        self.setup_library()
        csrf=self.client.get('/api/acesso/csrf').json['csrf']
        response=self.client.post('/api/acesso/sair',json={},headers={'X-CSRF-Token':csrf,'Origin':'https://malicious.test'})
        self.assertEqual(response.status_code,403)
        self.assertEqual(self.post('/api/acesso/sair',{}).status_code,200)
        self.assertEqual(self.client.get('/api/leitores').status_code,401)
        for _ in range(8):
            self.assertEqual(self.post('/api/acesso/entrar',dict(email='none@example.test',senha='bad')).status_code,403)
        self.assertEqual(self.post('/api/acesso/entrar',dict(email='none@example.test',senha='bad')).status_code,429)

    def test_last_librarian(self):
        self.setup_library()
        csrf=self.client.get('/api/acesso/csrf').json['csrf']
        response=self.client.put('/api/contas/1',json=dict(papel='leitor',ativa=False,motivo='Teste',senha_atual='senha forte de teste'),headers={'X-CSRF-Token':csrf})
        self.assertEqual(response.status_code,400,response.json)


if __name__ == '__main__':
    unittest.main()
