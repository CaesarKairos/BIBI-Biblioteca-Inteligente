"""Conexao SQLite, schema e compatibilidade com bancos existentes."""
import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path
from config import DB_NAME

class DatabaseManager:
    def __init__(self, db_name=DB_NAME, initialize=True):
        self.db_name = db_name
        if initialize:
            self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_name)
        try:
            cursor = conn.cursor()

            cursor.executescript(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))

            conn.execute("BEGIN IMMEDIATE")
            migrations = (
                ('Agendamento', 'data', 'TEXT'),
                ('Livros', 'data_cadastro', "TEXT NOT NULL DEFAULT ''"),
                ('Usuarios', 'telefone', 'TEXT'),
                ('Livros', 'localizacao', 'TEXT'),
                ('Livros', 'numero_paginas', "INTEGER CHECK (numero_paginas IS NULL OR (typeof(numero_paginas) = 'integer' AND numero_paginas > 0))"),
            )
            for table, column, definition in migrations:
                columns = {row[1] for row in cursor.execute(f'PRAGMA table_info({table})')}
                if column not in columns:
                    cursor.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
                    logging.getLogger(__name__).info('Coluna adicionada: %s.%s', table, column)
            # A data original de cadastro não existe nesses bancos legados.
            # Usa a data da migração somente nos registros sem data conhecida.
            cursor.execute("UPDATE Livros SET data_cadastro = date('now') WHERE data_cadastro IS NULL OR data_cadastro = ''")

            cursor.execute("INSERT OR IGNORE INTO Configuracoes (chave, valor) VALUES ('bloquear_email', 'false')")
            cursor.execute("INSERT OR IGNORE INTO Configuracoes (chave, valor) VALUES ('exigir_senha_emprestimo', 'false')")
            cursor.execute("INSERT OR IGNORE INTO Configuracoes (chave, valor) VALUES ('obrigar_localizacao_livro', 'false')")
            cursor.execute("INSERT OR IGNORE INTO Configuracoes (chave, valor) VALUES ('exigir_senha_agendamento', 'false')")
            cursor.execute("INSERT OR IGNORE INTO Configuracoes (chave, valor) VALUES ('bloquear_excluir_agendamento', 'true')")
            cursor.execute("INSERT OR IGNORE INTO Configuracoes (chave, valor) VALUES ('quantidade_aulas', '6')")
            cursor.execute("INSERT OR IGNORE INTO Configuracoes (chave, valor) VALUES ('email_organizacao', '')")
            cursor.execute("INSERT OR IGNORE INTO Configuracoes (chave, valor) VALUES ('email_app_password', '')")

            conn.commit()
        finally:
            conn.close()

    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            return conn
        except Exception:
            conn.close()
            raise

    @contextmanager
    def connection(self):
        conn = self.get_connection()
        try:
            yield conn
        finally:
            conn.close()

# Inicializado explicitamente por app.py, antes do registro das rotas.
db_manager = DatabaseManager(initialize=False)

def initialize_database():
    db_manager.init_database()
    return db_manager
