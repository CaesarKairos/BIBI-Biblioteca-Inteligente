"""Número de páginas: API, fontes externas e migração sem dados reais."""
import contextlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from tests.support import AppTest, ROOT, TEMP
from database.database import DatabaseManager, db_manager
from services import livros_service as books


class PageTests(AppTest):
    def setUp(self):
        super().setUp()
        self.http = self.stack.enter_context(patch('requests.get', side_effect=AssertionError('Live HTTP forbidden')))

    def payload(self, **extra):
        return dict(manual=True, titulo='Livro de páginas', autor='Autora', quantidade=2, **extra)

    def test_create_with_and_without_pages_and_public_api(self):
        for value in [None, '', 1, 240, '320']:
            with self.subTest(value=value):
                response = self.client.post('/api/livros', json=self.payload(numero_paginas=value))
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json['numero_paginas'], int(value) if value else None)
        response = self.client.post('/api/livros', json=self.payload())
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.json['numero_paginas'])
        public = self.client.get('/api/livros', environ_overrides={'REMOTE_ADDR': '127.0.0.1'})
        self.assertEqual(public.status_code, 200)
        self.assertEqual(len(public.json), 6)
        self.assertEqual(public.json[3]['numero_paginas'], 240)

    def test_invalid_pages_never_write(self):
        for value in [0, -1, 1.5, True, False, '1.5', 'abc', [], {}, 2**63]:
            with self.subTest(value=value):
                result = self.client.post('/api/livros', json=self.payload(numero_paginas=value))
                self.assertEqual(result.status_code, 400)
        self.assertEqual(self.client.get('/api/livros').json, [])

    def test_edit_clear_omit_and_invalid_are_atomic(self):
        book = self.client.post('/api/livros', json=self.payload(numero_paginas=100)).json
        url = f"/api/livros/{book['id']}"
        payload = dict(titulo=book['titulo'], autor=book['autor'], estoque=2, disponivel=2, categoria='Poesia')
        for extra, expected in [({'numero_paginas': 500}, 500), ({}, 500), ({'numero_paginas': None}, None), ({'numero_paginas': '220'}, 220)]:
            self.assertEqual(self.client.put(url, json={**payload, **extra}).status_code, 200)
            self.assertEqual(self.client.get('/api/livros').json[0]['numero_paginas'], expected)
        for invalid in [-1, 0, '3.5', True, []]:
            self.assertEqual(self.client.put(url, json={**payload, 'numero_paginas': invalid, 'titulo': 'Não salvar', 'capa': 'changed'}).status_code, 400)
        current = self.client.get('/api/livros').json[0]
        self.assertEqual(current['numero_paginas'], 220)
        self.assertEqual(current['titulo'], book['titulo'])
        self.assertEqual(current['capa'], book['capa'])

    def test_non_admin_cannot_mutate_pages(self):
        guest = self.app.test_client()
        guest.get('/api/acesso/csrf')
        for method, url in [('POST', '/api/livros'), ('PUT', '/api/livros/1'), ('DELETE', '/api/livros/1')]:
            self.assertEqual(guest.open(url, method=method, json=self.payload(numero_paginas=200)).status_code, 401)

    def test_old_database_migration_idempotent_preserves_data(self):
        # Schema anterior literal: a coluna nova realmente não existe.
        path = self.directory / 'old.db'
        schema = (ROOT / 'database/schema.sql').read_text(encoding='utf-8')
        schema = '\n'.join(line for line in schema.splitlines() if 'numero_paginas' not in line)
        with contextlib.closing(sqlite3.connect(path)) as conn, conn:
            conn.executescript(schema)
            conn.execute("INSERT INTO Livros (isbn,nome,autor,estoque,quantidade_disponivel) VALUES ('old','Preservado','Autor',3,2)")
            conn.execute("INSERT INTO Usuarios (nome,tipo,email) VALUES ('Ana','estudante','ana@test')")
            conn.execute("INSERT INTO Emprestimo (usuarios_id,livros_id,quantidade,data_emprestimo,data_vencimento) VALUES (1,1,1,'2026-01-01','2026-01-08')")
            conn.execute("INSERT INTO Configuracoes VALUES ('quantidade_aulas','12')")
            self.assertNotIn('numero_paginas', [r[1] for r in conn.execute('PRAGMA table_info(Livros)')])
        manager = DatabaseManager(str(path))
        with manager.connection() as conn:
            self.assertEqual(conn.execute('SELECT nome,estoque,quantidade_disponivel,numero_paginas FROM Livros').fetchone(), ('Preservado',3,2,None))
            conn.execute('UPDATE Livros SET numero_paginas=345')
            conn.commit()
        manager.init_database()
        manager.init_database()
        with manager.connection() as conn:
            self.assertEqual(conn.execute('SELECT numero_paginas FROM Livros').fetchone(), (345,))
            self.assertEqual(conn.execute('SELECT usuarios_id,livros_id,quantidade FROM Emprestimo').fetchone(), (1,1,1))
            self.assertEqual(conn.execute("SELECT valor FROM Configuracoes WHERE chave='quantidade_aulas'").fetchone(), ('12',))
            self.assertEqual([r[1] for r in conn.execute('PRAGMA table_info(Livros)')].count('numero_paginas'), 1)
            for invalid in [0,-1,2.5,'invalid']:
                with self.assertRaises(sqlite3.IntegrityError):
                    conn.execute('UPDATE Livros SET numero_paginas=?', (invalid,))

    def test_real_provider_field_names_and_optional_fallback(self):
        for value, expected in [(321,321),(None,None),(0,None),('bad',None),(2.5,None),(True,None)]:
            self.http.side_effect = None
            self.http.return_value = MagicMock(status_code=200)
            with self.subTest(provider='Open Library', value=value):
                self.http.return_value.json.return_value = {'ISBN:123': {'title':'Livro','authors':[{'name':'A'}], 'number_of_pages':value}}
                self.assertEqual(books.buscar_open_library('123')['numero_paginas'], expected)
            with self.subTest(provider='BrasilAPI', value=value):
                self.http.return_value.json.return_value = {'title':'Livro','authors':['A'],'page_count':value}
                self.assertEqual(books.buscar_brasil_api('123')['numero_paginas'], expected)
            with self.subTest(provider='Google Books', value=value):
                self.http.return_value.json.return_value = {'items':[{'volumeInfo':{'title':'Livro','authors':['A'],'pageCount':value}}]}
                self.assertEqual(books.buscar_google_books_por_isbn('123')['numero_paginas'], expected)
                self.assertEqual(books.buscar_google_books_por_titulo('Livro')['numero_paginas'], expected)

    def test_isbn_cascade_saves_pages_and_all_sources_without_pages(self):
        base = dict(titulo='Livro ISBN', autor='Autora', ano_publicacao=2000, descricao='Texto', temas='Tema', categoria='Ficção', capa='cover')
        for index, value in enumerate([None, 280]):
            with patch.object(books, 'buscar_open_library', return_value=base), patch.object(books, 'buscar_brasil_api', return_value={'numero_paginas': value}), patch.object(books, 'buscar_google_books_por_isbn', return_value=None), patch.object(books, 'buscar_google_books_por_titulo', return_value=None):
                response = self.client.post('/api/livros', json={'isbn': f'ISBN-{index}', 'quantidade': 1})
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json['numero_paginas'], value)
        self.assertEqual([l['numero_paginas'] for l in self.client.get('/api/livros').json], [None,280])

    def test_external_failure_does_not_discard_earlier_metadata(self):
        self.http.side_effect = [MagicMock(status_code=200, json=lambda: {'ISBN:123': {'title':'Livro', 'authors':[{'name':'A'}]}}), RuntimeError('offline'), RuntimeError('offline'), RuntimeError('offline')]
        with self.assertLogs('services.livros_service', level='ERROR'):
            result = self.client.post('/api/livros', json={'isbn':'123','quantidade':1})
        self.assertEqual(result.status_code, 201)
        self.assertIsNone(result.json['numero_paginas'])


if __name__ == '__main__':
    unittest.main()
