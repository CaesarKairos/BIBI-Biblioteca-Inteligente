from config import EMAIL_PASSWORD
from config import EMAIL_USER
from database.database import db_manager
import hashlib


def is_email_blocked():
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave = 'bloquear_email'")
        row = cursor.fetchone()
        return row is not None and row[0].lower() == 'true'


def is_exigir_senha_emprestimo():
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave = 'exigir_senha_emprestimo'")
        row = cursor.fetchone()
        return row is not None and row[0].lower() == 'true'


def is_obrigar_localizacao_livro():
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave = 'obrigar_localizacao_livro'")
        row = cursor.fetchone()
        return row is not None and row[0].lower() == 'true'


def is_exigir_senha_agendamento():
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave = 'exigir_senha_agendamento'")
        row = cursor.fetchone()
        return row is not None and row[0].lower() == 'true'


def is_bloquear_excluir_agendamento():
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave = 'bloquear_excluir_agendamento'")
        row = cursor.fetchone()
        return row is not None and row[0].lower() == 'true'


def get_email_credenciais():
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave = 'email_organizacao'")
        email_row = cursor.fetchone()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave = 'email_app_password'")
        pass_row = cursor.fetchone()
        email = email_row[0] if email_row else ''
        password = pass_row[0] if pass_row else ''
        if email and password:
            return email, password
        return EMAIL_USER, EMAIL_PASSWORD


def get_quantidade_aulas():
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave = 'quantidade_aulas'")
        row = cursor.fetchone()
        if row and row[0].isdigit():
            return int(row[0])
        return 6


def set_quantidade_aulas(qtd):
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('quantidade_aulas', ?)", (str(qtd),))
        conn.commit()


def senha_status():
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave='senha_hash'")
        row = cursor.fetchone()
        return {"set": row is not None}


def definir_senha(data):
    senha = data.get('senha')
    if not senha or len(senha) != 4:
        return {"erro": "Senha deve ter 4 caracteres"}, 400
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave='senha_hash'")
        if cursor.fetchone():
            return {"erro": "Senha já existe"}, 400
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        cursor.execute("INSERT INTO Configuracoes (chave, valor) VALUES ('senha_hash', ?)", (senha_hash,))
        conn.commit()
        return {"status": "ok"}


def verificar_senha(data):
    senha = data.get('senha')
    if not senha:
        return {"valido": False}
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave='senha_hash'")
        row = cursor.fetchone()
        if not row:
            return {"valido": False}
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        return {"valido": senha_hash == row[0]}


def bloquear_email_status():
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave='bloquear_email'")
        row = cursor.fetchone()
        return {"bloqueado": row is not None and row[0].lower() == 'true'}


def set_bloquear_email(data):
    bloqueado = data.get('bloqueado', False)
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('bloquear_email', ?)", ('true' if bloqueado else 'false',))
        conn.commit()
        return {"status": "ok"}


def exigir_senha_emprestimo_status():
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave='exigir_senha_emprestimo'")
        row = cursor.fetchone()
        return {"ativo": row is not None and row[0].lower() == 'true'}


def set_exigir_senha_emprestimo(data):
    ativo = data.get('ativo', False)
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('exigir_senha_emprestimo', ?)", ('true' if ativo else 'false',))
        conn.commit()
        return {"status": "ok"}


def obrigar_localizacao_livro_status():
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave='obrigar_localizacao_livro'")
        row = cursor.fetchone()
        return {"ativo": row is not None and row[0].lower() == 'true'}


def set_obrigar_localizacao_livro(data):
    ativo = data.get('ativo', False)
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('obrigar_localizacao_livro', ?)", ('true' if ativo else 'false',))
        conn.commit()
        return {"status": "ok"}


def exigir_senha_agendamento_status():
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave='exigir_senha_agendamento'")
        row = cursor.fetchone()
        return {"ativo": row is not None and row[0].lower() == 'true'}


def set_exigir_senha_agendamento(data):
    ativo = data.get('ativo', False)
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('exigir_senha_agendamento', ?)", ('true' if ativo else 'false',))
        conn.commit()
        return {"status": "ok"}


def bloquear_excluir_agendamento_status():
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave='bloquear_excluir_agendamento'")
        row = cursor.fetchone()
        return {"ativo": row is not None and row[0].lower() == 'true'}


def set_bloquear_excluir_agendamento(data):
    ativo = data.get('ativo', False)
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('bloquear_excluir_agendamento', ?)", ('true' if ativo else 'false',))
        conn.commit()
        return {"status": "ok"}


def quantidade_aulas_status():
    # Rota pública para que qualquer usuário possa ler a configuração de quantidade de aulas
    quantidade = get_quantidade_aulas()
    return {"quantidade": quantidade}


def set_quantidade_aulas_route(data):
    qtd = data.get('quantidade')
    if qtd is None or not isinstance(qtd, int) or qtd < 1 or qtd > 20:
        return {"erro": "Quantidade deve ser um número entre 1 e 20"}, 400
    set_quantidade_aulas(qtd)
    return {"status": "ok"}


def config_email_status():
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave='email_organizacao'")
        row = cursor.fetchone()
        return {"email": row[0] if row and row[0] else ''}


def set_config_email(data):
    data = data or {}
    email = (data.get('email_organizacao') or '').strip()
    senha_app = (data.get('email_app_password') or '').strip()
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('email_organizacao', ?)", (email,))
        # A senha de app só é sobrescrita se um novo valor for enviado, para não apagar a existente
        # quando o campo é deixado em branco na interface (ela nunca é reexibida por segurança).
        if senha_app:
            cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('email_app_password', ?)", (senha_app,))
        conn.commit()
        return {"status": "ok"}
