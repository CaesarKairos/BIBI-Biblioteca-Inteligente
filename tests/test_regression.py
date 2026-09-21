"""Contratos atuais substituem equivalência insegura com autorização por IP."""
import io
import contextlib
import re
import sqlite3
from unittest.mock import patch
from tests.support import AppTest,ROOT
from database.database import DatabaseManager


class RegressionTests(AppTest):
    def test_all_administrative_get_routes(self):
        guest=self.app.test_client()
        for rule in self.app.url_map.iter_rules():
            if rule.rule.startswith('/api/') and '<' not in rule.rule and 'GET' in rule.methods and not rule.rule.startswith(('/api/acesso','/api/minha-conta')):
                with self.subTest(rule=rule.rule):
                    response=self.client.get(rule.rule)
                    self.assertLess(response.status_code,500,response.data)
                    if rule.rule!='/api/hero-image':
                        self.assertEqual(guest.get(rule.rule).status_code,401)

    def test_configuration_and_agenda_contracts(self):
        for amount,status in [(0,400),(21,400),('6',400),(8,200)]:
            self.assertEqual(self.client.post('/api/config/quantidade_aulas/set',json={'quantidade':amount}).status_code,status)
        self.assertEqual(self.client.get('/api/config/quantidade_aulas/status').json['quantidade'],8)
        agenda=dict(data='2099-01-05',periodo='Manhã',dia=1,aula=2,professor='Prof',materia='Arte',uso='Leitura',turma='9A')
        result=self.client.post('/api/agendamentos',json=agenda)
        self.assertIn(result.status_code,(200,201),result.json)
        self.assertEqual(len(self.client.get('/api/agendamentos?data=2099-01-05&periodo=Manhã').json),1)
        self.client.post('/api/config/bloquear_excluir_agendamento/set',json={'ativo':False})
        self.assertEqual(self.client.delete('/api/agendamentos/1').status_code,200)

    def test_templates_keep_dom_contracts(self):
        html=self.client.get('/app').get_data(as_text=True)
        old=(ROOT/'docs/template_bindings.json').read_text(encoding='utf-8')
        for id in ('busca-acervo','lista-ativos','busca-emprestimos','acervo-prateleiras','info-livro','fechar-detalhes','resize-sidebar','resize-details','bibi-heading','manual-paginas','edit-paginas'):
            self.assertIn(f'id="{id}"',html)
        self.assertNotIn('✦',html)
        self.assertIn('data-admin="true"',html)
        self.assertNotRegex(html,r'<script>')
        for name in ('app','landing','contas'):
            with self.client.get('/static/css/'+name+'.css') as asset:
                self.assertEqual(asset.status_code,200)

    def test_migration_preserves_history_and_backs_up(self):
        path=self.directory/'legacy.db'
        schema=(ROOT/'database/schema.sql').read_text(encoding='utf-8')
        with contextlib.closing(sqlite3.connect(path)) as conn,conn:
            conn.executescript(schema)
            conn.execute("INSERT INTO Livros(nome,autor,estoque,quantidade_disponivel) VALUES ('História','Autor',2,1)")
            conn.execute("INSERT INTO Usuarios(nome,tipo) VALUES ('Leitor legado','bibliotecario')")
            conn.execute("INSERT INTO Emprestimo(usuarios_id,livros_id,data_emprestimo,data_vencimento) VALUES (1,1,'2020-01-01','2020-01-08')")
        manager=DatabaseManager(str(path));manager.init_database()
        with manager.connection() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM Contas').fetchone()[0],0)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM Emprestimo').fetchone()[0],1)
            self.assertEqual(conn.execute('SELECT quantidade_disponivel FROM Livros').fetchone()[0],1)
            self.assertEqual(conn.execute('PRAGMA foreign_keys').fetchone()[0],1)
        self.assertTrue(list((self.directory/'backups').glob('antes-migracao-*.db')))

    def test_migration_does_not_delete_orphans(self):
        path=self.directory/'orphan.db'
        with contextlib.closing(sqlite3.connect(path)) as conn,conn:
            conn.executescript((ROOT/'database/schema.sql').read_text(encoding='utf-8'))
            conn.execute("INSERT INTO Emprestimo(usuarios_id,livros_id,data_emprestimo,data_vencimento) VALUES (99,99,'2020-01-01','2020-01-08')")
        with self.assertRaisesRegex(RuntimeError,'órfãs'):
            DatabaseManager(str(path))
        with contextlib.closing(sqlite3.connect(path)) as conn,conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM Emprestimo').fetchone()[0],1)

    def test_import_has_no_desktop_or_workers(self):
        self.assertNotIn('notification_worker',self.app.extensions)
        import app
        self.assertFalse(hasattr(app,'app'))
        self.assertNotIn('load_dotenv',(ROOT/'config.py').read_text())

    def test_search_unknown_category_and_combined_filters(self):
        self.sql("INSERT INTO Livros(nome,autor,estoque,quantidade_disponivel,categoria,temas,localizacao) VALUES ('Coração','Érica',1,1,'Foreign category','Memória','A2')")
        result=self.client.get('/api/livros?paginado=1&q=ERICA+memoria+a2&disponibilidade=disponivel&categoria=Ficção').json
        self.assertEqual(result['total'],1)
        self.assertEqual(result['livros'][0]['categoria'],'Foreign category')
        self.assertEqual(result['livros'][0]['prateleira'],'Ficção')
        self.assertEqual(self.client.get('/api/livros?paginado=1&disponibilidade=indisponivel').json['total'],0)
