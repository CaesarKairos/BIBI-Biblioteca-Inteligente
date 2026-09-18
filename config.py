"""Caminhos e variaveis de ambiente originais do BIBI."""
import os
import sys
from dotenv import load_dotenv

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
    STATIC_DIR = os.path.join(APP_DIR, "_internal", "static")
    BASE_DIR = APP_DIR
    TEMPLATE_DIR = os.path.join(APP_DIR, "_internal", "templates")
    env_path = os.path.join(APP_DIR, "_internal", ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    STATIC_DIR = os.path.join(APP_DIR, "static")
    BASE_DIR = APP_DIR
    TEMPLATE_DIR = os.path.join(APP_DIR, "templates")
    load_dotenv()

EMAIL_USER = os.getenv('EMAIL_USER', '')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
DATA_DIR = os.path.join(os.getenv("LOCALAPPDATA"), "BIBI")
DB_NAME = os.path.join(DATA_DIR, "Biblioteca.db")
USER_DATA_DIR = DATA_DIR
UPLOAD_FOLDER = os.path.join(USER_DATA_DIR, "uploadedcovers")
EXTERNAL_FOLDER = os.path.join(USER_DATA_DIR, "externalcovers")
HERO_FOLDER = os.path.join(STATIC_DIR, 'images', 'hero')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def initialize_directories():
    for directory in (DATA_DIR, UPLOAD_FOLDER, EXTERNAL_FOLDER):
        os.makedirs(directory, exist_ok=True)
