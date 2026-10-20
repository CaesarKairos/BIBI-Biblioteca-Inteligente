from tests import test_recursos
from tests.support import AppTest
import json
from datetime import timedelta
from unittest.mock import patch
from utils.datetime import get_brasilia_today


class ReadingTests(AppTest):
    reader_account=test_recursos.ResourceTests.reader_account

    def setUp(self):
        super().setUp()
        policy={'estudante':{'maximo':1,'prazo':7,'renovacoes':2,'bloquear_atraso':True},'professor':{'maximo':100,'prazo':1,'renovacoes':2,'bloquear_atraso':True},'retirada_horas':48}
        self.sql("INSERT OR REPLACE INTO Configuracoes VALUES ('circulacao',?)",(json.dumps(policy),))
    def test_read_marker_is_voluntary_private_and_idempotent(self):
        book=self.book(2);reader,client=self.reader_account();_,other=self.reader_account('other@example.test')
        self.client.post('/api/emprestimos',json={'leitor_id':reader,'livros':[{'id':book}]})
        self.assertEqual(client.get('/api/minha-conta/lidos').json,[])
        for _ in range(2):
            self.assertEqual(client.post(f'/api/minha-conta/lidos/{book}').status_code,200)
        self.assertEqual(len(client.get('/api/minha-conta/lidos').json),1)
        self.assertEqual(other.get('/api/minha-conta/lidos').json,[])
        other.delete(f'/api/minha-conta/lidos/{book}')
        self.assertEqual(len(client.get('/api/minha-conta/lidos').json),1)
        self.assertEqual(self.sql('SELECT quantidade_disponivel FROM Livros'),[(1,)])
        self.assertEqual(self.client.post(f'/api/minha-conta/lidos/{book}').status_code,400)
        client.delete(f'/api/minha-conta/lidos/{book}')
        self.assertEqual(client.get('/api/minha-conta/lidos').json,[])
        self.assertEqual(client.post('/api/minha-conta/lidos/99999').status_code,404)

    def test_reservation_cancellation_notifies_once_without_smtp(self):
        book=self.book();reader,client=self.reader_account();borrower=self.reader(email='borrow@example.test')
        self.client.post('/api/emprestimos',json={'leitor_id':borrower,'livros':[{'id':book}]})
        client.post(f'/api/minha-conta/reservas/{book}')
        reservation=client.get('/api/minha-conta/reservas').json[0]['id']
        for _ in range(2):
            self.assertEqual(client.delete(f'/api/minha-conta/reservas/{reservation}').status_code,200)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM Notificacoes WHERE evento LIKE 'reserva-cancelada:%'"),[(1,)])
        self.assertTrue(any('cancelada' in n['mensagem'] for n in client.get('/api/minha-conta/notificacoes').json))

    def test_due_late_return_renewal_and_moderation_notifications_without_smtp(self):
        from services.email_service import verificar_e_enviar_notificacoes
        book=self.book();reader,client=self.reader_account()
        self.client.post('/api/emprestimos',json={'leitor_id':reader,'livros':[{'id':book}]})
        with patch('smtplib.SMTP',side_effect=AssertionError('SMTP real proibido')):
            self.sql('UPDATE Emprestimo SET data_vencimento=?',(get_brasilia_today().isoformat(),))
            verificar_e_enviar_notificacoes();verificar_e_enviar_notificacoes()
            self.sql('UPDATE Emprestimo SET data_vencimento=?',((get_brasilia_today()-timedelta(days=1)).isoformat(),))
            verificar_e_enviar_notificacoes();verificar_e_enviar_notificacoes()
            self.assertEqual(self.sql("SELECT COUNT(*) FROM Notificacoes WHERE evento LIKE 'prazo:%'"),[(2,)])
            client.post('/api/minha-conta/emprestimos/1/renovacao')
            self.client.post('/api/gestao/renovacoes/1/recusar',json={'motivo':'Conferir com a biblioteca'})
            client.post(f'/api/minha-conta/avaliacoes/{book}',json={'estrelas':4,'comentario':'Reflexão sobre a obra'})
            self.client.put('/api/gestao/avaliacoes/1',json={'estado':'oculto','motivo':'Revisão de teste'})
            self.client.post('/api/emprestimos/1/devolver')
            verificar_e_enviar_notificacoes()
        messages=' '.join(n['mensagem'] for n in client.get('/api/minha-conta/notificacoes').json)
        for expected in ['Empréstimo registrado','prevista','recusado','devolução']:
            self.assertIn(expected,messages)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM Notificacoes WHERE evento LIKE 'moderacao:%'"),[(1,)])

    def test_read_marker_survives_restart_and_portable_backup(self):
        import io
        import sqlite3
        import zipfile
        from app import create_app
        from tests.support import AuthClient,authenticate
        book=self.book();_,client=self.reader_account()
        client.post(f'/api/minha-conta/lidos/{book}')
        response=self.client.post('/api/gestao/backup')
        with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
            snapshot=self.directory/'snapshot.db';snapshot.write_bytes(archive.read('Biblioteca.db'))
        response.close()
        conn=sqlite3.connect(snapshot)
        try:self.assertEqual(conn.execute('SELECT COUNT(*) FROM LeiturasConcluidas').fetchone()[0],1)
        finally:conn.close()
        restarted=create_app({'TESTING':True,'DATA_DIR':str(self.directory)})
        restarted.test_client_class=AuthClient
        with restarted.app_context():
            after=authenticate(restarted,restarted.test_client(),2)
            self.assertEqual(after.get('/api/minha-conta/lidos').json[0]['id'],book)
