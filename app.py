"""Fabrica Flask sem efeitos de importacao."""
from datetime import timedelta
from pathlib import Path
import json
from flask import Flask
from config import STATIC_DIR,TEMPLATE_DIR,DATA_DIR
from database.database import DatabaseManager
from utils.secrets_store import SecretStore
from flask.sessions import SecureCookieSessionInterface
from flask import request


class InstallationSessionInterface(SecureCookieSessionInterface):
    def get_cookie_secure(self,app):
        # HTTPS de rede recebe Secure; a janela local usa HTTP em loopback.
        return request.is_secure or app.config['SESSION_COOKIE_SECURE']


def create_app(test_config=None):
    app = Flask(__name__,static_folder=STATIC_DIR,template_folder=TEMPLATE_DIR)
    app.config.update(DATA_DIR=DATA_DIR,MAX_CONTENT_LENGTH=512*1024*1024,
        SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        ALLOWED_HOSTS=['127.0.0.1','::1','localhost'],SESSION_COOKIE_SECURE=False,
        LAN_ENABLED=True,LAN_PORT=5443,DESKTOP_TRAY=True)
    if test_config:
        app.config.update(test_config)
    app.session_interface=InstallationSessionInterface()
    directory = Path(app.config['DATA_DIR'])
    directory.mkdir(parents=True,exist_ok=True)
    for name in ('uploadedcovers','externalcovers','avatars','backups'):
        (directory/name).mkdir(exist_ok=True)
    app.config.setdefault('DATABASE',str(directory/'Biblioteca.db'))
    app.config.setdefault('UPLOAD_FOLDER',str(directory/'uploadedcovers'))
    app.config.setdefault('EXTERNAL_FOLDER',str(directory/'externalcovers'))
    app.extensions['database'] = DatabaseManager(app.config['DATABASE'])
    store = SecretStore(directory)
    app.extensions['secrets'] = store
    app.secret_key = store.session_key()
    store.recovery_key()
    from werkzeug.security import generate_password_hash
    import secrets
    app.extensions['dummy_password_hash']=generate_password_hash(secrets.token_urlsafe(24),method='scrypt')
    # Migra apenas a configuração já existente no banco, nunca lê .env.
    with app.extensions['database'].connection() as conn:
        # Configurações anteriores ao fluxo de verificação persistente precisam de teste
        # e ativação explícitos. Nenhuma chave salva é tratada como prova de conexão.
        legacy_ai=conn.execute("SELECT valor FROM Configuracoes WHERE chave='ia'").fetchone()
        proofs=conn.execute("SELECT 1 FROM Configuracoes WHERE chave='ia_validacoes'").fetchone()
        if legacy_ai and not proofs:
            settings=json.loads(legacy_ai[0])
            if settings.get('ativa'):
                settings['ativa']=False
                conn.execute("UPDATE Configuracoes SET valor=? WHERE chave='ia'",(json.dumps(settings),))
                conn.commit()
        legacy = conn.execute("SELECT valor FROM Configuracoes WHERE chave='email_app_password'").fetchone()
        if legacy and legacy[0]:
            if not store.get('smtp_password'):
                store.set('smtp_password',legacy[0])
            conn.execute("UPDATE Configuracoes SET valor='' WHERE chave='email_app_password'")
            conn.commit()
    from routes import register_blueprints,register_error_handlers
    from utils.auth import install_security
    install_security(app)
    register_blueprints(app)
    register_error_handlers(app)
    return app


def main():
    from desktop import run_desktop
    run_desktop(create_app())


if __name__ == '__main__':
    main()
