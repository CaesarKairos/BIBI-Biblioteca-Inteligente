"""Configurações exercitadas nas operações reais, com banco temporário."""
from unittest.mock import patch
from tests.support import AppTest


class SettingsEffectsTests(AppTest):
    def test_circulation_settings_change_actual_deadlines_limits_and_renewals(self):
        from datetime import timedelta
        from utils.datetime import get_brasilia_today
        policies={'estudante':{'maximo':2,'prazo':10,'renovacoes':0,'bloquear_atraso':True},'professor':{'maximo':3,'prazo':15,'renovacoes':1,'bloquear_atraso':False},'retirada_horas':48}
        self.assertEqual(self.client.put('/api/gestao/configuracao',json={'circulacao':policies}).status_code,200)
        book=self.book(6);reader=self.reader();teacher=self.reader('Prof','prof@example.test','professor')
        self.assertEqual(self.client.post('/api/emprestimos',json={'leitor_id':reader,'livros':[{'id':book,'quantidade':2}]}).status_code,200)
        self.assertEqual(self.sql('SELECT data_vencimento FROM Emprestimo WHERE id=1')[0][0],(get_brasilia_today()+timedelta(days=10)).isoformat())
        self.assertEqual(self.client.post('/api/emprestimos',json={'leitor_id':reader,'livros':[{'id':book}]}).status_code,400)
        self.assertEqual(self.client.post('/api/emprestimos/1/renovar').status_code,400)
        self.assertEqual(self.client.post('/api/emprestimos',json={'leitor_id':teacher,'livros':[{'id':book}]}).status_code,200)
        self.assertEqual(self.sql('SELECT data_vencimento FROM Emprestimo WHERE id=2')[0][0],(get_brasilia_today()+timedelta(days=15)).isoformat())
        self.assertEqual(self.client.post('/api/emprestimos/2/renovar').status_code,200)
        self.assertEqual(self.client.post('/api/emprestimos/2/renovar').status_code,400)
        self.sql("UPDATE Emprestimo SET data_vencimento='2000-01-01' WHERE id=1")
        policies['estudante']['maximo']=3
        self.client.put('/api/gestao/configuracao',json={'circulacao':policies})
        self.assertEqual(self.client.post('/api/emprestimos',json={'leitor_id':reader,'livros':[{'id':book}]}).status_code,400)
        policies['estudante']['bloquear_atraso']=False
        self.client.put('/api/gestao/configuracao',json={'circulacao':policies})
        self.assertEqual(self.client.post('/api/emprestimos',json={'leitor_id':reader,'livros':[{'id':book}]}).status_code,200)

    def test_csv_respects_required_fields_in_preview_and_confirmation(self):
        self.fields(campoNumeroUsuario=True)
        self.client.post('/api/config/obrigar_localizacao_livro/set',json={'ativo':True})
        for kind,content in [('livros','titulo;autor;quantidade\nLivro;Autora;1\n'),('leitores','nome;tipo\nAna;estudante\n')]:
            data={'conteudo':content,'confirmado':True}
            result=self.client.post(f'/api/gestao/csv/{kind}/previa',json=data)
            self.assertTrue(result.json['linhas'][0]['erros'])
            self.assertEqual(self.client.post(f'/api/gestao/csv/{kind}/importar',json=data).status_code,400)

    def test_password_confirmation_on_agenda_is_applied_and_reversible(self):
        agenda=dict(data='2099-01-05',periodo='Manhã',dia=1,aula=1,professor='Prof',materia='Arte',uso='Leitura')
        path='/api/config/exigir_senha_agendamento/set'
        self.assertEqual(self.client.post(path,json={'ativo':True}).status_code,403)
        self.assertEqual(self.client.post(path,json={'ativo':True,'senha_atual':'senha forte de teste'}).status_code,200)
        self.assertEqual(self.client.post('/api/agendamentos',json=agenda).status_code,403)
        self.assertEqual(self.client.post('/api/agendamentos',json=agenda|{'senha':'senha forte de teste'}).status_code,201)
        self.client.post(path,json={'ativo':False,'senha_atual':'senha forte de teste'})
        self.assertEqual(self.client.post('/api/agendamentos',json=agenda|{'aula':2}).status_code,201)

    def fields(self, **values):
        response=self.client.put('/api/config/cadastro',json=values)
        self.assertEqual(response.status_code,200,response.json)
        return response.json

    def test_partial_changes_preserve_other_settings_and_validate_types(self):
        self.fields(campoNumeroUsuario=True,campoDescricaoVisivel=False)
        self.assertEqual(self.fields(mostrarColunaAula=False),dict(campoNumeroUsuario=True,campoDescricaoVisivel=False,mostrarColunaAula=False))
        for data in [[],None,{'campoNumeroUsuario':'false'},{'unknown':True}]:
            response=self.client.put('/api/config/cadastro',json=data)
            self.assertIn(response.status_code,(400,415))

    def test_phone_required_only_when_enabled_and_preserved_when_hidden(self):
        body=dict(nome='Estudante',tipo='estudante',sala='9A',periodo='Manhã')
        reader=self.client.post('/api/leitores',json=body).json['id']
        self.fields(campoNumeroUsuario=True)
        self.assertEqual(self.client.post('/api/leitores',json=body).status_code,400)
        self.assertEqual(self.client.put(f'/api/leitores/{reader}',json=body).status_code,400)
        body['telefone']='(11) 99999-9999'
        self.assertEqual(self.client.put(f'/api/leitores/{reader}',json=body).status_code,200)
        self.fields(campoNumeroUsuario=False)
        del body['telefone']
        self.assertEqual(self.client.put(f'/api/leitores/{reader}',json=body).status_code,200)
        self.assertEqual(self.sql('SELECT telefone FROM Usuarios WHERE id=?',(reader,))[0][0],'(11) 99999-9999')

    def test_phone_enforced_in_loan_backend_and_saved_for_existing_reader(self):
        book=self.book(3);reader=self.reader()
        self.fields(campoNumeroUsuario=True)
        loan=dict(leitor_id=reader,livros=[{'id':book}])
        self.assertEqual(self.client.post('/api/emprestimos',json=loan).status_code,400)
        loan['telefone']='11999999999'
        self.assertLess(self.client.post('/api/emprestimos',json=loan).status_code,300)
        self.assertEqual(self.sql('SELECT telefone FROM Usuarios WHERE id=?',(reader,))[0][0],loan['telefone'])
        self.assertEqual(self.client.post('/api/emprestimos',json=dict(nome='Outra',tipo='estudante',livros=[{'id':book}])).status_code,400)

    def test_location_required_on_create_and_edit_and_optional_when_disabled(self):
        book=self.book()
        self.client.post('/api/config/obrigar_localizacao_livro/set',json={'ativo':True})
        body=dict(manual=True,titulo='Livro novo',autor='Autora',quantidade=1)
        self.assertEqual(self.client.post('/api/livros',json=body).status_code,400)
        self.assertEqual(self.client.put(f'/api/livros/{book}',json=dict(titulo='Livro',autor='Autora')).status_code,400)
        self.assertEqual(self.client.put(f'/api/livros/{book}',json=dict(titulo='Livro',autor='Autora',localizacao='A1')).status_code,200)
        self.client.post('/api/config/obrigar_localizacao_livro/set',json={'ativo':False})
        self.assertLess(self.client.post('/api/livros',json=body).status_code,300)

    def test_email_block_covers_direct_messages_and_no_smtp_calls(self):
        from services.mensagens_service import enviar
        self.client.post('/api/config/bloquear_email/set',json={'bloqueado':True})
        result=self.client.post('/api/gestao/email/testar',json={})
        self.assertEqual(result.status_code,400)
        self.assertIn('bloqueado',result.json['erro'])
        with self.app.app_context(),patch('services.mensagens_service.smtp_config',side_effect=AssertionError('Não deve preparar envio bloqueado')):
            self.assertFalse(enviar('x@example.test','Teste','Mensagem'))

    def test_lesson_count_enforced_and_future_appointments_not_hidden(self):
        agenda=dict(data='2099-01-05',periodo='Manhã',dia=1,aula=7,professor='Prof',materia='Arte',uso='Leitura')
        self.assertEqual(self.client.post('/api/agendamentos',json=agenda).status_code,400)
        self.client.post('/api/config/quantidade_aulas/set',json={'quantidade':8})
        self.assertEqual(self.client.post('/api/agendamentos',json=agenda).status_code,201)
        self.assertEqual(self.client.post('/api/config/quantidade_aulas/set',json={'quantidade':6}).status_code,400)
        self.assertEqual(self.client.get('/api/config/quantidade_aulas/status').json['quantidade'],8)
        self.client.post('/api/config/bloquear_excluir_agendamento/set',json={'ativo':True})
        self.assertEqual(self.client.delete('/api/agendamentos/1').status_code,403)
        self.client.post('/api/config/bloquear_excluir_agendamento/set',json={'ativo':False})
        self.assertEqual(self.client.delete('/api/agendamentos/1').status_code,200)
        self.assertEqual(self.client.post('/api/config/quantidade_aulas/set',json={'quantidade':6}).status_code,200)
