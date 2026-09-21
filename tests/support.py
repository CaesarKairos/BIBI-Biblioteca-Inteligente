"""Fixtures autenticadas; nenhuma permissão decorre do IP do cliente."""
import contextlib
from pathlib import Path
import tempfile
import unittest
from werkzeug.security import generate_password_hash
from flask.testing import FlaskClient
from app import create_app

ROOT=Path(__file__).resolve().parents[1]
TEMP=tempfile.TemporaryDirectory(prefix='bibi-tests-')
HASH=generate_password_hash('senha forte de teste',method='scrypt')


class AuthClient(FlaskClient):
    """Somente fixtures usam cookie/sessão sem passar pelo formulário a cada teste."""
    def open(self,*args,**kwargs):
        with self.session_transaction() as session:
            token=session.get('csrf')
        if token:
            headers=dict(kwargs.get('headers') or {})
            headers.setdefault('X-CSRF-Token',token)
            kwargs['headers']=headers
        return super().open(*args,**kwargs)


def authenticate(app,client,account_id=1):
    import secrets,time
    from services.contas_service import digest
    raw=secrets.token_urlsafe(32)
    with app.extensions['database'].connection() as conn:
        row=conn.execute('SELECT versao_sessao FROM Contas WHERE id=?',(account_id,)).fetchone()
        conn.execute('INSERT INTO Sessoes VALUES (?,?,?,?)',(digest(raw),account_id,row[0],int(time.time())+3600));conn.commit()
    with client.session_transaction() as session:
        session['sid']=raw;session['csrf']=secrets.token_urlsafe(32)
    return client


class AppTest(unittest.TestCase):
    def setUp(self):
        self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close)
        self.directory=Path(self.stack.enter_context(tempfile.TemporaryDirectory(dir=TEMP.name)))
        self.app=create_app({'TESTING':True,'DATA_DIR':str(self.directory)})
        self.app.test_client_class=AuthClient
        self.stack.enter_context(self.app.app_context())
        self.db=self.app.extensions['database']
        with self.db.connection() as conn:
            conn.execute("INSERT INTO Contas(id,nome,email,senha_hash,papel,ativacao) VALUES (1,'Admin','admin@example.test',?,'bibliotecario','inicial')",(HASH,));conn.commit()
        self.client=authenticate(self.app,self.app.test_client())

    def sql(self,query,params=()):
        with self.db.connection() as conn:
            result=conn.execute(query,params).fetchall();conn.commit();return result

    def book(self,stock=1):
        self.sql("INSERT INTO Livros(nome,autor,estoque,quantidade_disponivel) VALUES ('Livro','Autora',?,?)",(stock,stock))
        return self.sql('SELECT MAX(id) FROM Livros')[0][0]

    def reader(self,name='Ana',email='ana@example.test',tipo='estudante'):
        self.sql('INSERT INTO Usuarios(nome,tipo,email) VALUES (?,?,?)',(name,tipo,email))
        return self.sql('SELECT MAX(id) FROM Usuarios')[0][0]
