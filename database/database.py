"""Conexao SQLite, schema e compatibilidade com bancos existentes."""
import sqlite3
from pathlib import Path
from config import DB_NAME

class DatabaseManager:
    def __init__(self, db_name=DB_NAME, initialize=True):
        self.db_name = db_name
        if initialize:
            self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.executescript(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))

        try:
            cursor.execute("ALTER TABLE Agendamento ADD COLUMN data TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE Livros ADD COLUMN data_cadastro TEXT NOT NULL DEFAULT (date('now'))")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE Usuarios ADD COLUMN telefone TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE Livros ADD COLUMN localizacao TEXT")
        except sqlite3.OperationalError:
            pass

        cursor.execute("INSERT OR IGNORE INTO Configuracoes (chave, valor) VALUES ('bloquear_email', 'false')")
        cursor.execute("INSERT OR IGNORE INTO Configuracoes (chave, valor) VALUES ('exigir_senha_emprestimo', 'false')")
        cursor.execute("INSERT OR IGNORE INTO Configuracoes (chave, valor) VALUES ('obrigar_localizacao_livro', 'false')")
        cursor.execute("INSERT OR IGNORE INTO Configuracoes (chave, valor) VALUES ('exigir_senha_agendamento', 'false')")
        cursor.execute("INSERT OR IGNORE INTO Configuracoes (chave, valor) VALUES ('bloquear_excluir_agendamento', 'true')")
        cursor.execute("INSERT OR IGNORE INTO Configuracoes (chave, valor) VALUES ('quantidade_aulas', '6')")
        cursor.execute("INSERT OR IGNORE INTO Configuracoes (chave, valor) VALUES ('email_organizacao', '')")
        cursor.execute("INSERT OR IGNORE INTO Configuracoes (chave, valor) VALUES ('email_app_password', '')")

        conn.commit()
        conn.close()

    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

# Inicializado explicitamente por app.py, antes do registro das rotas.
db_manager = DatabaseManager(initialize=False)

def initialize_database():
    db_manager.init_database()
    return db_manager
