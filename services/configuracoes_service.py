from config import EMAIL_PASSWORD
from config import EMAIL_USER
from database.database import db_manager
import hashlib


def is_email_blocked():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave = 'bloquear_email'")
    row = cursor.fetchone()
    conn.close()
    return row is not None and row[0].lower() == 'true'


def is_exigir_senha_emprestimo():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave = 'exigir_senha_emprestimo'")
    row = cursor.fetchone()
    conn.close()
    return row is not None and row[0].lower() == 'true'


def is_obrigar_localizacao_livro():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave = 'obrigar_localizacao_livro'")
    row = cursor.fetchone()
    conn.close()
    return row is not None and row[0].lower() == 'true'


def is_exigir_senha_agendamento():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave = 'exigir_senha_agendamento'")
    row = cursor.fetchone()
    conn.close()
    return row is not None and row[0].lower() == 'true'


def is_bloquear_excluir_agendamento():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave = 'bloquear_excluir_agendamento'")
    row = cursor.fetchone()
    conn.close()
    return row is not None and row[0].lower() == 'true'


def get_email_credenciais():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave = 'email_organizacao'")
    email_row = cursor.fetchone()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave = 'email_app_password'")
    pass_row = cursor.fetchone()
    conn.close()
    email = email_row[0] if email_row else ''
    password = pass_row[0] if pass_row else ''
    if email and password:
        return email, password
    return EMAIL_USER, EMAIL_PASSWORD


def get_quantidade_aulas():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave = 'quantidade_aulas'")
    row = cursor.fetchone()
    conn.close()
    if row and row[0].isdigit():
        return int(row[0])
    return 6


def set_quantidade_aulas(qtd):
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('quantidade_aulas', ?)", (str(qtd),))
    conn.commit()
    conn.close()


def senha_status():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='senha_hash'")
    row = cursor.fetchone()
    conn.close()
    return {"set": row is not None}


def definir_senha(data):
    senha = data.get('senha')
    if not senha or len(senha) != 4:
        return {"erro": "Senha deve ter 4 caracteres"}, 400
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='senha_hash'")
    if cursor.fetchone():
        conn.close()
        return {"erro": "Senha já existe"}, 400
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    cursor.execute("INSERT INTO Configuracoes (chave, valor) VALUES ('senha_hash', ?)", (senha_hash,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


def verificar_senha(data):
    senha = data.get('senha')
    if not senha:
        return {"valido": False}
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='senha_hash'")
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {"valido": False}
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    return {"valido": senha_hash == row[0]}


def bloquear_email_status():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='bloquear_email'")
    row = cursor.fetchone()
    conn.close()
    return {"bloqueado": row is not None and row[0].lower() == 'true'}


def set_bloquear_email(data):
    bloqueado = data.get('bloqueado', False)
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('bloquear_email', ?)", ('true' if bloqueado else 'false',))
    conn.commit()
    conn.close()
    return {"status": "ok"}


def exigir_senha_emprestimo_status():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='exigir_senha_emprestimo'")
    row = cursor.fetchone()
    conn.close()
    return {"ativo": row is not None and row[0].lower() == 'true'}


def set_exigir_senha_emprestimo(data):
    ativo = data.get('ativo', False)
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('exigir_senha_emprestimo', ?)", ('true' if ativo else 'false',))
    conn.commit()
    conn.close()
    return {"status": "ok"}


def obrigar_localizacao_livro_status():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='obrigar_localizacao_livro'")
    row = cursor.fetchone()
    conn.close()
    return {"ativo": row is not None and row[0].lower() == 'true'}


def set_obrigar_localizacao_livro(data):
    ativo = data.get('ativo', False)
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('obrigar_localizacao_livro', ?)", ('true' if ativo else 'false',))
    conn.commit()
    conn.close()
    return {"status": "ok"}


def exigir_senha_agendamento_status():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='exigir_senha_agendamento'")
    row = cursor.fetchone()
    conn.close()
    return {"ativo": row is not None and row[0].lower() == 'true'}


def set_exigir_senha_agendamento(data):
    ativo = data.get('ativo', False)
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('exigir_senha_agendamento', ?)", ('true' if ativo else 'false',))
    conn.commit()
    conn.close()
    return {"status": "ok"}


def bloquear_excluir_agendamento_status():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='bloquear_excluir_agendamento'")
    row = cursor.fetchone()
    conn.close()
    return {"ativo": row is not None and row[0].lower() == 'true'}


def set_bloquear_excluir_agendamento(data):
    ativo = data.get('ativo', False)
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('bloquear_excluir_agendamento', ?)", ('true' if ativo else 'false',))
    conn.commit()
    conn.close()
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
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='email_organizacao'")
    row = cursor.fetchone()
    conn.close()
    return {"email": row[0] if row and row[0] else ''}


def set_config_email(data):
    data = data or {}
    email = (data.get('email_organizacao') or '').strip()
    senha_app = (data.get('email_app_password') or '').strip()
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('email_organizacao', ?)", (email,))
    # A senha de app só é sobrescrita se um novo valor for enviado, para não apagar a existente
    # quando o campo é deixado em branco na interface (ela nunca é reexibida por segurança).
    if senha_app:
        cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('email_app_password', ?)", (senha_app,))
    conn.commit()
    conn.close()
    return {"status": "ok"}
