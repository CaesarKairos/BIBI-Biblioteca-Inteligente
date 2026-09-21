"""Conexao SQLite, schema e compatibilidade com bancos existentes."""
import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path
from config import DB_NAME
from flask import current_app, has_app_context
from datetime import datetime
import threading

operation_lock = threading.RLock()
# Envio externo pode ser lento: bloqueia restauração, não o uso normal da biblioteca.
maintenance_lock = threading.RLock()

class DatabaseManager:
    def __init__(self, db_name=DB_NAME, initialize=True):
        self.db_name = db_name
        if initialize:
            self.init_database()

    def init_database(self):
        Path(self.db_name).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_name)
        try:
            cursor = conn.cursor()
            # Backup online consistente (inclui páginas no WAL), antes de qualquer migração.
            versions = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            applied = {r[0] for r in conn.execute('SELECT versao FROM Migracoes')} if 'Migracoes' in versions else set()
            scripts = sorted(Path(__file__).with_name('migrations').glob('*.sql'))
            if 'Livros' in versions and any(p.stem not in applied for p in scripts):
                backup = Path(self.db_name).parent / 'backups'
                backup.mkdir(exist_ok=True)
                target = sqlite3.connect(backup / ('antes-migracao-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.db'))
                try:
                    conn.backup(target)
                finally:
                    target.close()
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
            cursor.execute('CREATE TABLE IF NOT EXISTS Migracoes (versao TEXT PRIMARY KEY, aplicada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
            for script in scripts:
                if cursor.execute('SELECT 1 FROM Migracoes WHERE versao=?',(script.stem,)).fetchone():
                    continue
                # Não usar executescript: ele faria commit implícito antes do SQL.
                for statement in script.read_text(encoding='utf-8').split(';'):
                    if statement.strip():
                        cursor.execute(statement)
                cursor.execute('INSERT INTO Migracoes(versao) VALUES (?)', (script.stem,))
            # Não apagar órfãos legados. Bloquear migração e orientar correção explícita.
            violations = conn.execute('PRAGMA foreign_key_check').fetchall()
            if violations:
                raise RuntimeError('Integridade legada pendente: corrija referências órfãs antes de iniciar. Backup preservado.')
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute('PRAGMA foreign_keys=ON')
            conn.execute('PRAGMA busy_timeout=10000')
            return conn
        except Exception:
            conn.close()
            raise

    @contextmanager
    def connection(self):
        with operation_lock:
            conn = self.get_connection()
            try:
                yield conn
            finally:
                conn.close()

# Inicializado explicitamente por app.py, antes do registro das rotas.
class DatabaseProxy:
    """Services existentes usam o gerenciador da aplicação/contexto atual."""
    def __init__(self):
        self.fallback = DatabaseManager(initialize=False)

    def __getattr__(self, name):
        manager = current_app.extensions['database'] if has_app_context() else self.fallback
        return getattr(manager, name)

    @property
    def db_name(self):
        return self.__getattr__('db_name')

    @db_name.setter
    def db_name(self, value):
        self.fallback.db_name = value

db_manager = DatabaseProxy()

def initialize_database():
    db_manager.init_database()
    return db_manager
