"""Inicializacao e orquestracao da Biblioteca Inteligente."""
import os
import logging
import threading
import time
import webview
from flask import Flask
from config import STATIC_DIR, TEMPLATE_DIR, UPLOAD_FOLDER, initialize_directories
from database.database import initialize_database

initialize_directories()
db_manager = initialize_database()

# Os services sao importados somente depois da inicializacao do banco.
from routes import register_blueprints, register_error_handlers
from services.email_service import iniciar_verificacao_notificacoes

app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATE_DIR)
app.secret_key = os.getenv('SECRET_KEY', 'sua-chave-secreta-padrao')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
register_blueprints(app)
register_error_handlers(app)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

if __name__ == '__main__':

    iniciar_verificacao_notificacoes(app)

    # Lê as variáveis do ambiente com fallbacks
    ENV_PORT = int(os.getenv('PORT', 5000))
    ENV_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')

    def start_flask():
        app.run(
            host='0.0.0.0',
            port=ENV_PORT,
            debug=ENV_DEBUG,
            use_reloader=False
        )

    flask_thread = threading.Thread(
        target=start_flask,
        daemon=True
    )
    flask_thread.start()

    time.sleep(2)

    webview.create_window(
        title='Sistema de Biblioteca - BIBI',
        url=f'http://127.0.0.1:{ENV_PORT}',
        width=1200,
        height=700,
        resizable=True,
    )

    webview.start()
