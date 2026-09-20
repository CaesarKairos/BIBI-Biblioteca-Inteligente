"""Tests for approved corrections; no live database or external services."""
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import unittest
from unittest.mock import MagicMock, patch

from test_regression import modular, ROOT, TEMP
from database.database import db_manager
from services import emprestimos_service as loans, email_service, image_service, livros_service
from utils.datetime import get_brasilia_today

class ImprovementTests(unittest.TestCase):
    def setUp(self):
        self.stack=contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        directory=self.stack.enter_context(tempfile.TemporaryDirectory(dir=TEMP.name))
        self.stack.enter_context(patch.object(db_manager,'db_name',str(Path(directory)/'test.db')))
        db_manager.init_database()
        self.stack.enter_context(patch('requests.get',side_effect=AssertionError('Live HTTP forbidden')))
        self.smtp=self.stack.enter_context(patch('smtplib.SMTP'))
        self.client=modular.app.test_client()
        self.sql("UPDATE Configuracoes SET valor='true' WHERE chave='bloquear_email'")

    def sql(self,query,params=()):
        with db_manager.connection() as conn:
            result=conn.execute(query,params).fetchall()
            conn.commit()
            return result

    def book(self,stock=1):
        with db_manager.connection() as conn:
            cur=conn.execute("INSERT INTO Livros(nome,autor,estoque,quantidade_disponivel) VALUES('Livro','Autor',?,?)",(stock,stock))
            conn.commit()
            return cur.lastrowid

    def payload(self,book,email='ana@example.test',**overrides):
        data={'tipo':'estudante','nome':'Ana','email':email,'livros':[{'id':book,'quantidade':1}]}
        data.update(overrides)
        return data

    def credentials(self):
        for key,value in [('bloquear_email','false'),('email_organizacao','test@example.test'),('email_app_password','fake-secret')]:
            self.sql('UPDATE Configuracoes SET valor=? WHERE chave=?',(value,key))

    def test_invalid_loan_inputs_never_write(self):
        book=self.book()
        inputs=[None, [], 'invalid', {}, self.payload(book,livros=[]),self.payload(book,livros='invalid'),self.payload(book,livros=[None]),self.payload(book,livros=[{'id':book},{'id':book}])]
        for quantity in [0,-1,1.5,True,'2',None]: inputs.append(self.payload(book,livros=[{'id':book,'quantidade':quantity}]))
        for book_id in [0,-1,True,'1',None]: inputs.append(self.payload(book,livros=[{'id':book_id}]))
        for prazo in ['invalid',0,-1]: inputs.append(self.payload(book,prazo=prazo))
        for data in inputs:
            with self.subTest(data=data):
                result=loans.realizar_emprestimo(data)
                self.assertEqual(result[1],400)
                self.assertEqual(self.sql('SELECT COUNT(*) FROM Emprestimo')[0][0],0)
                self.assertEqual(self.sql('SELECT COUNT(*) FROM Usuarios')[0][0],0)
                self.assertEqual(self.sql('SELECT quantidade_disponivel FROM Livros')[0][0],1)

    def test_duplicate_return_does_not_increment_stock(self):
        book=self.book(2)
        self.assertEqual(self.client.post('/api/emprestimos',json=self.payload(book)).status_code,200)
        with patch.object(loans,'enviar_email_devolucao') as send:
            for _ in range(2):
                response=self.client.post('/api/emprestimos/1/devolver')
                self.assertEqual(response.status_code,200)
            send.assert_not_called() # blocked
        self.assertEqual(self.sql('SELECT quantidade_disponivel FROM Livros')[0][0],2)
        self.assertEqual(self.sql('SELECT status FROM Emprestimo')[0][0],'Devolvido')

    def test_concurrent_loans_cannot_oversell(self):
        book=self.book()
        barrier=threading.Barrier(2)
        def borrow(index):
            barrier.wait(timeout=5)
            with modular.app.test_client() as client:
                return client.post('/api/emprestimos',json=self.payload(book,email=f'user{index}@example.test')).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses=list(pool.map(borrow,[1,2]))
        self.assertEqual(sorted(statuses),[200,400])
        self.assertEqual(self.sql('SELECT quantidade_disponivel FROM Livros')[0][0],0)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM Emprestimo')[0][0],1)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM Usuarios')[0][0],1)

    def test_concurrent_returns_restore_only_once(self):
        book=self.book(); loans.realizar_emprestimo(self.payload(book))
        barrier=threading.Barrier(2)
        def give_back(_):
            barrier.wait(timeout=5)
            return loans.devolver_emprestimo(1)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(give_back,[1,2]))
        self.assertEqual(results,[{'status':'ok'},{'status':'ok'}])
        self.assertEqual(self.sql('SELECT quantidade_disponivel FROM Livros')[0][0],1)

    def test_transaction_rolls_back_all_books_and_reader(self):
        first=self.book(); second=self.book()
        self.sql(f"CREATE TRIGGER test_failure BEFORE INSERT ON Emprestimo WHEN NEW.livros_id={second} BEGIN SELECT RAISE(ABORT,'test failure'); END")
        with self.assertLogs('services.emprestimos_service',level='ERROR'):
            result=loans.realizar_emprestimo(self.payload(first,tipo='professor',livros=[{'id':first},{'id':second}]))
        self.assertEqual(result[1],500)
        self.assertEqual(self.sql('SELECT quantidade_disponivel FROM Livros'),[(1,),(1,)])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM Usuarios'),[(0,)])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM Emprestimo'),[(0,)])

    def test_connections_close_after_validation_error_and_exception(self):
        book=self.book(); connections=[]; connect=db_manager.get_connection
        def tracked():
            conn=connect(); connections.append(conn); return conn
        with patch.object(db_manager,'get_connection',side_effect=tracked):
            self.assertEqual(loans.realizar_emprestimo(self.payload(book,nome=''))[1],400)
        self.assertTrue(connections)
        for conn in connections:
            with self.assertRaises(sqlite3.ProgrammingError): conn.execute('SELECT 1')
        with self.assertRaises(RuntimeError):
            with db_manager.connection() as conn:
                conn.execute("UPDATE Livros SET estoque=999")
                raise RuntimeError('test')
        self.assertEqual(self.sql('SELECT estoque FROM Livros'),[(1,)])

    def test_email_response_reflects_smtp_result(self):
        for result in [False,True]:
            book=self.book(); self.credentials()
            with patch.object(loans,'enviar_email_confirmacao',return_value=result):
                response=self.client.post('/api/emprestimos',json=self.payload(book,email=f'{result}@example.test'))
            self.assertEqual(response.status_code,200)
            self.assertIs(response.json['email_enviado'],result)
        book=self.book()
        with patch.object(loans,'enviar_email_confirmacao',side_effect=RuntimeError('smtp failure')),self.assertLogs('services.emprestimos_service',level='ERROR'):
            response=self.client.post('/api/emprestimos',json=self.payload(book,email='failure@example.test'))
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.json['email_enviado'])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM Emprestimo'),[(3,)])

    def test_email_disabled_still_updates_overdue(self):
        book=self.book(); loans.realizar_emprestimo(self.payload(book))
        self.sql("UPDATE Emprestimo SET data_vencimento='2000-01-01'")
        with patch.object(email_service,'enviar_email_notificacao') as send:
            response=self.client.get('/api/emprestimos/atrasos')
            email_service.verificar_e_enviar_notificacoes()
            send.assert_not_called()
        self.assertEqual(len(response.json),1)
        self.assertEqual(self.sql('SELECT status FROM Emprestimo'),[('Atrasado',)])

    def test_notification_flags_follow_success_and_retries(self):
        for days,flag in [(3,'notificacao_3dias'),(0,'notificacao_hoje')]:
            with self.subTest(days=days):
                book=self.book(); loans.realizar_emprestimo(self.payload(book,email=f'{days}@example.test'))
                loan_id=self.sql('SELECT MAX(id) FROM Emprestimo')[0][0]
                self.sql('UPDATE Emprestimo SET data_vencimento=? WHERE id=?',((get_brasilia_today()+timedelta(days=days)).isoformat(),loan_id))
                self.sql("UPDATE Configuracoes SET valor='false' WHERE chave='bloquear_email'")
                with patch.object(email_service,'enviar_email_notificacao',return_value=False):
                    email_service.verificar_e_enviar_notificacoes()
                self.assertEqual(self.sql(f'SELECT {flag} FROM Emprestimo WHERE id=?',(loan_id,)),[(0,)])
                with patch.object(email_service,'enviar_email_notificacao',return_value=True) as send:
                    email_service.verificar_e_enviar_notificacoes()
                    email_service.verificar_e_enviar_notificacoes()
                    self.assertEqual(send.call_count,1)
                self.assertEqual(self.sql(f'SELECT {flag} FROM Emprestimo WHERE id=?',(loan_id,)),[(1,)])

    def test_parallel_notification_checks_send_only_once(self):
        book=self.book(); loans.realizar_emprestimo(self.payload(book))
        self.sql('UPDATE Emprestimo SET data_vencimento=?',(get_brasilia_today().isoformat(),))
        self.sql("UPDATE Configuracoes SET valor='false' WHERE chave='bloquear_email'")
        entered=threading.Event(); release=threading.Event()
        def send(*args):
            entered.set(); self.assertTrue(release.wait(5)); return True
        with patch.object(email_service,'enviar_email_notificacao',side_effect=send) as mocked:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first=pool.submit(email_service.verificar_e_enviar_notificacoes)
                self.assertTrue(entered.wait(5))
                second=pool.submit(email_service.verificar_e_enviar_notificacoes)
                try: second.result(timeout=5)
                finally: release.set()
                first.result(timeout=5)
            self.assertEqual(mocked.call_count,1)

    def test_book_cascade_fills_fields_in_order(self):
        calls=[]
        def provider(name,data):
            def run(*args): calls.append(name); return data
            return run
        with patch.object(livros_service,'buscar_open_library',side_effect=provider('ol',{'titulo':'Original'})),patch.object(livros_service,'buscar_brasil_api',side_effect=provider('br',{'titulo':'Other','autor':'Autor'})),patch.object(livros_service,'buscar_google_books_por_isbn',side_effect=provider('isbn',{'ano_publicacao':2000,'categoria':'Poesia','numero_paginas':240})),patch.object(livros_service,'buscar_google_books_por_titulo',side_effect=provider('title',{'descricao':'Descricao','temas':'Tema','capa':'https://example.test/cover.png'})):
            result=livros_service.buscar_livro_cascata('123')
        self.assertEqual(calls,['ol','br','isbn','title'])
        self.assertEqual(result['titulo'],'Original')
        self.assertTrue(all(value is not None for value in result.values()))
        with patch.object(livros_service,'buscar_open_library',return_value=result),patch.object(livros_service,'buscar_brasil_api') as fallback:
            self.assertEqual(livros_service.buscar_livro_cascata('123'),result)
            fallback.assert_not_called()

    def test_invalid_upload_and_real_image_content(self):
        invalid=self.client.post('/api/upload',data={'file':(io.BytesIO(b'<script>bad</script>'),'cover.png')})
        self.assertEqual(invalid.status_code,400)
        image=(ROOT/'static/images/placeholder.png').read_bytes()
        with tempfile.TemporaryDirectory(dir=TEMP.name) as folder,patch.dict(modular.app.config,UPLOAD_FOLDER=folder):
            response=self.client.post('/api/upload',data={'file':(io.BytesIO(image),'cover.jpg')})
            self.assertEqual(response.status_code,200)
            self.assertTrue(response.json['url'].endswith('.png'))
            self.assertEqual(len(list(Path(folder).iterdir())),1)
        with self.assertRaises(ValueError): image_service.validate_image(b'')

    def test_external_and_bundled_local_covers(self):
        image=(ROOT/'static/images/placeholder.png').read_bytes()
        with tempfile.TemporaryDirectory(dir=TEMP.name) as folder:
            Path(folder,'cover.png').write_bytes(image)
            with patch.object(image_service,'EXTERNAL_FOLDER',folder):
                self.assertEqual(image_service.get_book_cover_image_bytes('/externalcovers/cover.png'),(image,'png'))
                self.assertEqual(image_service.get_book_cover_image_bytes('/externalcovers/../outside.png'),(None,None))
            with patch.object(image_service,'STATIC_DIR',folder):
                self.assertEqual(image_service.get_book_cover_image_bytes('/static/cover.png'),(image,'png'))
        response=MagicMock(); response.__enter__.return_value=response; response.iter_content.return_value=[image]
        with patch.object(image_service.requests,'get',return_value=response):
            self.assertEqual(image_service.download_image_from_url('https://example.test/cover'),(image,'png'))
        response.__exit__.assert_called_once()

    def test_smtp_timeout_cleanup_and_safe_template_data(self):
        self.credentials()
        server=self.smtp.return_value.__enter__.return_value
        self.assertTrue(email_service.enviar_email_confirmacao('ana@example.test','<script>bad</script>','<b>Livro</b>','01/01/2030'))
        self.smtp.assert_called_once_with('smtp.gmail.com',587,timeout=15)
        message=server.send_message.call_args.args[0]
        html=next(part.get_payload(decode=True).decode() for part in message.walk() if part.get_content_type()=='text/html')
        self.assertIn('&lt;script&gt;',html)
        self.assertNotIn('<script>',html)
        self.smtp.return_value.__exit__.assert_called_once()
        server.send_message.side_effect=OSError('failure')
        with self.assertLogs('services.email_service',level='ERROR'):
            self.assertFalse(email_service.enviar_email_confirmacao('ana@example.test','Ana','Livro','01/01/2030'))
        self.assertEqual(self.smtp.return_value.__exit__.call_count,2)

    def test_http_errors_are_json_and_hide_tracebacks(self):
        self.assertEqual(self.client.post('/api/emprestimos',data='{',content_type='application/json').status_code,400)
        self.assertEqual(self.client.post('/api/emprestimos',data='x',content_type='text/plain').status_code,415)
        with patch.object(livros_service,'api_livros',side_effect=RuntimeError('PRIVATE-DETAIL')),self.assertLogs(modular.app.logger,level='ERROR'):
            response=self.client.get('/api/livros')
        self.assertEqual(response.status_code,500)
        self.assertTrue(response.is_json)
        self.assertNotIn('PRIVATE-DETAIL',response.get_data(as_text=True))

if __name__=='__main__': unittest.main()
