"""Capacidade efêmera emitida somente pelo menu nativo, nunca por HTTP."""
import secrets
import time
import threading
from flask import current_app, session
from werkzeug.exceptions import Forbidden, BadRequest
from database.database import db_manager
from services.contas_service import limitar, senha_validada, email_normalizado, auditar
from utils.auth import local_only


class RecuperacaoDesktop:
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        self.pending = None

    def abrir(self):
        with self.lock:
            key = self.store.recovery_key()
            token = secrets.token_urlsafe(32)
            self.pending = {'token': token, 'expires': time.monotonic()+180,
                            'installation': key, 'session': None}
            return token

    def validar(self, token, bind=False):
        local_only()
        pending = self.pending
        if (not pending or time.monotonic() >= pending['expires']
                or not isinstance(token, str)
                or not secrets.compare_digest(pending['token'], token)
                or pending['installation'] != self.store.get('recovery_installation')):
            raise Forbidden('Abra uma nova recuperação pelo menu da janela desktop do BIBI.')
        if bind and pending['session'] is None:
            session['recovery_session'] = secrets.token_urlsafe(32)
            pending['session'] = session['recovery_session']
        if not pending['session'] or pending['session'] != session.get('recovery_session'):
            raise Forbidden('Sessão de recuperação inválida.')


def recuperar(data):
    local_only()
    limitar('desktop-recovery', limite=5, janela=900)
    manager = current_app.extensions.get('desktop_recovery')
    if manager is None:
        raise Forbidden('Recuperação disponível apenas na janela desktop do servidor.')
    with manager.lock:
        manager.validar(data.get('token'))
        email = email_normalizado(data.get('email'))
        password = senha_validada(data)
        with db_manager.connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute("SELECT id FROM Contas WHERE email=? AND papel='bibliotecario' AND ativa=1", (email,)).fetchone()
            if not row:
                raise BadRequest('Conta bibliotecária ativa não encontrada.')
            conn.execute('UPDATE Contas SET senha_hash=?,recuperacao_hash=NULL,versao_sessao=versao_sessao+1 WHERE id=?', (password,row[0]))
            conn.execute('DELETE FROM Sessoes WHERE conta_id=?', (row[0],))
            conn.execute("UPDATE Codigos SET consumido=1 WHERE conta_id=? OR email=?", (row[0],email))
            auditar(conn,'recuperacao_desktop',row[0],ator=row[0])
            conn.commit()
        manager.pending = None
        session.clear()
    return {'mensagem':'Senha redefinida. Entre novamente na sua conta.'}
