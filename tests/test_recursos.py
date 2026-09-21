import io
import json
import time
import zipfile
from unittest.mock import patch
from tests.support import AppTest,authenticate,HASH
from services.circulacao_service import processar_expiracoes
from services.mensagens_service import processar_fila


class ResourceTests(AppTest):
    def setUp(self):
        super().setUp()
        # Políticas sintéticas explícitas do cenário, não defaults impostos à escola.
        policy={'estudante':{'maximo':1,'prazo':7,'renovacoes':2,'bloquear_atraso':True},'professor':{'maximo':100,'prazo':1,'renovacoes':2,'bloquear_atraso':True},'retirada_horas':48}
        self.sql("INSERT OR REPLACE INTO Configuracoes VALUES ('circulacao',?)",(json.dumps(policy),))
    def reader_account(self,email='leitor@example.test'):
        reader=self.reader(email=email)
        self.sql("INSERT INTO Contas(leitor_id,nome,email,senha_hash,papel,ativacao) VALUES (?,'Leitor',?,?,'leitor','presencial')",(reader,email,HASH))
        account=self.sql('SELECT MAX(id) FROM Contas')[0][0]
        return reader,authenticate(self.app,self.app.test_client(),account)

    def test_reservation_queue_multiple_expiration_and_pickup(self):
        book=self.book(2);r1,c1=self.reader_account();r2,c2=self.reader_account('second@example.test')
        borrower=self.reader(email='borrower@example.test',tipo='professor')
        response=self.client.post('/api/emprestimos',json={'leitor_id':borrower,'livros':[{'id':book,'quantidade':2}]})
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(c1.post(f'/api/minha-conta/reservas/{book}').status_code,200)
        self.assertEqual(c2.post(f'/api/minha-conta/reservas/{book}').status_code,200)
        self.assertEqual(c2.get('/api/minha-conta/reservas').json[0]['posicao'],2)
        self.assertEqual(c2.delete('/api/minha-conta/reservas/1').status_code,404)
        self.client.post('/api/emprestimos/1/devolver')
        self.assertEqual(self.sql('SELECT quantidade_disponivel FROM Livros'),[(0,)])
        self.assertEqual(self.sql('SELECT estado FROM Reservas'),[('retirada',),('retirada',)])
        self.assertEqual(self.client.post('/api/emprestimos',json={'leitor_id':borrower,'livros':[{'id':book}]}).status_code,400)
        self.assertEqual(self.client.post('/api/emprestimos',json={'leitor_id':r1,'livros':[{'id':book}]}).status_code,200)
        self.sql("UPDATE Reservas SET expira=1 WHERE estado='retirada'")
        processar_expiracoes();processar_expiracoes()
        self.assertEqual(self.sql('SELECT quantidade_disponivel FROM Livros'),[(1,)])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM Notificacoes WHERE evento LIKE ?',('reserva-disponivel:%',)),[(2,)])

    def test_wishlist_does_not_change_stock_and_is_private(self):
        book=self.book();r,c=self.reader_account();r2,c2=self.reader_account('second@example.test')
        for _ in range(2):
            self.assertEqual(c.post('/api/minha-conta/quero-ler/'+str(book)).status_code,200)
        self.assertEqual(len(c.get('/api/minha-conta/quero-ler').json),1)
        self.assertEqual(c2.get('/api/minha-conta/quero-ler').json,[])
        self.assertEqual(self.sql('SELECT quantidade_disponivel FROM Livros'),[(1,)])
        self.assertEqual(c.post('/api/minha-conta/reservas/'+str(book)).status_code,400)

    def test_personal_history_and_manual_renewal(self):
        book=self.book();r,c=self.reader_account();_,other=self.reader_account('second@example.test')
        self.client.post('/api/emprestimos',json={'leitor_id':r,'livros':[{'id':book}]})
        old=self.sql('SELECT data_vencimento FROM Emprestimo')[0][0]
        self.assertEqual(other.post('/api/minha-conta/emprestimos/1/renovacao').status_code,404)
        self.assertEqual(c.post('/api/minha-conta/emprestimos/1/renovacao').status_code,200)
        self.assertEqual(self.sql('SELECT data_vencimento FROM Emprestimo')[0][0],old)
        self.assertEqual(self.client.post('/api/emprestimos/1/renovar').status_code,200)
        self.assertGreater(self.sql('SELECT data_vencimento FROM Emprestimo')[0][0],old)
        self.assertEqual(other.get('/api/minha-conta/emprestimos').json,[])

    def test_local_avatar_validated_and_persistent(self):
        _,client=self.reader_account()
        with patch('requests.get',side_effect=AssertionError('No avatar network')):
            result=client.get('/api/minha-conta/avatar')
            self.assertEqual(result.status_code,200,result.json)
            data=result.json['config'];data['opcoes']={'eyesVariant':'variant02','backgroundColor':'#f0ccaa'}
            self.assertEqual(client.post('/api/minha-conta/avatar/previa',json=data).status_code,200)
            self.assertEqual(client.put('/api/minha-conta/avatar',json=data).status_code,200)
            self.assertEqual(client.get('/api/minha-conta/avatar').json['config'],data)
            self.assertEqual(client.put('/api/minha-conta/avatar',json=data|{'opcoes':{'url':'http://evil.test'}}).status_code,400)

    def test_reviews_moderation_and_safe_public_fields(self):
        book=self.book();_,c=self.reader_account();_,other=self.reader_account('second@example.test')
        self.assertEqual(c.post('/api/minha-conta/avaliacoes/'+str(book),json=dict(estrelas=4,comentario='<script>alert(1)</script>')).status_code,200)
        public=other.get('/api/minha-conta/avaliacoes/'+str(book)).json[0]
        self.assertEqual(set(public),{'estrelas','comentario','atualizada_em'})
        self.assertEqual(other.get('/api/minha-conta/avaliacoes').json,[])
        self.assertEqual(c.post('/api/minha-conta/avaliacoes/'+str(book),json=dict(estrelas=4,comentario='idiota')).status_code,200)
        self.assertEqual(other.get('/api/minha-conta/avaliacoes/'+str(book)).json,[])
        self.assertEqual(self.client.put('/api/gestao/avaliacoes/1',json=dict(estado='oculto',motivo='Revisado')).status_code,200)
        self.assertEqual(c.get('/api/minha-conta/avaliacoes').json[0]['motivo'],'Revisado')

    def test_csv_preview_import_duplicates_and_safe_export(self):
        content='titulo;autor;quantidade\nLivro;Autora;2\nOutro;Autor;invalido\n'
        preview=self.client.post('/api/gestao/csv/livros/previa',json={'conteudo':content}).json
        self.assertTrue(preview['linhas'][1]['erros'])
        self.assertEqual(self.client.post('/api/gestao/csv/livros/importar',json={'conteudo':content,'confirmado':True}).status_code,400)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM Livros'),[(0,)])
        content='ISBN;Nome;Escritor;Exemplares\nTEST;=formula;Autora;2\n'
        data={'conteudo':content,'mapeamento':{'isbn':'ISBN','titulo':'Nome','autor':'Escritor','quantidade':'Exemplares'},'confirmado':True}
        self.assertEqual(self.client.post('/api/gestao/csv/livros/importar',json=data).status_code,200)
        self.assertEqual(self.client.post('/api/gestao/csv/livros/importar',json=data).status_code,400)
        reader=self.reader();self.client.post('/api/emprestimos',json={'leitor_id':reader,'livros':[{'id':1}]})
        text=self.client.get('/api/gestao/exportar/emprestimos').get_data(as_text=True)
        self.assertIn("'=formula",text)

    def test_backup_restoration_and_bad_paths(self):
        book=self.book();reader,client=self.reader_account()
        response=self.client.post('/api/gestao/backup');raw=response.data;response.close()
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            self.assertIn('manifesto.json',archive.namelist())
            self.assertNotIn('segredos.dpapi',archive.namelist())
        self.sql("UPDATE Livros SET nome='Alterado'")
        response=self.client.post('/api/gestao/restaurar',data={'arquivo':(io.BytesIO(raw),'backup.zip'),'confirmado':'true'})
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(self.sql('SELECT nome FROM Livros'),[('Livro',)])
        self.assertEqual(client.get('/api/minha-conta').status_code,401)
        authenticate(self.app,self.client)
        invalid=io.BytesIO()
        with zipfile.ZipFile(invalid,'w') as archive:
            archive.writestr('../escape','bad')
        response=self.client.post('/api/gestao/restaurar',data={'arquivo':(io.BytesIO(invalid.getvalue()),'bad.zip'),'confirmado':'true'})
        self.assertEqual(response.status_code,400)

    def test_email_verified_only_persistent_queue_and_retry(self):
        reader,client=self.reader_account()
        self.sql("INSERT INTO Notificacoes(leitor_id,evento,mensagem) VALUES (?,'event','Mensagem')",(reader,))
        self.sql("INSERT OR REPLACE INTO Configuracoes VALUES ('email_organizacao','test@example.test')")
        self.app.extensions['secrets'].set('smtp_password','fake')
        with patch('services.mensagens_service.enviar',return_value=True) as send:
            processar_fila();send.assert_not_called()
            self.sql('UPDATE Contas SET email_verificado=1 WHERE leitor_id=?',(reader,))
            processar_fila();processar_fila();self.assertEqual(send.call_count,1)
        self.assertEqual(self.sql('SELECT estado FROM FilaEmail'),[('aceito',)])

    def test_email_invite_failure_revokes_without_claiming_success(self):
        reader=self.reader()
        with patch('services.mensagens_service.enviar',return_value=False):
            response=self.client.post('/api/contas/leitores/'+str(reader)+'/email',json={})
        self.assertEqual(response.status_code,400)
        self.assertEqual(self.sql('SELECT consumido FROM Codigos'),[(1,)])
        with patch('services.mensagens_service.enviar',return_value=True):
            response=self.client.post('/api/contas/leitores/'+str(reader)+'/email',json={})
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM Contas WHERE leitor_id=?',(reader,)),[(0,)])

    def test_smtp_secret_not_plaintext_and_restart_key_stable(self):
        self.client.post('/api/config/email/set',json={'email_organizacao':'test@example.test','email_app_password':'test-private-password'})
        self.assertEqual(self.sql("SELECT valor FROM Configuracoes WHERE chave='email_app_password'"),[('',)])
        self.assertNotIn(b'test-private-password',(self.directory/'segredos.dpapi').read_bytes())
        from app import create_app
        second=create_app({'DATA_DIR':str(self.directory),'TESTING':True})
        self.assertEqual(second.secret_key,self.app.secret_key)

    def test_verified_email_and_reset_are_separate_flows(self):
        reader,client=self.reader_account()
        with patch('services.mensagens_service.enviar',return_value=True) as send:
            result=client.post('/api/minha-conta/email/enviar',json={'email':'leitor@example.test','senha_atual':'senha forte de teste'})
            self.assertEqual(result.status_code,200,result.json)
            import re
            code=re.search(r': ([A-Z2-9]{16})',send.call_args.args[2]).group(1)
            self.assertEqual(self.sql('SELECT email_verificado FROM Contas WHERE leitor_id=?',(reader,)),[(0,)])
            self.assertEqual(client.post('/api/minha-conta/email/confirmar',json={'email':'leitor@example.test','codigo':code}).status_code,200)
            self.assertEqual(client.get('/api/minha-conta').status_code,401)
            self.assertEqual(self.sql('SELECT email_verificado FROM Contas WHERE leitor_id=?',(reader,)),[(1,)])
            guest=self.app.test_client();guest.get('/api/acesso/csrf')
            self.assertEqual(guest.post('/api/acesso/recuperacao-email',json={'email':'leitor@example.test'}).status_code,200)
            recovery=re.search(r': ([A-Z2-9]{16})',send.call_args.args[2]).group(1)
            self.assertNotEqual(code,recovery)
            payload={'email':'leitor@example.test','codigo':code,'senha':'senha nova de teste','confirmacao':'senha nova de teste'}
            self.assertEqual(guest.post('/api/acesso/redefinir',json=payload).status_code,400)
            payload['codigo']=recovery
            self.assertEqual(guest.post('/api/acesso/redefinir',json=payload).status_code,200)

    def test_policies_preserve_dates_and_skip_ineligible_queue(self):
        held_book=self.book();other_book=self.book();r1,c1=self.reader_account();r2,c2=self.reader_account('second@example.test')
        borrower=self.reader(email='borrower@example.test',tipo='professor')
        first=self.client.post('/api/emprestimos',json={'leitor_id':r1,'livros':[{'id':other_book}]}).json['emprestimos'][0]
        loan=self.client.post('/api/emprestimos',json={'leitor_id':borrower,'livros':[{'id':held_book}]}).json['emprestimos'][0]
        c1.post(f'/api/minha-conta/reservas/{held_book}');c2.post(f'/api/minha-conta/reservas/{held_book}')
        self.client.post(f'/api/emprestimos/{loan}/devolver')
        self.assertEqual(self.sql('SELECT leitor_id FROM Reservas WHERE estado=?',('retirada',)),[(r2,)])
        before=self.sql('SELECT data_vencimento FROM Emprestimo WHERE id=?',(first,))
        policy=self.client.get('/api/gestao/configuracao').json['circulacao'];policy['estudante']['prazo']=21
        self.assertEqual(self.client.put('/api/gestao/configuracao',json={'circulacao':policy}).status_code,200)
        self.assertEqual(self.sql('SELECT data_vencimento FROM Emprestimo WHERE id=?',(first,)),before)
        report=self.client.get('/api/gestao/exportar/emprestimos?formato=agregado').get_data(as_text=True)
        self.assertNotIn('Leitor',report);self.assertNotIn('Ana',report);self.assertIn('Exemplares emprestados',report)
