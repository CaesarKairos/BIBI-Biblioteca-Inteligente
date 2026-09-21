"""Regressões de circulação, imagens e entrega: fixtures autenticadas e sem rede real."""
import io
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from tests.support import AppTest,authenticate,ROOT
from services import image_service,livros_service


class ImprovementTests(AppTest):
    def payload(self,book,**extra):
        return dict(nome='Ana',tipo='estudante',email='ana@example.test',livros=[{'id':book}],**extra)

    def test_invalid_loan_inputs_never_write(self):
        book=self.book()
        for value in [None,[],{},'invalid',{'livros':[]},{'livros':[None]}]+[self.payload(book)|{'livros':[{'id':book,'quantidade':q}]} for q in [0,-1,1.5,True,'2',None]]:
            response=self.client.post('/api/emprestimos',json=value)
            self.assertIn(response.status_code,(400,415),response.json)
            self.assertEqual(self.sql('SELECT COUNT(*) FROM Emprestimo'),[(0,)])
            self.assertEqual(self.sql('SELECT COUNT(*) FROM Usuarios'),[(0,)])

    def test_concurrent_loans_and_idempotent_return(self):
        book=self.book();clients=[authenticate(self.app,self.app.test_client()) for _ in range(2)]
        def borrow(i):
            return clients[i].post('/api/emprestimos',json=self.payload(book)|{'email':f'a{i}@example.test'}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(borrow,[0,1])),[200,400])
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(lambda i:clients[i].post('/api/emprestimos/1/devolver').status_code,[0,1])),[200,200])
        self.assertEqual(self.sql('SELECT quantidade_disponivel FROM Livros'),[(1,)])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM Notificacoes WHERE evento='devolucao:1'"),[(1,)])

    def test_transaction_rolls_back_all_books_and_reader(self):
        a=self.book();b=self.book()
        self.sql(f"CREATE TRIGGER test_failure BEFORE INSERT ON Emprestimo WHEN NEW.livros_id={b} BEGIN SELECT RAISE(ABORT,'test failure'); END")
        response=self.client.post('/api/emprestimos',json=self.payload(a)|{'tipo':'professor','livros':[{'id':a},{'id':b}]})
        self.assertEqual(response.status_code,409)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM Usuarios'),[(0,)])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM Emprestimo'),[(0,)])
        self.assertEqual(self.sql('SELECT quantidade_disponivel FROM Livros'),[(1,),(1,)])

    def test_reader_id_not_silent_identity_update(self):
        reader=self.reader();book=self.book()
        result=self.client.post('/api/emprestimos',json={'leitor_id':reader,'nome':'Troca maliciosa','tipo':'professor','livros':[{'id':book}]})
        self.assertEqual(result.status_code,200,result.json)
        self.assertEqual(self.sql('SELECT nome,tipo FROM Usuarios'),[('Ana','estudante')])
        self.assertFalse(result.json['email_enviado'])

    def test_archive_and_stock_consistency(self):
        book=self.book(2)
        self.assertEqual(self.client.post('/api/emprestimos',json=self.payload(book)).status_code,200)
        self.assertEqual(self.client.delete('/api/livros/'+str(book)).status_code,400)
        self.assertEqual(self.client.delete('/api/leitores/1').status_code,400)
        self.assertEqual(self.client.put('/api/livros/'+str(book),json=dict(titulo='Livro',autor='Autora',estoque=2,disponivel=2)).status_code,400)
        self.client.post('/api/emprestimos/1/devolver')
        self.assertEqual(self.client.delete('/api/livros/'+str(book)).status_code,200)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM Emprestimo'),[(1,)])
        self.assertEqual(self.client.get('/api/livros').json,[])

    def test_loss_is_not_a_return(self):
        book=self.book();self.client.post('/api/emprestimos',json=self.payload(book))
        r=self.client.post('/api/gestao/ocorrencias',json=dict(tipo='perda',livro_id=book,emprestimo_id=1,quantidade=1,observacao='Perda conferida'))
        self.assertEqual(r.status_code,200,r.json)
        self.assertEqual(self.sql('SELECT estoque,quantidade_disponivel FROM Livros'),[(0,0)])
        self.assertEqual(self.client.post('/api/emprestimos/1/devolver').status_code,400)
        self.assertEqual(self.client.get('/api/emprestimos/ativos').json,[])

    def test_invalid_upload_and_image_content(self):
        response=self.client.post('/api/upload',data={'file':(io.BytesIO(b'<script>x</script>'),'cover.png')})
        self.assertEqual(response.status_code,400)
        image=(ROOT/'static/images/placeholder.png').read_bytes()
        response=self.client.post('/api/upload',data={'file':(io.BytesIO(image),'cover.jpg')})
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.json['url'].endswith('.png'))
        with self.client.get(response.json['url']) as asset:
            self.assertEqual(asset.data,image)
        for url in ['http://127.0.0.1/private','https://169.254.169.254/latest','file:///secret','https://attacker.test/cover']:
            self.assertEqual(image_service.download_image_from_url(url),(None,None))

    def test_cascade_precedence_and_fallback(self):
        with patch.object(livros_service,'buscar_open_library',return_value={'titulo':'Original'}),patch.object(livros_service,'buscar_brasil_api',return_value={'titulo':'Outro','autor':'Autora'}),patch.object(livros_service,'buscar_google_books_por_isbn',return_value={'numero_paginas':240}),patch.object(livros_service,'buscar_google_books_por_titulo',return_value={'descricao':'Texto'}):
            result=livros_service.buscar_livro_cascata('123')
        self.assertEqual(result['titulo'],'Original');self.assertEqual(result['numero_paginas'],240)

    def test_http_errors_do_not_expose_details(self):
        self.assertEqual(self.client.post('/api/emprestimos',data='{',content_type='application/json').status_code,400)
        self.assertEqual(self.client.post('/api/emprestimos',data='x',content_type='text/plain').status_code,415)
        with patch.object(livros_service,'api_livros',side_effect=RuntimeError('PRIVATE-DETAIL')):
            response=self.client.get('/api/livros')
        self.assertEqual(response.status_code,500)
        self.assertNotIn('PRIVATE-DETAIL',response.get_data(as_text=True))
