from database.database import db_manager
from flask import jsonify
from flask import request
import hashlib


def is_admin():
    """Verifica se o cliente está acessando a partir do localhost (127.0.0.1 ou ::1)."""
    remote_addr = request.remote_addr
    return remote_addr in ('127.0.0.1', '::1', 'localhost')


def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not is_admin():
            return jsonify({"erro": "Acesso negado. Operação permitida apenas para administradores."}), 403
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


def verificar_senha_admin(senha):
    if not senha:
        return False
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave='senha_hash'")
        row = cursor.fetchone()
        if not row:
            return False
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        return senha_hash == row[0]
