import requests
import sqlite3
from datetime import datetime, timedelta, date, timezone
import os
import re
import uuid
import threading
import smtplib
import hashlib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from werkzeug.utils import secure_filename
import random
import time
from io import BytesIO
import atexit
import webview
from flask import Flask, render_template_string, jsonify, request, send_from_directory
from dotenv import load_dotenv
import sys

# ==========================================
# DIRETÓRIOS DO SISTEMA
# ==========================================

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
    STATIC_DIR = os.path.join(APP_DIR, "_internal", "static")
    BASE_DIR = APP_DIR

    env_path = os.path.join(APP_DIR, "_internal", ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)

else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    STATIC_DIR = os.path.join(APP_DIR, "static")
    BASE_DIR = APP_DIR

    load_dotenv()

# ==========================================
# FLASK
# ==========================================

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'sua-chave-secreta-padrao')

# ==========================================
# CONFIGURAÇÕES DE E-MAIL
# ==========================================

EMAIL_USER = os.getenv('EMAIL_USER', '')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')

# ==========================================
# DADOS DO USUÁRIO
# ==========================================

DATA_DIR = os.path.join(os.getenv("LOCALAPPDATA"), "BIBI")
os.makedirs(DATA_DIR, exist_ok=True)

DB_NAME = os.path.join(DATA_DIR, "Biblioteca.db")

USER_DATA_DIR = DATA_DIR

# ==========================================
# PASTAS DE IMAGENS DO USUÁRIO
# ==========================================

UPLOAD_FOLDER = os.path.join(USER_DATA_DIR, "uploadedcovers")
EXTERNAL_FOLDER = os.path.join(USER_DATA_DIR, "externalcovers")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXTERNAL_FOLDER, exist_ok=True)

# ==========================================
# ARQUIVOS ESTÁTICOS DO SISTEMA
# ==========================================

HERO_FOLDER = os.path.join(STATIC_DIR, 'images', 'hero')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ==========================================
# TIPOS DE ARQUIVO ACEITOS
# ==========================================

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

# ==========================================
# FUSO HORÁRIO DE BRASÍLIA
# ==========================================

def get_brasilia_now():
    """Retorna datetime atual no fuso horário de Brasília (UTC-3)"""
    return datetime.now(timezone(timedelta(hours=-3)))

def get_brasilia_today():
    """Retorna a data atual (sem hora) em Brasília"""
    return get_brasilia_now().date()
# ============================
# CONTROLE DE ACESSO ADMINISTRADOR (APENAS LOCALHOST)
# ============================
def is_admin():
    """Verifica se o cliente está acessando a partir do localhost (127.0.0.1 ou ::1)."""
    remote_addr = request.remote_addr
    return remote_addr in ('127.0.0.1', '::1', 'localhost')

# Decorator para rotas exclusivas de admin
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not is_admin():
            return jsonify({"erro": "Acesso negado. Operação permitida apenas para administradores."}), 403
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

class DatabaseManager:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS Livros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                isbn TEXT UNIQUE,
                nome TEXT NOT NULL,
                autor TEXT NOT NULL,
                ano_publicacao INTEGER,
                capa_url TEXT,
                descricao TEXT,
                temas TEXT,
                categoria TEXT DEFAULT 'Ficção',
                estoque INTEGER NOT NULL,
                quantidade_disponivel INTEGER NOT NULL,
                data_cadastro TEXT NOT NULL DEFAULT (date('now')),
                localizacao TEXT
            );

            CREATE TABLE IF NOT EXISTS Usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                tipo TEXT CHECK(tipo IN ('estudante', 'professor', 'bibliotecario')) NOT NULL,
                email TEXT UNIQUE,
                sala TEXT,
                periodo TEXT,
                materia TEXT,
                telefone TEXT
            );

            CREATE TABLE IF NOT EXISTS Emprestimo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuarios_id INTEGER NOT NULL,
                livros_id INTEGER NOT NULL,
                data_emprestimo TEXT NOT NULL,
                data_vencimento TEXT NOT NULL,
                data_devolucao TEXT,
                quantidade INTEGER NOT NULL DEFAULT 1,
                status TEXT CHECK(status IN ('Pendente', 'Aprovado', 'Devolvido', 'Atrasado')) DEFAULT 'Aprovado',
                notificacao_3dias INTEGER DEFAULT 0,
                notificacao_hoje INTEGER DEFAULT 0,
                FOREIGN KEY (usuarios_id) REFERENCES Usuarios(id),
                FOREIGN KEY (livros_id) REFERENCES Livros(id)
            );

            CREATE TABLE IF NOT EXISTS Agendamento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                periodo TEXT CHECK(periodo IN('Manhã', 'Tarde', 'Noite')) NOT NULL,
                dia_semana INTEGER NOT NULL,
                aula INTEGER NOT NULL,
                professor TEXT NOT NULL,
                materia TEXT NOT NULL,
                uso TEXT NOT NULL,
                turma TEXT
            );

            CREATE TABLE IF NOT EXISTS Configuracoes (
                chave TEXT PRIMARY KEY,
                valor TEXT
            );
        ''')

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

db_manager = DatabaseManager()

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

def verificar_senha_admin(senha):
    if not senha:
        return False
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='senha_hash'")
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    return senha_hash == row[0]

def download_image_from_url(url, timeout=10):
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            ext = 'jpg'
            if 'png' in content_type:
                ext = 'png'
            elif 'gif' in content_type:
                ext = 'gif'
            elif 'webp' in content_type:
                ext = 'webp'
            else:
                url_ext = url.split('.')[-1].split('?')[0].lower()
                if url_ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    ext = url_ext
            return response.content, ext
    except Exception as e:
        print(f"Erro ao baixar imagem para e-mail: {e}")
    return None, None

def get_book_cover_image_bytes(cover_url):
    if not cover_url:
        return None, None

    if cover_url.startswith('/uploadedcovers/'):
        filename = cover_url.split('/')[-1]
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                return f.read(), file_path.split('.')[-1].lower()

    elif cover_url.startswith('/static/'):
        file_path = os.path.join(BASE_DIR, cover_url[1:])

        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                return f.read(), file_path.split('.')[-1].lower()

    elif cover_url.startswith('http://') or cover_url.startswith('https://'):
        return download_image_from_url(cover_url)

    return None, None

def anexar_capa_livro(msg, cover_url, cid_name='capa_livro'):
    img_data, ext = get_book_cover_image_bytes(cover_url)
    if img_data:
        img = MIMEImage(img_data, _subtype=ext if ext else 'jpeg')
        img.add_header('Content-ID', f'<{cid_name}>')
        img.add_header('Content-Disposition', 'inline', filename=f'capa.{ext}')
        msg.attach(img)
        return f'cid:{cid_name}'
    return None

def enviar_email_confirmacao(destinatario, nome_usuario, titulo_livro, data_devolucao, capa_url=None):
    if is_email_blocked():
        print("E-mail bloqueado pelas configurações.")
        return False
    try:
        EMAIL_USER, EMAIL_PASSWORD = get_email_credenciais()
        if not EMAIL_USER or not EMAIL_PASSWORD:
            print("Credenciais de e-mail não configuradas.")
            return False
        msg = MIMEMultipart("related")
        msg["Subject"] = "Empréstimo Confirmado - Biblioteca BIBI"
        msg["From"] = EMAIL_USER
        msg["To"] = destinatario

        msg_alternative = MIMEMultipart("alternative")
        msg.attach(msg_alternative)

        cid_capa = anexar_capa_livro(msg, capa_url, 'capa_livro')
        capa_html = ''
        if cid_capa:
            capa_html = f'<div style="text-align:center; margin-bottom:20px;"><img src="{cid_capa}" alt="Capa do livro" style="max-width:150px; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.1);"></div>'

        html = f"""
        <!DOCTYPE html>
        <html lang="pt-br">
        <head><meta charset="UTF-8"><title>Empréstimo Confirmado</title></head>
        <body style="margin:0; padding:0; background-color:#ffffff; font-family: 'Nunito', 'Segoe UI', Arial, sans-serif; color:#3e332a;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#ffffff; padding:20px 0;">
        <tr><td align="center">
        <table width="100%" style="max-width:600px; background-color:#fdfcfa; border-radius:20px; overflow:hidden;">
        <tr>
          <td style="background-color:#3e332a; padding:30px; text-align:center; color:#ffffff;">
            <img src="cid:logo_bibi" width="55" style="display:block; margin:0 auto 10px auto; border-radius:8px;" alt="Logo">
            <div style="font-size:28px; font-weight:800; letter-spacing:2px; margin-bottom:2px;">BIBI</div>
            <div style="font-size:13px; opacity:0.8; text-transform:uppercase; letter-spacing:1px;">Biblioteca Inteligente</div>
          </td>
        </tr>
        <tr>
          <td style="padding:40px 30px; line-height:1.6; background-color:#f5eee6;">
            <h2 style="color:#3e332a; margin-top:0;">Olá, {nome_usuario}!</h2>
            <p>Seu empréstimo foi confirmado com sucesso.</p>
            {capa_html}
            <div style="background-color:#ffffff; border-left:5px solid #d4b59e; padding:20px; margin:20px 0; border-radius:4px;">
            <strong>Livro:</strong> {titulo_livro}<br>
            <strong>Data de devolução:</strong> {data_devolucao}
            </div>
            <p>Agradecemos por utilizar a Biblioteca BIBI.</p>
            <p style="margin-top:30px;">Atenciosamente,<br><strong>Equipe Biblioteca Inteligente</strong></p>
          </td>
        </tr>
        <tr>
          <td style="background-color:#fdfcfa; padding:25px 20px; text-align:center; font-size:12px; color:#8c8279;">
            <div>© 2026 Biblioteca Inteligente | Gerencie seu acervo com sabedoria.</div>
          </td>
        </tr>
        </table>
        </td></tr>
        </table>
        </body>
        </html>
        """
        msg_alternative.attach(MIMEText(html, "html"))

        logo_path = os.path.join(BASE_DIR, "static", "images", "icon.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                img = MIMEImage(img_file.read())
                img.add_header("Content-ID", "<logo_bibi>")
                msg.attach(img)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"E-mail de confirmação enviado para {destinatario}")
        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail de confirmação: {e}")
        return False


def enviar_email_renovacao(destinatario, nome_usuario, titulo_livro, nova_data_devolucao, capa_url=None):
    if is_email_blocked():
        print("E-mail bloqueado pelas configurações.")
        return False
    try:
        EMAIL_USER, EMAIL_PASSWORD = get_email_credenciais()
        if not EMAIL_USER or not EMAIL_PASSWORD:
            print("Credenciais de e-mail não configuradas.")
            return False
        msg = MIMEMultipart("related")
        msg["Subject"] = "Renovação Confirmada - Biblioteca BIBI"
        msg["From"] = EMAIL_USER
        msg["To"] = destinatario

        msg_alternative = MIMEMultipart("alternative")
        msg.attach(msg_alternative)

        cid_capa = anexar_capa_livro(msg, capa_url, 'capa_livro')
        capa_html = ''
        if cid_capa:
            capa_html = f'<div style="text-align:center; margin-bottom:20px;"><img src="{cid_capa}" alt="Capa do livro" style="max-width:150px; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.1);"></div>'

        html = f"""
        <!DOCTYPE html>
        <html lang="pt-br">
        <head><meta charset="UTF-8"><title>Renovação Confirmada</title></head>
        <body style="margin:0; padding:0; background-color:#ffffff; font-family: 'Nunito', 'Segoe UI', Arial, sans-serif; color:#3e332a;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#ffffff; padding:20px 0;">
        <tr><td align="center">
        <table width="100%" style="max-width:600px; background-color:#fdfcfa; border-radius:20px; overflow:hidden;">
        <tr>
          <td style="background-color:#3e332a; padding:30px; text-align:center; color:#ffffff;">
            <img src="cid:logo_bibi" width="55" style="display:block; margin:0 auto 10px auto; border-radius:8px;" alt="Logo">
            <div style="font-size:28px; font-weight:800; letter-spacing:2px; margin-bottom:2px;">BIBI</div>
            <div style="font-size:13px; opacity:0.8; text-transform:uppercase; letter-spacing:1px;">Biblioteca Inteligente</div>
          </td>
        </tr>
        <tr>
          <td style="padding:40px 30px; line-height:1.6; background-color:#f5eee6;">
            <h2 style="color:#3e332a; margin-top:0;">Olá, {nome_usuario}!</h2>
            <p>Seu empréstimo foi <strong>renovado com sucesso</strong>.</p>
            {capa_html}
            <div style="background-color:#ffffff; border-left:5px solid #d4b59e; padding:20px; margin:20px 0; border-radius:4px;">
            <strong>Livro:</strong> {titulo_livro}<br>
            <strong>Nova data de devolução:</strong> {nova_data_devolucao}
            </div>
            <p>Fique atento ao novo prazo para evitar atrasos.</p>
            <p style="margin-top:30px;">Atenciosamente,<br><strong>Equipe Biblioteca Inteligente</strong></p>
          </td>
        </tr>
        <tr>
          <td style="background-color:#fdfcfa; padding:25px 20px; text-align:center; font-size:12px; color:#8c8279;">
            <div>© 2026 Biblioteca Inteligente | Gerencie seu acervo com sabedoria.</div>
          </td>
        </tr>
        </table>
        </td></tr>
        </table>
        </body>
        </html>
        """
        msg_alternative.attach(MIMEText(html, "html"))

        logo_path = os.path.join(BASE_DIR, "static", "images", "icon.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                img = MIMEImage(img_file.read())
                img.add_header("Content-ID", "<logo_bibi>")
                msg.attach(img)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"E-mail de renovação enviado para {destinatario}")
        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail de renovação: {e}")
        return False


def enviar_email_devolucao(destinatario, nome_usuario, titulo_livro, data_devolucao_real, capa_url=None):
    if is_email_blocked():
        print("E-mail bloqueado pelas configurações.")
        return False
    try:
        EMAIL_USER, EMAIL_PASSWORD = get_email_credenciais()
        if not EMAIL_USER or not EMAIL_PASSWORD:
            print("Credenciais de e-mail não configuradas.")
            return False
        msg = MIMEMultipart("related")
        msg["Subject"] = "Devolução Confirmada - Biblioteca BIBI"
        msg["From"] = EMAIL_USER
        msg["To"] = destinatario

        msg_alternative = MIMEMultipart("alternative")
        msg.attach(msg_alternative)

        cid_capa = anexar_capa_livro(msg, capa_url, 'capa_livro')
        capa_html = ''
        if cid_capa:
            capa_html = f'<div style="text-align:center; margin-bottom:20px;"><img src="{cid_capa}" alt="Capa do livro" style="max-width:150px; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.1);"></div>'

        html = f"""
        <!DOCTYPE html>
        <html lang="pt-br">
        <head><meta charset="UTF-8"><title>Devolução Confirmada</title></head>
        <body style="margin:0; padding:0; background-color:#ffffff; font-family: 'Nunito', 'Segoe UI', Arial, sans-serif; color:#3e332a;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#ffffff; padding:20px 0;">
        <tr><td align="center">
        <table width="100%" style="max-width:600px; background-color:#fdfcfa; border-radius:20px; overflow:hidden;">
        <tr>
          <td style="background-color:#3e332a; padding:30px; text-align:center; color:#ffffff;">
            <img src="cid:logo_bibi" width="55" style="display:block; margin:0 auto 10px auto; border-radius:8px;" alt="Logo">
            <div style="font-size:28px; font-weight:800; letter-spacing:2px; margin-bottom:2px;">BIBI</div>
            <div style="font-size:13px; opacity:0.8; text-transform:uppercase; letter-spacing:1px;">Biblioteca Inteligente</div>
          </td>
        </tr>
        <tr>
          <td style="padding:40px 30px; line-height:1.6; background-color:#f5eee6;">
            <h2 style="color:#3e332a; margin-top:0;">Olá, {nome_usuario}!</h2>
            <p>Registramos a <strong>devolução do seu empréstimo com sucesso</strong>.</p>
            {capa_html}
            <div style="background-color:#ffffff; border-left:5px solid #d4b59e; padding:20px; margin:20px 0; border-radius:4px;">
            <strong>Livro:</strong> {titulo_livro}<br>
            <strong>Data da devolução:</strong> {data_devolucao_real}
            </div>
            <p>Obrigado por manter o acervo organizado e acessível para todos</p>
            <p style="margin-top:30px;">Atenciosamente,<br><strong>Equipe Biblioteca Inteligente</strong></p>
          </td>
        </tr>
        <tr>
          <td style="background-color:#fdfcfa; padding:25px 20px; text-align:center; font-size:12px; color:#8c8279;">
            <div>© 2026 Biblioteca Inteligente | Gerencie seu acervo com sabedoria.</div>
          </td>
        </tr>
        </table>
        </td></tr>
        </table>
        </body>
        </html>
        """
        msg_alternative.attach(MIMEText(html, "html"))

        logo_path = os.path.join(BASE_DIR, "static", "images", "icon.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                img = MIMEImage(img_file.read())
                img.add_header("Content-ID", "<logo_bibi>")
                msg.attach(img)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"E-mail de devolução enviado para {destinatario}")
        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail de devolução: {e}")
        return False


def enviar_email_notificacao(destinatario, nome_usuario, titulo_livro, data_devolucao, dias_faltantes, capa_url=None):
    if is_email_blocked():
        print("E-mail bloqueado pelas configurações.")
        return False
    try:
        EMAIL_USER, EMAIL_PASSWORD = get_email_credenciais()
        if not EMAIL_USER or not EMAIL_PASSWORD:
            print("Credenciais de e-mail não configuradas.")
            return False
        msg = MIMEMultipart("related")
        msg["Subject"] = "Lembrete de Devolução - Biblioteca BIBI"
        msg["From"] = EMAIL_USER
        msg["To"] = destinatario

        msg_alternative = MIMEMultipart("alternative")
        msg.attach(msg_alternative)

        status_texto = f"Faltam {dias_faltantes} dias" if dias_faltantes > 0 else "Vence hoje"
        if dias_faltantes == 0:
            status_texto = "Vence <strong>hoje</strong>"

        cid_capa = anexar_capa_livro(msg, capa_url, 'capa_livro')
        capa_html = ''
        if cid_capa:
            capa_html = f'<div style="text-align:center; margin-bottom:20px;"><img src="{cid_capa}" alt="Capa do livro" style="max-width:150px; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.1);"></div>'

        html = f"""
        <!DOCTYPE html>
        <html lang="pt-br">
        <head><meta charset="UTF-8"><title>Lembrete de Devolução</title></head>
        <body style="margin:0; padding:0; background-color:#ffffff; font-family: 'Nunito', 'Segoe UI', Arial, sans-serif; color:#3e332a;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#ffffff; padding:20px 0;">
        <tr><td align="center">
        <table width="100%" style="max-width:600px; background-color:#fdfcfa; border-radius:20px; overflow:hidden;">
        <tr>
          <td style="background-color:#3e332a; padding:30px; text-align:center; color:#ffffff;">
            <img src="cid:logo_bibi" width="55" style="display:block; margin:0 auto 10px auto; border-radius:8px;" alt="Logo">
            <div style="font-size:28px; font-weight:800; letter-spacing:2px; margin-bottom:2px;">BIBI</div>
            <div style="font-size:13px; opacity:0.8; text-transform:uppercase; letter-spacing:1px;">Biblioteca Inteligente</div>
          </td>
        </tr>
        <tr>
          <td style="padding:40px 30px; line-height:1.6; background-color:#f5eee6;">
            <h2 style="color:#3e332a; margin-top:0;">Olá, {nome_usuario}!</h2>
            <p>Este é um lembrete automático sobre o prazo de devolução do seu empréstimo.</p>
            {capa_html}
            <div style="background-color:#ffffff; border-left:5px solid #d4b59e; padding:20px; margin:20px 0; border-radius:4px;">
            <strong>Livro:</strong> {titulo_livro}<br>
            <strong>Status:</strong> <span style="color:#cc4444; font-weight:bold;">{status_texto}</span> para o vencimento.
            </div>
            <p>A data limite para entrega é <strong>{data_devolucao}</strong>.</p>
            <p style="background-color:#ffffff; padding:15px; border-radius:10px; border:1px solid #e5d8cc; font-size:14px;">
            <strong style="color:#8c8279;">Informação sobre Renovação:</strong><br>
            Caso ainda não tenha terminado a leitura, por favor, <strong>compareça à nossa unidade física</strong> para solicitar a renovação do empréstimo.
            </p>
            <p style="margin-top:30px;">Atenciosamente,<br><strong>Equipe Biblioteca Inteligente</strong></p>
          </td>
        </tr>
        <tr>
          <td style="background-color:#fdfcfa; padding:25px 20px; text-align:center; font-size:12px; color:#8c8279;">
            <div>© 2026 Biblioteca Inteligente | Gerencie seu acervo com sabedoria.</div>
            <div style="display:inline-block; margin-top:10px; padding:8px 15px; background-color:#f5eee6; border-radius:20px; font-size:11px; color:#a3968c;">
            Notificação automática. Não responda este e-mail.
            </div>
          </td>
        </tr>
        </table>
        </td></tr>
        </table>
        </body>
        </html>
        """
        msg_alternative.attach(MIMEText(html, "html"))

        logo_path = os.path.join(BASE_DIR, "static", "images", "icon.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                img = MIMEImage(img_file.read())
                img.add_header("Content-ID", "<logo_bibi>")
                msg.attach(img)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"E-mail enviado para {destinatario} ({dias_faltantes} dias)")
        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
        return False

def verificar_e_enviar_notificacoes():
    if is_email_blocked():
        return
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    hoje = get_brasilia_today()

    cursor.execute('''
        UPDATE Emprestimo 
        SET status = 'Atrasado' 
        WHERE status = 'Aprovado' AND date(data_vencimento) < ?
    ''', (hoje.isoformat(),))
    conn.commit()

    cursor.execute('''
        SELECT e.id, e.data_vencimento, e.notificacao_3dias, e.notificacao_hoje,
               u.nome, u.email, l.nome as livro_titulo, l.capa_url
        FROM Emprestimo e
        JOIN Usuarios u ON e.usuarios_id = u.id
        JOIN Livros l ON e.livros_id = l.id
        WHERE e.status IN ('Aprovado', 'Atrasado') AND e.data_devolucao IS NULL
    ''')
    emprestimos = cursor.fetchall()

    for emp in emprestimos:
        emp_id, data_venc_str, notif_3, notif_hoje, nome_user, email_user, livro_titulo, capa_url = emp
        data_venc = datetime.strptime(data_venc_str, "%Y-%m-%d").date()
        dias_restantes = (data_venc - hoje).days

        if dias_restantes == 3 and not notif_3:
            threading.Thread(target=enviar_email_notificacao, args=(email_user, nome_user, livro_titulo, data_venc.strftime("%d/%m/%Y"), 3, capa_url)).start()
            cursor.execute('UPDATE Emprestimo SET notificacao_3dias = 1 WHERE id = ?', (emp_id,))
            conn.commit()
        elif dias_restantes == 0 and not notif_hoje:
            threading.Thread(target=enviar_email_notificacao, args=(email_user, nome_user, livro_titulo, data_venc.strftime("%d/%m/%Y"), 0, capa_url)).start()
            cursor.execute('UPDATE Emprestimo SET notificacao_hoje = 1 WHERE id = ?', (emp_id,))
            conn.commit()

    conn.close()

def iniciar_verificacao_notificacoes():
    def _executar_periodicamente():
        while True:
            with app.app_context():
                verificar_e_enviar_notificacoes()
            time.sleep(1800)

    thread = threading.Thread(target=_executar_periodicamente, daemon=True)
    thread.start()

@app.route('/')
def landing():
    return render_template_string(LANDING_PAGE)

@app.route('/app')
def app_principal():
    admin = is_admin()
    # Busca a quantidade de aulas diretamente do banco para injetar no HTML
    qtd_aulas = get_quantidade_aulas()
    return render_template_string(get_app_html(admin, qtd_aulas))

@app.route('/static/images/<path:filename>')
def serve_images(filename):
    return send_from_directory(
        os.path.join(STATIC_DIR, 'images'),
        filename
    )

@app.route('/api/admin/status', methods=['GET'])
def admin_status():
    """Endpoint para o frontend saber se o usuário é administrador (localhost)."""
    return jsonify({"admin": is_admin()})

@app.route('/api/hero-image', methods=['GET'])
def hero_image():
    hero_dir = HERO_FOLDER
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
    images = []
    if os.path.exists(hero_dir):
        for f in os.listdir(hero_dir):
            if f.lower().endswith(image_extensions):
                images.append(f)
    if not images:
        fallback = 'hero.jpg'
        if not os.path.exists(os.path.join(hero_dir, fallback)):
            try:
                from PIL import Image, ImageDraw
                img = Image.new('RGB', (1200, 600), color=(100, 80, 70))
                draw = ImageDraw.Draw(img)
                draw.text((500, 280), "BIBI", fill=(255,255,255))
                img.save(os.path.join(hero_dir, fallback))
            except:
                pass
        images = [fallback] if os.path.exists(os.path.join(hero_dir, fallback)) else []
    if images:
        chosen = random.choice(images)
        return jsonify({"url": f"/static/images/hero/{chosen}"})
    return jsonify({"url": "/static/images/hero/hero.jpg"}), 200

# ROTAS DE CONFIGURAÇÃO - protegidas por admin (exceto leitura da quantidade de aulas)
@app.route('/api/config/senha/status', methods=['GET'])
@admin_required
def senha_status():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='senha_hash'")
    row = cursor.fetchone()
    conn.close()
    return jsonify({"set": row is not None})

@app.route('/api/config/senha/definir', methods=['POST'])
@admin_required
def definir_senha():
    data = request.json
    senha = data.get('senha')
    if not senha or len(senha) != 4:
        return jsonify({"erro": "Senha deve ter 4 caracteres"}), 400
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='senha_hash'")
    if cursor.fetchone():
        conn.close()
        return jsonify({"erro": "Senha já existe"}), 400
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    cursor.execute("INSERT INTO Configuracoes (chave, valor) VALUES ('senha_hash', ?)", (senha_hash,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/config/senha/verificar', methods=['POST'])
def verificar_senha():
    data = request.json
    senha = data.get('senha')
    if not senha:
        return jsonify({"valido": False})
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='senha_hash'")
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({"valido": False})
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    return jsonify({"valido": senha_hash == row[0]})

@app.route('/api/config/bloquear_email/status', methods=['GET'])
@admin_required
def bloquear_email_status():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='bloquear_email'")
    row = cursor.fetchone()
    conn.close()
    return jsonify({"bloqueado": row is not None and row[0].lower() == 'true'})

@app.route('/api/config/bloquear_email/set', methods=['POST'])
@admin_required
def set_bloquear_email():
    data = request.json
    bloqueado = data.get('bloqueado', False)
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('bloquear_email', ?)", ('true' if bloqueado else 'false',))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/config/exigir_senha_emprestimo/status', methods=['GET'])
@admin_required
def exigir_senha_emprestimo_status():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='exigir_senha_emprestimo'")
    row = cursor.fetchone()
    conn.close()
    return jsonify({"ativo": row is not None and row[0].lower() == 'true'})

@app.route('/api/config/exigir_senha_emprestimo/set', methods=['POST'])
@admin_required
def set_exigir_senha_emprestimo():
    data = request.json
    ativo = data.get('ativo', False)
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('exigir_senha_emprestimo', ?)", ('true' if ativo else 'false',))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/config/obrigar_localizacao_livro/status', methods=['GET'])
@admin_required
def obrigar_localizacao_livro_status():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='obrigar_localizacao_livro'")
    row = cursor.fetchone()
    conn.close()
    return jsonify({"ativo": row is not None and row[0].lower() == 'true'})

@app.route('/api/config/obrigar_localizacao_livro/set', methods=['POST'])
@admin_required
def set_obrigar_localizacao_livro():
    data = request.json
    ativo = data.get('ativo', False)
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('obrigar_localizacao_livro', ?)", ('true' if ativo else 'false',))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/config/exigir_senha_agendamento/status', methods=['GET'])
@admin_required
def exigir_senha_agendamento_status():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='exigir_senha_agendamento'")
    row = cursor.fetchone()
    conn.close()
    return jsonify({"ativo": row is not None and row[0].lower() == 'true'})

@app.route('/api/config/exigir_senha_agendamento/set', methods=['POST'])
@admin_required
def set_exigir_senha_agendamento():
    data = request.json
    ativo = data.get('ativo', False)
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('exigir_senha_agendamento', ?)", ('true' if ativo else 'false',))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/config/bloquear_excluir_agendamento/status', methods=['GET'])
@admin_required
def bloquear_excluir_agendamento_status():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='bloquear_excluir_agendamento'")
    row = cursor.fetchone()
    conn.close()
    return jsonify({"ativo": row is not None and row[0].lower() == 'true'})

@app.route('/api/config/bloquear_excluir_agendamento/set', methods=['POST'])
@admin_required
def set_bloquear_excluir_agendamento():
    data = request.json
    ativo = data.get('ativo', False)
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO Configuracoes (chave, valor) VALUES ('bloquear_excluir_agendamento', ?)", ('true' if ativo else 'false',))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/config/quantidade_aulas/status', methods=['GET'])
def quantidade_aulas_status():
    # Rota pública para que qualquer usuário possa ler a configuração de quantidade de aulas
    quantidade = get_quantidade_aulas()
    return jsonify({"quantidade": quantidade})

@app.route('/api/config/quantidade_aulas/set', methods=['POST'])
@admin_required
def set_quantidade_aulas_route():
    data = request.json
    qtd = data.get('quantidade')
    if qtd is None or not isinstance(qtd, int) or qtd < 1 or qtd > 20:
        return jsonify({"erro": "Quantidade deve ser um número entre 1 e 20"}), 400
    set_quantidade_aulas(qtd)
    return jsonify({"status": "ok"})

@app.route('/api/config/email/status', methods=['GET'])
@admin_required
def config_email_status():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM Configuracoes WHERE chave='email_organizacao'")
    row = cursor.fetchone()
    conn.close()
    return jsonify({"email": row[0] if row and row[0] else ''})

@app.route('/api/config/email/set', methods=['POST'])
@admin_required
def set_config_email():
    data = request.json or {}
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
    return jsonify({"status": "ok"})

# ROTAS DE LIVROS (escrita protegida, leitura liberada)
@app.route('/api/livros', methods=['GET', 'POST'])
def api_livros():
    conn = db_manager.get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        if not is_admin():
            conn.close()
            return jsonify({"erro": "Acesso negado. Operação permitida apenas para administradores."}), 403
        data = request.json
        hoje = get_brasilia_today().isoformat()
        
        localizacao = data.get('localizacao', '').strip()
        if is_obrigar_localizacao_livro() and not localizacao:
            conn.close()
            return jsonify({"erro": "O campo Localização (prateleira) é obrigatório conforme configuração do sistema."}), 400

        if data.get('manual'):
            isbn = data.get('isbn', 'MANUAL_' + str(uuid.uuid4())[:8])
            titulo = data['titulo']
            autor = data['autor']
            ano = data.get('ano')
            descricao = data.get('descricao', '')
            temas = data.get('temas', '')
            categoria = data.get('categoria', 'Ficção')
            quantidade = int(data['quantidade'])
            capa = data.get('capa', '')
            if not capa:
                capa = '/static/images/placeholder.png'
        else:
            isbn = data['isbn']
            quantidade = int(data['quantidade'])
            info = buscar_livro_cascata(isbn)
            if not info:
                return jsonify({"erro": "ISBN não encontrado ou serviço indisponível"}), 404
            titulo = info['titulo']
            autor = info['autor']
            ano = info['ano_publicacao']
            descricao = info['descricao']
            temas = info['temas']
            categoria = info['categoria']
            capa = info['capa']

        cursor.execute('''
            INSERT INTO Livros (isbn, nome, autor, ano_publicacao, capa_url, descricao, temas, categoria, estoque, quantidade_disponivel, data_cadastro, localizacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (isbn, titulo, autor, ano, capa, descricao, temas, categoria, quantidade, quantidade, hoje, localizacao))
        conn.commit()
        livro_id = cursor.lastrowid
        conn.close()
        return jsonify({
            "id": livro_id, "isbn": isbn, "titulo": titulo, "autor": autor,
            "ano": ano, "capa": capa, "descricao": descricao, "temas": temas,
            "categoria": categoria, "estoque": quantidade, "disponivel": quantidade,
            "data_cadastro": hoje, "localizacao": localizacao
        }), 201

    else:
        cursor.execute('''
            SELECT id, isbn, nome, autor, ano_publicacao, capa_url, descricao, temas, categoria, estoque, quantidade_disponivel, data_cadastro, localizacao
            FROM Livros
        ''')
        livros = []
        for row in cursor.fetchall():
            livros.append({
                "id": row[0], "isbn": row[1], "titulo": row[2], "autor": row[3],
                "ano": row[4], "capa": row[5], "descricao": row[6], "temas": row[7],
                "categoria": row[8], "estoque": row[9], "disponivel": row[10],
                "data_cadastro": row[11], "localizacao": row[12] if len(row) > 12 else ''
            })
        conn.close()
        return jsonify(livros)

@app.route('/api/upload', methods=['POST'])
@admin_required
def upload_imagem():
    if 'file' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"erro": "Nome de arquivo vazio"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4()}_{filename}"

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)

        file.save(filepath)

        return jsonify({
            "url": f"/uploadedcovers/{unique_name}"
        })

    return jsonify({"erro": "Tipo de arquivo não permitido"}), 400

@app.route('/uploadedcovers/<filename>')
def uploaded_file(filename):
    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )

@app.route('/api/livros/<int:id>', methods=['PUT'])
@admin_required
def editar_livro(id):
    data = request.json
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    capa_url = data.get('capa')
    if capa_url:
        cursor.execute('UPDATE Livros SET capa_url = ? WHERE id = ?', (capa_url, id))
    cursor.execute('''
        UPDATE Livros
        SET nome = ?, autor = ?, ano_publicacao = ?, descricao = ?, temas = ?, estoque = ?, quantidade_disponivel = ?, categoria = ?, localizacao = ?
        WHERE id = ?
    ''', (
        data.get('titulo'), data.get('autor'), data.get('ano'),
        data.get('descricao'), data.get('temas'), data.get('estoque'), data.get('disponivel'),
        data.get('categoria'), data.get('localizacao', ''), id
    ))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/livros/<int:id>', methods=['DELETE'])
@admin_required
def excluir_livro(id):
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Livros WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# ROTAS DE LEITORES (escrita protegida)
@app.route('/api/leitores', methods=['GET'])
@admin_required
def api_leitores():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome, tipo, email, sala, periodo, materia, telefone FROM Usuarios WHERE tipo != "bibliotecario"')
    leitores = []
    for row in cursor.fetchall():
        leitores.append({
            "id": row[0], "nome": row[1], "tipo": row[2], "email": row[3],
            "sala": row[4], "periodo": row[5], "materia": row[6], "telefone": row[7]
        })
    conn.close()
    return jsonify(leitores)

@app.route('/api/leitores/buscar', methods=['GET'])
@admin_required
def buscar_leitor():
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify([])
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT id, nome, tipo, email, sala, periodo, materia, telefone 
                      FROM Usuarios 
                      WHERE tipo != "bibliotecario" AND nome LIKE ? 
                      ORDER BY nome LIMIT 10''', (f'%{q}%',))
    leitores = []
    for row in cursor.fetchall():
        leitores.append({
            "id": row[0], "nome": row[1], "tipo": row[2], "email": row[3],
            "sala": row[4], "periodo": row[5], "materia": row[6], "telefone": row[7]
        })
    conn.close()
    return jsonify(leitores)

@app.route('/api/leitores', methods=['POST'])
@admin_required
def criar_leitor():
    data = request.json
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    email = data.get('email')
    if data['tipo'] == 'professor' and not email:
        email = f"professor_{uuid.uuid4().hex[:8]}@bibi.local"
    cursor.execute('''
        INSERT INTO Usuarios (nome, tipo, email, sala, periodo, materia, telefone)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (data['nome'], data['tipo'], email, data.get('sala'),
          data.get('periodo'), data.get('materia'), data.get('telefone')))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"}), 201

@app.route('/api/leitores/<int:id>', methods=['PUT'])
@admin_required
def editar_leitor(id):
    data = request.json
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    email = data.get('email')
    if data['tipo'] == 'professor' and not email:
        email = f"professor_{uuid.uuid4().hex[:8]}@bibi.local"
    cursor.execute('''
        UPDATE Usuarios
        SET nome = ?, tipo = ?, email = ?, sala = ?, periodo = ?, materia = ?, telefone = ?
        WHERE id = ?
    ''', (data['nome'], data['tipo'], email, data.get('sala'),
          data.get('periodo'), data.get('materia'), data.get('telefone'), id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/leitores/<int:id>', methods=['DELETE'])
@admin_required
def excluir_leitor(id):
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Usuarios WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# ROTAS DE EMPRÉSTIMOS (escrita protegida)
@app.route('/api/emprestimos', methods=['POST'])
@admin_required
def realizar_emprestimo():
    try:
        data = request.json
        conn = db_manager.get_connection()
        cursor = conn.cursor()

        tipo = data.get('tipo')
        nome = data.get('nome')
        email = data.get('email')
        sala = data.get('sala')
        periodo = data.get('periodo')
        materia = data.get('materia')
        prazo_str = data.get('prazo', '7')
        livros = data.get('livros', [])
        telefone = data.get('telefone')
        senha_fornecida = data.get('senha', None)

        if not tipo or not nome:
            return jsonify({"erro": "Nome e tipo são obrigatórios."}), 400
        if tipo not in ('estudante', 'professor'):
            return jsonify({"erro": "Tipo de leitor inválido."}), 400

        if tipo == 'professor' and not email:
            email = f"professor_{uuid.uuid4().hex[:8]}@bibi.local"
        elif not email:
            return jsonify({"erro": "E-mail é obrigatório para estudantes."}), 400

        if is_exigir_senha_emprestimo():
            if not senha_fornecida or not verificar_senha_admin(senha_fornecida):
                return jsonify({"erro": "Senha de administrador necessária para realizar empréstimos."}), 403

        try:
            prazo = int(prazo_str) if tipo == 'estudante' else 0
        except:
            prazo = 7 if tipo == 'estudante' else 0

        if tipo == 'estudante':
            if len(livros) > 1:
                return jsonify({"erro": "Estudante pode emprestar apenas um livro por vez."}), 400
            cursor.execute('''
                SELECT COUNT(*) FROM Emprestimo e
                JOIN Usuarios u ON e.usuarios_id = u.id
                WHERE u.email = ? AND e.status IN ('Aprovado', 'Atrasado')
            ''', (email,))
            if cursor.fetchone()[0] > 0:
                return jsonify({"erro": "Este e-mail já possui um livro emprestado."}), 400

        cursor.execute('SELECT id, nome, sala, periodo, materia, telefone FROM Usuarios WHERE email = ? AND tipo = ?', (email, tipo))
        user = cursor.fetchone()
        user_id = None
        if user:
            user_id = user[0]
            updates = []
            params = []
            if user[1] != nome:
                updates.append("nome = ?")
                params.append(nome)
            if tipo == 'estudante':
                if sala is not None and user[2] != sala:
                    updates.append("sala = ?")
                    params.append(sala)
                if periodo is not None and user[3] != periodo:
                    updates.append("periodo = ?")
                    params.append(periodo)
                if telefone is not None and user[5] != telefone:
                    updates.append("telefone = ?")
                    params.append(telefone)
            else:
                if materia is not None and user[4] != materia:
                    updates.append("materia = ?")
                    params.append(materia)
                if telefone is not None and user[5] != telefone:
                    updates.append("telefone = ?")
                    params.append(telefone)

            if updates:
                query = f"UPDATE Usuarios SET {', '.join(updates)} WHERE id = ?"
                params.append(user_id)
                cursor.execute(query, params)
        else:
            cursor.execute('''
                INSERT INTO Usuarios (nome, tipo, email, sala, periodo, materia, telefone)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (nome, tipo, email, sala, periodo, materia, telefone))
            user_id = cursor.lastrowid

        hoje = get_brasilia_today()
        vencimento = hoje + timedelta(days=prazo)

        for item in livros:
            livro_id = item.get('id')
            qtd = item.get('quantidade', 1)
            if not livro_id:
                return jsonify({"erro": "ID do livro não informado."}), 400
            cursor.execute('SELECT quantidade_disponivel FROM Livros WHERE id = ?', (livro_id,))
            disp = cursor.fetchone()
            if not disp or disp[0] < qtd:
                conn.rollback()
                conn.close()
                return jsonify({"erro": f"Quantidade insuficiente para o livro ID {livro_id}."}), 400

        for item in livros:
            livro_id = item['id']
            qtd = item.get('quantidade', 1)
            cursor.execute('''
                INSERT INTO Emprestimo (usuarios_id, livros_id, data_emprestimo, data_vencimento, quantidade, status, notificacao_3dias, notificacao_hoje)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, livro_id, hoje.isoformat(), vencimento.isoformat(), qtd, 'Aprovado', 0, 0))
            cursor.execute('UPDATE Livros SET quantidade_disponivel = quantidade_disponivel - ? WHERE id = ?', (qtd, livro_id))

        conn.commit()

        cursor.execute('SELECT nome, capa_url FROM Livros WHERE id = ?', (livros[0]['id'],))
        livro_info = cursor.fetchone()
        titulo = livro_info[0]
        capa_url = livro_info[1]
        conn.close()

        if email and '@' in email and not is_email_blocked():
            threading.Thread(target=enviar_email_confirmacao, args=(email, nome, titulo, vencimento.strftime("%d/%m/%Y"), capa_url)).start()

        return jsonify({"status": "sucesso", "email_enviado": True})

    except Exception as e:
        print(f"Erro detalhado no empréstimo: {e}")
        return jsonify({"erro": f"Falha no servidor: {str(e)}"}), 500

@app.route('/api/emprestimos/ativos/count', methods=['GET'])
@admin_required
def contar_emprestimos_ativos():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Emprestimo WHERE status IN ('Aprovado', 'Atrasado')")
    count = cursor.fetchone()[0]
    conn.close()
    return jsonify({"count": count})

@app.route('/api/emprestimos/ativos', methods=['GET'])
@admin_required
def listar_emprestimos_ativos():
    threading.Thread(target=verificar_e_enviar_notificacoes).start()
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.id, u.nome as leitor, u.sala as serie, u.telefone, l.nome as livro, l.capa_url, e.data_emprestimo, e.data_vencimento, e.quantidade, e.status
        FROM Emprestimo e
        JOIN Usuarios u ON e.usuarios_id = u.id
        JOIN Livros l ON e.livros_id = l.id
        WHERE e.status IN ('Aprovado', 'Atrasado')
        ORDER BY e.data_vencimento
    ''')
    emprestimos = []
    for row in cursor.fetchall():
        emprestimos.append({
            "id": row[0], "leitor": row[1], "serie": row[2] or '', "telefone": row[3] or '',
            "livro": row[4], "capa": row[5], "data_emprestimo": row[6],
            "data_vencimento": row[7], "quantidade": row[8], "status": row[9]
        })
    conn.close()
    return jsonify(emprestimos)

@app.route('/api/emprestimos/todos', methods=['GET'])
@admin_required
def listar_todos_emprestimos():
    threading.Thread(target=verificar_e_enviar_notificacoes).start()
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.id, u.nome as leitor, u.sala as serie, u.telefone, l.nome as livro, l.capa_url, e.data_emprestimo, e.data_vencimento, e.quantidade, e.status
        FROM Emprestimo e
        JOIN Usuarios u ON e.usuarios_id = u.id
        JOIN Livros l ON e.livros_id = l.id
        ORDER BY e.data_vencimento DESC
    ''')
    emprestimos = []
    for row in cursor.fetchall():
        emprestimos.append({
            "id": row[0], "leitor": row[1], "serie": row[2] or '', "telefone": row[3] or '',
            "livro": row[4], "capa": row[5], "data_emprestimo": row[6],
            "data_vencimento": row[7], "quantidade": row[8], "status": row[9]
        })
    conn.close()
    return jsonify(emprestimos)

@app.route('/api/emprestimos/devolvidos', methods=['GET'])
@admin_required
def listar_emprestimos_devolvidos():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.id, u.nome as leitor, u.sala as serie, u.telefone, l.nome as livro, l.capa_url, e.data_emprestimo, e.data_vencimento, e.data_devolucao, e.quantidade, e.status
        FROM Emprestimo e
        JOIN Usuarios u ON e.usuarios_id = u.id
        JOIN Livros l ON e.livros_id = l.id
        WHERE e.status = 'Devolvido'
        ORDER BY e.data_devolucao DESC
    ''')
    emprestimos = []
    for row in cursor.fetchall():
        emprestimos.append({
            "id": row[0], "leitor": row[1], "serie": row[2] or '', "telefone": row[3] or '',
            "livro": row[4], "capa": row[5], "data_emprestimo": row[6],
            "data_vencimento": row[7], "data_devolucao": row[8], "quantidade": row[9], "status": row[10]
        })
    conn.close()
    return jsonify(emprestimos)

@app.route('/api/emprestimos/devolucoes-hoje', methods=['GET'])
@admin_required
def listar_devolucoes_hoje():
    hoje = get_brasilia_today().isoformat()
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.id, u.nome as leitor, u.sala as serie, u.telefone, l.nome as livro, l.capa_url, e.data_vencimento
        FROM Emprestimo e
        JOIN Usuarios u ON e.usuarios_id = u.id
        JOIN Livros l ON e.livros_id = l.id
        WHERE e.status IN ('Aprovado', 'Atrasado') AND e.data_vencimento = ?
    ''', (hoje,))
    devolucoes = []
    for row in cursor.fetchall():
        devolucoes.append({
            "id": row[0], "leitor": row[1], "serie": row[2] or '', "telefone": row[3] or '',
            "livro": row[4], "capa": row[5], "vencimento": row[6]
        })
    conn.close()
    return jsonify(devolucoes)

@app.route('/api/emprestimos/atrasos', methods=['GET'])
@admin_required
def listar_atrasos():
    threading.Thread(target=verificar_e_enviar_notificacoes).start()
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.id, u.nome as leitor, u.sala as serie, u.telefone, l.nome as livro, l.capa_url, e.data_vencimento
        FROM Emprestimo e
        JOIN Usuarios u ON e.usuarios_id = u.id
        JOIN Livros l ON e.livros_id = l.id
        WHERE e.status = 'Atrasado'
    ''')
    atrasos = []
    for row in cursor.fetchall():
        atrasos.append({
            "id": row[0], "leitor": row[1], "serie": row[2] or '', "telefone": row[3] or '',
            "livro": row[4], "capa": row[5], "vencimento": row[6]
        })
    conn.close()
    return jsonify(atrasos)

@app.route('/api/emprestimos/<int:id>/devolver', methods=['POST'])
@admin_required
def devolver_emprestimo(id):
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT livros_id, usuarios_id, quantidade FROM Emprestimo WHERE id = ?', (id,))
    emp = cursor.fetchone()
    if not emp:
        conn.close()
        return jsonify({"erro": "Empréstimo não encontrado"}), 404
    livro_id, user_id, qtd = emp
    hoje = get_brasilia_today().isoformat()
    cursor.execute('''
        UPDATE Emprestimo
        SET status = 'Devolvido', data_devolucao = ?
        WHERE id = ?
    ''', (hoje, id))
    cursor.execute('UPDATE Livros SET quantidade_disponivel = quantidade_disponivel + ? WHERE id = ?', (qtd, livro_id))
    conn.commit()

    cursor.execute('SELECT nome, email FROM Usuarios WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    cursor.execute('SELECT nome, capa_url FROM Livros WHERE id = ?', (livro_id,))
    livro_info = cursor.fetchone()
    livro_nome = livro_info[0]
    capa_url = livro_info[1]
    conn.close()

    if user and user[1] and '@' in user[1] and not is_email_blocked():
        threading.Thread(target=enviar_email_devolucao, args=(user[1], user[0], livro_nome, hoje, capa_url)).start()

    return jsonify({"status": "ok"})

@app.route('/api/emprestimos/<int:id>/renovar', methods=['POST'])
@admin_required
def renovar_emprestimo(id):
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.data_vencimento, u.tipo, u.email, u.nome, l.nome as livro_titulo, l.capa_url
        FROM Emprestimo e
        JOIN Usuarios u ON e.usuarios_id = u.id
        JOIN Livros l ON e.livros_id = l.id
        WHERE e.id = ? AND e.status IN ('Aprovado', 'Atrasado')
    ''', (id,))
    emp = cursor.fetchone()
    if not emp:
        conn.close()
        return jsonify({"erro": "Empréstimo não encontrado ou já devolvido."}), 404

    data_venc_str, tipo, email, nome, titulo, capa_url = emp
    data_venc = datetime.strptime(data_venc_str, "%Y-%m-%d").date()
    hoje = get_brasilia_today()
    if data_venc < hoje:
        data_venc = hoje
    dias_extras = 7 if tipo == 'estudante' else 1
    nova_data = data_venc + timedelta(days=dias_extras)

    cursor.execute('''
        UPDATE Emprestimo
        SET data_vencimento = ?, status = 'Aprovado', notificacao_3dias = 0, notificacao_hoje = 0
        WHERE id = ?
    ''', (nova_data.isoformat(), id))
    conn.commit()
    conn.close()

    if email and '@' in email and not is_email_blocked():
        threading.Thread(target=enviar_email_renovacao, args=(email, nome, titulo, nova_data.strftime("%d/%m/%Y"), capa_url)).start()

    return jsonify({"status": "ok", "nova_data": nova_data.isoformat()})

@app.route('/api/emprestimos/mais-emprestados', methods=['GET'])
def listar_mais_emprestados():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT l.id, l.nome, l.autor, l.capa_url, COUNT(e.id) as total_emprestimos
        FROM Emprestimo e
        JOIN Livros l ON e.livros_id = l.id
        GROUP BY l.id
        ORDER BY total_emprestimos DESC
        LIMIT 5
    ''')
    destaques = []
    for row in cursor.fetchall():
        destaques.append({
            "id": row[0],
            "titulo": row[1],
            "autor": row[2],
            "capa": row[3],
            "total_emprestimos": row[4]
        })
    conn.close()
    return jsonify(destaques)

@app.route('/api/emprestimos/ativos-por-genero', methods=['GET'])
def listar_ativos_por_genero():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT l.categoria, COUNT(*) as total
        FROM Emprestimo e
        JOIN Livros l ON e.livros_id = l.id
        WHERE e.status IN ('Aprovado', 'Atrasado')
        GROUP BY l.categoria
        ORDER BY total DESC
    ''')
    generos = []
    for row in cursor.fetchall():
        generos.append({
            "categoria": row[0],
            "total": row[1]
        })
    conn.close()
    return jsonify(generos)

@app.route('/api/emprestimos/historico-por-genero', methods=['GET'])
def listar_historico_por_genero():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT l.categoria, COUNT(*) as total
        FROM Emprestimo e
        JOIN Livros l ON e.livros_id = l.id
        GROUP BY l.categoria
        ORDER BY total DESC
    ''')
    generos = []
    for row in cursor.fetchall():
        generos.append({
            "categoria": row[0],
            "total": row[1]
        })
    conn.close()
    return jsonify(generos)

@app.route('/api/emprestimos/ranking-leitores', methods=['GET'])
def listar_ranking_leitores():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    tres_meses_atras = (get_brasilia_today() - timedelta(days=90)).isoformat()
    cursor.execute('''
        SELECT u.nome, u.sala, u.tipo, COUNT(e.id) as total
        FROM Emprestimo e
        JOIN Usuarios u ON e.usuarios_id = u.id
        WHERE e.data_emprestimo >= ?
        GROUP BY u.id
        ORDER BY total DESC
    ''', (tres_meses_atras,))
    ranking = []
    for row in cursor.fetchall():
        ranking.append({
            "nome": row[0],
            "sala": row[1] or '',
            "tipo": row[2],
            "total": row[3]
        })
    conn.close()
    return jsonify(ranking)

@app.route('/api/livros/adormecidos', methods=['GET'])
def listar_livros_adormecidos():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT l.id, l.nome, l.autor, l.capa_url
        FROM Livros l
        WHERE l.data_cadastro <= date('now', '-6 months')
        AND l.id NOT IN (
            SELECT DISTINCT e.livros_id 
            FROM Emprestimo e 
            WHERE e.data_emprestimo >= date('now', '-6 months')
        )
    ''')
    adormecidos = []
    for row in cursor.fetchall():
        adormecidos.append({
            "id": row[0],
            "titulo": row[1],
            "autor": row[2],
            "capa": row[3]
        })
    conn.close()
    return jsonify(adormecidos)

# ROTAS DE AGENDAMENTOS (escrita protegida)
@app.route('/api/agendamentos', methods=['GET'])
def api_agendamentos():
    periodo = request.args.get('periodo')
    data = request.args.get('data')
    conn = db_manager.get_connection()
    cursor = conn.cursor()

    if data:
        if periodo:
            cursor.execute('''
                SELECT id, data, periodo, dia_semana, aula, professor, materia, uso, turma
                FROM Agendamento WHERE data = ? AND periodo = ?
            ''', (data, periodo))
        else:
            cursor.execute('''
                SELECT id, data, periodo, dia_semana, aula, professor, materia, uso, turma
                FROM Agendamento WHERE data = ?
            ''', (data,))
    else:
        cursor.execute('''
            SELECT id, data, periodo, dia_semana, aula, professor, materia, uso, turma
            FROM Agendamento WHERE periodo = ?
        ''', (periodo or 'Manhã',))

    agendamentos = []
    for row in cursor.fetchall():
        agendamentos.append({
            "id": row[0],
            "data": row[1],
            "periodo": row[2],
            "dia": row[3],
            "aula": row[4],
            "professor": row[5],
            "materia": row[6],
            "uso": row[7],
            "turma": row[8]
        })
    conn.close()
    return jsonify(agendamentos)

@app.route('/api/agendamentos/datas-com-agendamentos', methods=['GET'])
def datas_com_agendamentos():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    hoje = get_brasilia_today().isoformat()
    # Retorna um agendamento representativo (o de menor id) para cada uma das próximas
    # 5 datas com agendamento, incluindo periodo/aula, para permitir que a interface
    # navegue diretamente até o período e destaque a célula correspondente.
    cursor.execute('''
        SELECT a.id, a.data, a.periodo, a.aula, a.professor, a.materia
        FROM Agendamento a
        INNER JOIN (
            SELECT data, MIN(id) as min_id
            FROM Agendamento
            WHERE date(data) >= date(?)
            GROUP BY data
            ORDER BY data
            LIMIT 5
        ) sub ON a.id = sub.min_id
        ORDER BY a.data
    ''', (hoje,))
    proximos = []
    for row in cursor.fetchall():
        proximos.append({
            "id": row[0],
            "data": row[1],
            "periodo": row[2],
            "aula": row[3],
            "professor": row[4],
            "materia": row[5]
        })
    conn.close()
    return jsonify(proximos)

@app.route('/api/agendamentos/passados', methods=['GET'])
def agendamentos_passados():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    hoje = get_brasilia_today().isoformat()
    cursor.execute('''
        SELECT id, data, periodo, dia_semana, aula, professor, materia, uso, turma
        FROM Agendamento 
        WHERE date(data) < date(?)
        ORDER BY data DESC
        LIMIT 5
    ''', (hoje,))
    passados = []
    for row in cursor.fetchall():
        passados.append({
            "id": row[0],
            "data": row[1],
            "periodo": row[2],
            "dia": row[3],
            "aula": row[4],
            "professor": row[5],
            "materia": row[6],
            "uso": row[7],
            "turma": row[8]
        })
    conn.close()
    return jsonify(passados)

@app.route('/api/agendamentos', methods=['POST'])
@admin_required
def criar_agendamento():
    data = request.json
    data_ag = data.get('data')
    if data_ag:
        data_date = datetime.strptime(data_ag, "%Y-%m-%d").date()
        hoje = get_brasilia_today()
        if data_date < hoje:
            return jsonify({"erro": "Não é possível criar agendamentos em datas passadas."}), 400

    senha_fornecida = data.get('senha', None)
    if is_exigir_senha_agendamento():
        if not senha_fornecida or not verificar_senha_admin(senha_fornecida):
            return jsonify({"erro": "Senha de administrador necessária para criar agendamentos."}), 403

    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Agendamento (data, periodo, dia_semana, aula, professor, materia, uso, turma)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('data'),
        data['periodo'],
        data['dia'],
        data['aula'],
        data['professor'],
        data['materia'],
        data['uso'],
        data.get('turma', '')
    ))
    conn.commit()
    novo_id = cursor.lastrowid
    conn.close()
    return jsonify({"id": novo_id, "status": "ok"}), 201

@app.route('/api/agendamentos/<int:id>', methods=['DELETE'])
@admin_required
def excluir_agendamento(id):
    if is_bloquear_excluir_agendamento():
        return jsonify({"erro": "Exclusão de agendamentos está bloqueada nas configurações."}), 403
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Agendamento WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# Função auxiliar para gerar o HTML do app com condicionais de admin
def get_app_html(admin, quantidade_aulas=None):
    # Se não for admin, os menus restritos são omitidos completamente
    nav_dashboard = ''
    nav_emprestimos = ''
    nav_leitores = ''
    btn_adicionar_livro = ''
    config_button = ''
    right_bar_buttons = ''
    acervo_header_btn = ''
    leitores_list_buttons = ''
    modal_add_livro = ''
    modal_edit_livro = ''
    modal_leitor = ''
    modal_emprestimo_rapido = ''
    modal_configuracoes = ''
    modal_senha_config = ''
    if admin:
        nav_dashboard = '<li onclick="tab(\'dash\')" id="m-dash"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-clipboard-data" viewBox="0 0 16 16"><path d="M4 11a1 1 0 1 1 2 0v1a1 1 0 1 1-2 0zm6-4a1 1 0 1 1 2 0v5a1 1 0 1 1-2 0zM7 9a1 1 0 0 1 2 0v3a1 1 0 1 1-2 0z"/><path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1z"/><path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0z"/></svg><span>Dashboard</span><span class="shortcut">Ctrl+1</span></li>'
        nav_emprestimos = '<li onclick="tab(\'emp\')" id="m-emp"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-list-check" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M5 11.5a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5m0-4a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5m0-4a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5M3.854 2.146a.5.5 0 0 1 0 .708l-1.5 1.5a.5.5 0 0 1-.708 0l-.5-.5a.5.5 0 1 1 .708-.708l.146.147 1.146-1.147a.5.5 0 0 1 .708 0m0 4a.5.5 0 0 1 0 .708l-1.5 1.5a.5.5 0 0 1-.708 0l-.5-.5a.5.5 0 1 1 .708-.708l.146.147 1.146-1.147a.5.5 0 0 1 .708 0m0 4a.5.5 0 0 1 0 .708l-1.5 1.5a.5.5 0 0 1-.708 0l-.5-.5a.5.5 0 0 1 .708-.708l.146.147 1.146-1.147a.5.5 0 0 1 .708 0"/></svg><span>Empréstimos</span><span class="shortcut">Ctrl+3</span></li>'
        nav_leitores = '<li onclick="tab(\'lei\')" id="m-lei"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-person" viewBox="0 0 16 16"><path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6m2-3a2 2 0 1 1-4 0 2 2 0 0 1 4 0m4 8c0 1-1 1-1 1H3s-1 0-1-1 1-4 6-4 6 3 6 4m-1-.004c-.001-.246-.154-.986-.832-1.664C11.516 10.68 10.289 10 8 10s-3.516.68-4.168 1.332c-.678.678-.83 1.418-.832 1.664z"/></svg><span>Leitores</span><span class="shortcut">Ctrl+5</span></li>'
        btn_adicionar_livro = '<button class="btn-primary" style="width:auto;" onclick="openModal(\'modalAddLivro\')">+ Adicionar Livro</button>'
        config_button = '<div class="config-item" onclick="abrirConfiguracoes()" title="Configurações"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-gear-wide-connected" viewBox="0 0 16 16"><path d="M7.068.727c.243-.97 1.62-.97 1.864 0l.071.286a.96.96 0 0 0 1.622.434l.205-.211c.695-.719 1.888-.03 1.613.931l-.08.284a.96.96 0 0 0 1.187 1.187l.283-.081c.96-.275 1.65.918.931 1.613l-.211.205a.96.96 0 0 0 .434 1.622l.286.071c.97.243.97 1.62 0 1.864l-.286.071a.96.96 0 0 0-.434 1.622l.211.205c.719.695.03 1.888-.931 1.613l-.284-.08a.96.96 0 0 0-1.187 1.187l.081.283c.275.96-.918 1.65-1.613.931l-.205-.211a.96.96 0 0 0-1.622.434l-.071.286c-.243.97-1.62.97-1.864 0l-.071-.286a.96.96 0 0 0-1.622-.434l-.205.211c-.695.719-1.888.03-1.613-.931l.08-.284a.96.96 0 0 0-1.186-1.187l-.284.081c-.96.275-1.65-.918-.931-1.613l.211-.205a.96.96 0 0 0-.434-1.622l-.286-.071c-.97-.243-.97-1.62 0-1.864l.286-.071a.96.96 0 0 0 .434-1.622l-.211-.205c-.719-.695-.03-1.888.931-1.613l.284.08a.96.96 0 0 0 1.187-1.186l-.081-.284c-.275-.96.918-1.65 1.613-.931l.205.211a.96.96 0 0 0 1.622-.434zM12.973 8.5H8.25l-2.834 3.779A4.998 4.998 0 0 0 12.973 8.5m0-1a4.998 4.998 0 0 0-7.557-3.779l2.834 3.78zM5.048 3.967l-.087.065zm-.431.355A4.98 4.98 0 0 0 3.002 8c0 1.455.622 2.765 1.615 3.678L7.375 8zm.344 7.646.087.065z"/></svg></div>'
        right_bar_buttons = '<button class="btn-primary" id="btn-emprestar" style="margin-bottom:10px;" onclick="emprestarSelecionado()">Emprestar este</button><button class="btn-primary" style="margin-bottom:10px;" onclick="editarLivroSelecionado()">Editar</button><button class="btn-primary" id="btn-excluir-livro" style="background:#b33;" onclick="confirmarExclusaoLivro()">Excluir Livro</button>'
        acervo_header_btn = '<button class="btn-primary" style="width:auto;" onclick="openModal(\'modalAddLivro\')">+ Adicionar Livro</button>'
        leitores_list_buttons = '<span><button class="btn-primary btn-small" onclick="editarLeitor(${l.id})">Editar</button><button class="btn-primary btn-small" style="background:#b33;" onclick="excluirLeitor(${l.id})">Excluir</button></span>'
        modal_add_livro = '''
            <div id="modalAddLivro" class="modal">
                <div class="modal-content">
                    <h3>Adicionar Livro</h3>
                    <input type="text" id="add-isbn" placeholder="ISBN (ex: 9788533302273)">
                    <input type="number" id="add-qtd" placeholder="Quantidade">
                    <button class="btn-primary" id="btn-buscar-salvar" onclick="salvarLivro()">Buscar e Salvar</button>
                    <button class="btn-primary" style="margin-top:10px;" onclick="openModalManual()">Adicionar Manualmente</button>
                    <button class="btn-cancel" style="margin-top:10px;" onclick="closeModal('modalAddLivro')">Cancelar</button>
                </div>
            </div>
            <div id="modalManualLivro" class="modal">
                <div class="modal-content">
                    <h3>Cadastro Manual de Livro</h3>
                    <label>ISBN (opcional)</label><input type="text" id="manual-isbn">
                    <label>Título *</label><input type="text" id="manual-titulo">
                    <label>Autor *</label><input type="text" id="manual-autor">
                    <div class="campo-ano"><label>Ano</label><input type="number" id="manual-ano"></div>
                    <div class="campo-descricao"><label>Descrição</label><textarea id="manual-descricao" rows="3"></textarea></div>
                    <div class="campo-temas"><label>Temas (separados por vírgula)</label><input type="text" id="manual-temas" placeholder="Ficção, Aventura..."></div>
                    <div class="campo-categoria">
                        <label>Categoria</label>
                        <div id="custom-select-categoria-manual" class="custom-select"></div>
                        <input type="hidden" id="manual-categoria" value="Ficção">
                    </div>
                    <div class="campo-localizacao" id="campo-localizacao-manual" style="display:none;">
                        <label>Localização (Prateleira) *</label>
                        <input type="text" id="manual-localizacao" placeholder="Ex: Prateleira A, Corredor 3">
                    </div>
                    <label>Quantidade *</label><input type="number" id="manual-qtd" min="1" value="1">
                    <label>Capa (upload, arraste ou cole)</label>
                    <input type="file" id="manual-capa-file" accept="image/*" onchange="previewCapaManual(event)">
                    <div class="capa-preview" id="manual-capa-preview"><div class="preview-text">Arraste ou cole imagem aqui</div></div>
                    <input type="hidden" id="manual-capa-url">
                    <button class="btn-primary" id="btn-salvar-manual" onclick="salvarLivroManual()">Salvar Livro</button>
                    <button class="btn-cancel" style="margin-top:10px;" onclick="closeModal('modalManualLivro')">Cancelar</button>
                </div>
            </div>
            <div id="modalEditarLivro" class="modal">
                <div class="modal-content">
                    <h3>Editar Livro</h3>
                    <input type="hidden" id="edit-id">
                    <label>Título</label><input type="text" id="edit-titulo">
                    <label>Autor</label><input type="text" id="edit-autor">
                    <div class="campo-ano"><label>Ano</label><input type="number" id="edit-ano"></div>
                    <div class="campo-descricao"><label>Descrição</label><textarea id="edit-descricao" rows="3"></textarea></div>
                    <div class="campo-temas"><label>Temas</label><input type="text" id="edit-temas" placeholder="Ficção, Aventura..."></div>
                    <div class="campo-categoria">
                        <label>Categoria</label>
                        <div id="custom-select-categoria-edit" class="custom-select"></div>
                        <input type="hidden" id="edit-categoria">
                    </div>
                    <div class="campo-localizacao" id="campo-localizacao-edit" style="display:none;">
                        <label>Localização (Prateleira)</label>
                        <input type="text" id="edit-localizacao" placeholder="Ex: Prateleira A, Corredor 3">
                    </div>
                    <label>Estoque Total</label><input type="number" id="edit-estoque">
                    <label>Disponível</label><input type="number" id="edit-disponivel">
                    <label>Nova Capa (opcional - arraste ou cole)</label>
                    <input type="file" id="edit-capa-file" accept="image/*" onchange="previewCapaEdit(event)">
                    <div class="capa-preview" id="edit-capa-preview"><div class="preview-text">Arraste ou cole imagem aqui</div></div>
                    <input type="hidden" id="edit-capa-url">
                    <button class="btn-primary" id="btn-salvar-edicao" onclick="salvarEdicaoLivro()">Salvar Alterações</button>
                    <button class="btn-cancel" style="margin-top:10px;" onclick="closeModal('modalEditarLivro')">Cancelar</button>
                </div>
            </div>
        '''
        modal_leitor = '''
            <div id="modalLeitor" class="modal">
                <div class="modal-content">
                    <h3 id="leitor-titulo">Novo Leitor</h3>
                    <input type="hidden" id="leitor-id">
                    <label>Tipo</label>
                    <div id="custom-select-tipo-leitor" class="custom-select"></div>
                    <input type="hidden" id="leitor-tipo" value="estudante">
                    <div id="leitor-aluno">
                        <label>Nome</label><input type="text" id="leitor-nome" placeholder="Nome completo">
                        <label>Sala</label><input type="text" id="leitor-sala" placeholder="Ex: 9° ano">
                        <small class="instrucao-ordinal">(Para digitar º use AltGr + °)</small>
                        <label>Período</label><input type="text" id="leitor-periodo" placeholder="Manhã / Tarde">
                        <label>E-mail</label><input type="email" id="leitor-email" placeholder="email@escola.com">
                        <label>Telefone do Aluno</label><input type="text" id="leitor-telefone" placeholder="(11) 99999-9999" oninput="aplicarMascaraTelefone(this)">
                    </div>
                    <div id="leitor-prof" style="display:none;">
                        <label>Nome</label><input type="text" id="leitor-nome-prof" placeholder="Nome do professor">
                        <label>Matéria</label><input type="text" id="leitor-materia" placeholder="Disciplina">
                        <label>E-mail (opcional)</label><input type="email" id="leitor-email-prof" placeholder="email@escola.com">
                    </div>
                    <button class="btn-primary" id="btn-salvar-leitor" onclick="salvarLeitor()">Salvar</button>
                    <button class="btn-cancel" style="margin-top:10px;" onclick="closeModal('modalLeitor')">Cancelar</button>
                </div>
            </div>
        '''
        modal_emprestimo_rapido = '''
            <div id="modalEmprestimoRapido" class="modal">
                <div class="modal-content">
                    <h3>Empréstimo Rápido</h3>
                    <input type="hidden" id="emprestimo-rapido-livro-id">
                    <label>Tipo de Leitor</label>
                    <div id="custom-select-tipo-rapido" class="custom-select"></div>
                    <input type="hidden" id="rapido-tipo" value="estudante">
                    <div id="rapido-aluno">
                        <label>Nome</label>
                        <div class="relative-container">
                            <input type="text" id="rapido-nome" placeholder="Nome completo" autocomplete="off" oninput="buscarLeitoresAutocomplete()">
                            <div class="autocomplete-suggestions" id="rapido-nome-suggestions"></div>
                        </div>
                        <label>Sala/Turma</label><input type="text" id="rapido-sala" placeholder="Ex: 9° ano" onblur="formatarSala()">
                        <small class="instrucao-ordinal">(Para digitar º use AltGr + °)</small>
                        <label>Período</label>
                        <div id="custom-select-periodo-rapido" class="custom-select"></div>
                        <input type="hidden" id="rapido-periodo" value="Manhã">
                        <label>E-mail</label><input type="email" id="rapido-email" placeholder="email@escola.com">
                        <div class="campo-telefone-aluno">
                            <label>Telefone do Aluno</label><input type="text" id="rapido-telefone" placeholder="(11) 99999-9999" oninput="aplicarMascaraTelefone(this)">
                        </div>
                        <label>Prazo (dias)</label>
                        <div id="custom-select-prazo-rapido" class="custom-select"></div>
                        <input type="hidden" id="rapido-prazo" value="7">
                    </div>
                    <div id="rapido-professor" style="display:none;">
                        <label>Nome</label><input type="text" id="rapido-nome-prof" placeholder="Nome do professor">
                        <label>Matéria</label><input type="text" id="rapido-materia" placeholder="Disciplina">
                        <p style="font-size:12px; margin:15px 0 20px 0; color: var(--text);">Devolução no mesmo dia.</p>
                    </div>
                    <button class="btn-primary" id="btn-confirmar-emprestimo" onclick="confirmarEmprestimoRapido()">Confirmar Empréstimo</button>
                    <button class="btn-cancel" style="margin-top:10px;" onclick="closeModal('modalEmprestimoRapido')">Cancelar</button>
                </div>
            </div>
        '''
        modal_configuracoes = '''
            <div id="modalConfiguracoes" class="modal">
                <div class="modal-content" style="max-width:560px;">
                    <h3>Configurações</h3>
                    <div class="config-panel" id="lista-config-toggles">
                    </div>
                    <button class="btn-primary" onclick="salvarConfigGerais()">Salvar</button>
                    <button class="btn-cancel" style="margin-top:10px;" onclick="closeModal('modalConfiguracoes')">Cancelar</button>
                </div>
            </div>
            <div id="modalConfigAgenda" class="modal">
                <div class="modal-content">
                    <h3>Configurações da Agenda</h3>
                    <div class="config-panel">
                        <label>Quantidade de aulas por dia:</label>
                        <input type="number" id="cfg-qtd-aulas" min="1" max="20" value="6">
                    </div>
                    <button class="btn-primary" id="btn-salvar-config" onclick="salvarConfigAgenda()">Salvar Configurações</button>
                    <button class="btn-cancel" style="margin-top:10px;" onclick="closeModal('modalConfigAgenda')">Cancelar</button>
                </div>
            </div>
        '''
        modal_senha_config = '''
            <div id="modalSenhaConfig" class="modal">
                <div class="modal-content" style="max-width:400px;">
                    <h3 id="senha-titulo">Acessar Configurações</h3>
                    <p id="senha-mensagem" style="margin:10px 0;">Digite a senha (4 caracteres):</p>
                    <input type="password" id="senha-input" class="pin-simple" maxlength="4" placeholder="****" autocomplete="off">
                    <input type="password" id="senha-confirm" class="pin-simple" maxlength="4" placeholder="****" style="display:none;" autocomplete="off">
                    <button class="btn-primary" id="btn-senha" style="margin-top:15px;" onclick="verificarSenhaConfig()">Ok</button>
                    <button class="btn-cancel" style="margin-top:10px;" onclick="closeModal('modalSenhaConfig')">Cancelar</button>
                </div>
            </div>
        '''

    # Se a quantidade de aulas não foi fornecida, busca do banco (fallback)
    if quantidade_aulas is None:
        quantidade_aulas = get_quantidade_aulas()
    
    # Construir o HTML completo com base na flag admin
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.5, user-scalable=yes">
        <title>BIBI - Sistema</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700&display=swap');
            :root {{
                --bg: #e2e8f0; --app: #fdfcfaf0; --main: #f5eee6;
                --dark: #3e332a; --light: #8c8279; --accent: #e5d8cc;
                --ocupado: #d4b59e; --alert-border: #A52A2A; --today-border: #CD853F;
                --text: #3e332a; --card-bg: white; --btn-cancel: #aaa;
                --green-earth: #7d9b5e;
                --cal-bg: #ffffff;
                --cal-header-bg: #ffffff;
                --cal-text: #5d4037;
                --cal-border: #ece4d9;
                --cal-hover: #ece4d9;
                --fp-bg: #ffffff;
                --fp-day-hover: #e5d8cc;
                --select-bg: white;
                --select-border: #ccc;
                --select-hover: #e5d8cc;
                --select-arrow: #8c8279;
                --fake-select-bg: #fdfaf5;
                --fake-select-text: #5d4037;
                --fake-options-bg: #ffffff;
                --agenda-panel-bg: #f9f6f1;
            }}
            .dark-mode {{
                --bg: #1e1e1e; --app: #2d2a26f0; --main: #3c332c;
                --dark: #a3968c; --light: #b7aca2; --accent: #5a4e44;
                --ocupado: #6b5b4e; --alert-border: #b85c5c; --today-border: #c99b6c;
                --text: #f0e7de; --card-bg: #4a3f38; --btn-cancel: #666;
                --green-earth: #8b9a6e;
                --cal-bg: #3c332c;
                --cal-header-bg: #3c332c;
                --cal-text: #f0e7de;
                --cal-border: #5a4e44;
                --cal-hover: #5a4e44;
                --fp-bg: #3c332c;
                --fp-day-hover: #5a4e44;
                --select-bg: #2d2926;
                --select-border: #5a4e44;
                --select-hover: #5a4e44;
                --select-arrow: #b7aca2;
                --fake-select-bg: #2d2926;
                --fake-select-text: #f0e7de;
                --fake-options-bg: #2d2926;
                --agenda-panel-bg: #2b2724;
            }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Nunito', sans-serif; }}
            body {{ 
                background: var(--bg); 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                min-height: 100vh;
                padding: 10px;
                color: var(--text);
            }}
            .app-container {{ 
                width: 100%; 
                max-width: 1400px; 
                height: 95vh; 
                background: var(--app); 
                border-radius: 20px; 
                display: grid;
                grid-template-columns: 260px 1fr 320px;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }}
            .sidebar {{ 
                padding: 25px 15px; 
                border-right: 2px dashed var(--accent); 
                display: flex; 
                flex-direction: column; 
                background: var(--app);
                overflow-y: auto;
            }}
            .logo {{ 
                font-size: 28px; font-weight: 800; margin-bottom: 20px; 
                display: flex; align-items: center; gap: 10px; 
                cursor: pointer;
            }}
            .logo img {{ width: 36px; height: 36px; }}
            .nav-menu {{ 
                list-style: none; 
                display: flex; flex-direction: column; gap: 5px;
                margin-bottom: 15px;
            }}
            .nav-menu li {{ 
                padding: 12px 12px;
                cursor: pointer;
                color: var(--light);
                font-weight: 600;
                border-radius: 10px;
                transition: 0.2s;
                display: flex;
                align-items: center;
                gap: 10px;
                white-space: nowrap;
            }}

            .nav-menu li span.shortcut {{
                display: none;
            }}

            .nav-menu li svg {{
                width: 20px;
                height: 20px;
                fill: currentColor;
                flex-shrink: 0;
            }}

            .nav-menu li:hover,
            .nav-menu li.active {{
                background: var(--accent);
                color: var(--dark);
            }}

            .sidebar-buttons {{
                display: flex;
                justify-content: flex-end;
                gap: 12px;
                margin-bottom: 20px;
                margin-top: 8px;
            }}
            .config-item, .theme-item {{
                background: transparent;
                color: var(--light);
                cursor: pointer;
                padding: 8px 12px;
                border-radius: 10px;
                transition: transform 0.05s linear;
                display: inline-flex;
                align-items: center;
                justify-content: center;
            }}
            .config-item:hover, .theme-item:hover {{
                background: var(--accent);
                color: var(--dark);
            }}
            .config-item:active, .theme-item:active {{
                transform: scale(0.92);
            }}
            .config-item svg, .theme-item svg {{
                width: 22px;
                height: 22px;
                fill: currentColor;
            }}

            .cat-container {{
                text-align: center;
                width: 100%;
                margin-top: auto;
                padding-top: 20px;
            }}
            .cat-waving {{
                width: 140px; max-width: 100%; height: auto;
                border-radius: 20px; opacity: 0.9; 
                display: block; margin: 0 auto;
            }}

            .content-area {{ 
                padding: 20px; 
                background: var(--main); 
                margin: 15px; 
                border-radius: 20px; 
                overflow-y: auto; 
                position: relative; 
            }}
            .right-bar {{ 
                padding: 20px; 
                border-left: 2px dashed var(--accent); 
                background: var(--app);
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                text-align: center;
            }}
            .section {{ display: none; }}
            .section.active {{ display: block; }}

            .section-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                flex-wrap: wrap;
                gap: 10px;
            }}
            .section-header h2 {{
                margin-bottom: 0;
            }}

            .shelf {{ 
                margin-bottom: 30px; 
                padding-top: 10px;
            }}
            .books-grid {{ 
                display: flex; gap: 15px; padding: 10px; 
                overflow-x: auto; overflow-y: visible;
                scroll-behavior: smooth;
                -webkit-overflow-scrolling: touch;
                min-height: 130px;
            }}
            .books-grid::-webkit-scrollbar {{
                height: 6px;
            }}
            .books-grid::-webkit-scrollbar-thumb {{
                background: var(--accent);
                border-radius: 10px;
            }}
            .book {{ 
                flex: 0 0 auto;
                width: 80px; height: 110px; background: #ccc; border-radius: 4px; 
                cursor: pointer; transition: transform 0.3s; background-size: cover;
                box-shadow: 2px 4px 8px rgba(0,0,0,0.2);
                margin-top: 5px;
            }}
            .book:hover {{ transform: translateY(-10px) scale(1.05); }}
            .shelf-base {{ height: 8px; background: #d5c3b1; border-radius: 4px; width: 100%; margin-top: 5px; }}
            .dash-grid {{ 
                display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); 
                gap: 15px; margin-bottom: 30px; 
            }}
            .card {{ 
                background: var(--card-bg); padding: 15px; border-radius: 15px; text-align: center; 
                border-left: 4px solid var(--dark); cursor: pointer; 
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            }}
            .card.alert {{ border-left-color: var(--alert-border); }}
            .card.today {{ border-left-color: var(--today-border); }}
            .card.green {{ border-left-color: var(--green-earth); }}
            table {{ width: 100%; border-collapse: collapse; background: var(--card-bg); border-radius: 10px; overflow: hidden; }}
            th, td {{ padding: 12px 8px; border: 1px solid var(--accent); text-align: center; font-size: 13px; }}
            th {{ background: var(--accent); }}
            .ocupado {{ background-color: var(--ocupado); font-weight: bold; cursor: pointer; }}
            .detail-capa {{ 
                width: 140px; height: 200px; background: #eee; margin: 0 auto 15px; 
                border-radius: 8px; background-size: cover; box-shadow: 0 5px 15px rgba(0,0,0,0.1); 
            }}
            input, select, textarea {{ 
                width: 100%; padding: 8px; margin: 5px 0 15px; border: 1px solid #ccc; border-radius: 8px; 
                background: var(--card-bg); color: var(--text);
            }}
            .btn-primary {{ 
                background: var(--dark); color: white; border: none; padding: 10px 20px; 
                border-radius: 8px; cursor: pointer; width: 100%; font-weight: bold; 
            }}
            .btn-primary:disabled {{
                opacity: 0.5; cursor: not-allowed;
            }}
            .btn-cancel {{ 
                background: var(--btn-cancel); color: white; border: none; padding: 10px 20px; 
                border-radius: 8px; cursor: pointer; width: 100%; font-weight: bold; 
            }}
            .btn-small {{ padding: 5px 10px; width: auto; }}
            .btn-filtro {{
                padding: 8px 16px; width: auto; border-radius: 20px; font-size: 13px;
                border: none; cursor: pointer; font-weight: bold; transition: all 0.2s;
            }}
            .btn-filtro.active-filtro {{
                box-shadow: 0 0 0 3px var(--dark);
                transform: scale(1.05);
            }}
            .btn-filtro.green {{ background: var(--green-earth); }}
            .modal {{ 
                position: fixed; top:0; left:0; width:100%; height:100%; 
                background: rgba(0,0,0,0.5); display:none; justify-content:center; align-items:center; z-index:1000; 
            }}
            .modal-content {{ 
                background: var(--app); padding: 30px; border-radius: 20px; width: 90%; max-width: 500px; 
                max-height: 80vh; overflow-y: auto; 
            }}
            .badge {{ background: var(--accent); padding: 2px 8px; border-radius: 12px; font-size: 12px; }}
            .livro-item {{ 
                display: flex; justify-content: space-between; align-items: center; 
                padding: 8px; border-bottom: 1px solid #ddd; 
            }}
            .periodo-selector {{ margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }}
            .search-box {{ margin-bottom: 15px; }}
            .toast-container {{ position: fixed; top: 20px; right: 20px; z-index: 9999; }}
            .toast {{ 
                background: #333; color: white; padding: 12px 20px; border-radius: 8px; 
                margin-bottom: 10px; opacity: 0.9; transition: opacity 0.3s; 
            }}
            .toast.success {{ background: #2e7d32; }}
            .toast.error {{ background: #c62828; }}
            .toast.warning {{ background: #f57c00; }}

            .dashboard-row {{
                display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 20px;
            }}
            .dashboard-panel {{
                flex: 1; min-width: 280px; background: var(--card-bg); 
                border-radius: 15px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.06);
            }}
            .dashboard-panel h3 {{ margin-bottom: 15px; font-size: 16px; }}
            .ranking-list {{ 
                padding-left: 20px; 
                max-height: 300px; 
                overflow-y: auto; 
            }}
            .ranking-list li {{ margin-bottom: 8px; font-size: 14px; }}
            .adormecido-tag {{
                display: inline-block; background: var(--accent); padding: 6px 12px; 
                border-radius: 20px; font-size: 12px; margin: 4px; cursor: pointer;
            }}
            .adormecido-tag:hover {{ background: var(--ocupado); }}

            .top-livros-grid {{
                display: flex; flex-direction: column; gap: 15px;
            }}
            .top-livro-item {{
                display: flex; align-items: center; gap: 15px;
                padding: 12px; background: var(--main); border-radius: 12px;
                transition: transform 0.2s; cursor: pointer;
            }}
            .top-livro-item:hover {{ transform: translateX(5px); }}
            .top-livro-capa {{
                width: 50px; height: 70px; border-radius: 6px;
                background-size: cover; background-position: center;
                box-shadow: 0 3px 8px rgba(0,0,0,0.15); flex-shrink: 0;
            }}
            .top-livro-info {{
                flex: 1; text-align: left;
            }}
            .top-livro-info h4 {{ margin: 0 0 4px 0; font-size: 14px; }}
            .top-livro-info p {{ margin: 0; font-size: 12px; color: var(--light); }}
            .top-livro-badge {{
                background: var(--dark); color: white; font-size: 12px;
                padding: 4px 12px; border-radius: 20px; font-weight: bold;
            }}

            .agenda-container {{
                display: flex;
                flex-direction: column;
                gap: 10px;
            }}
            .agenda-header {{
                margin-bottom: 5px;
            }}
            .periodo-selector {{
                margin-bottom: 8px;
                gap: 8px;
            }}
            .agenda-tabela {{
                overflow-x: auto;
                margin-bottom: 8px;
            }}
            .agendas-laterais {{
                margin-top: 8px;
                padding: 10px 12px;
                max-height: 180px;
                background: var(--agenda-panel-bg);
                border-radius: 12px;
                border: 1px solid var(--accent);
            }}
            .agendas-laterais h4 {{
                margin-bottom: 5px;
                font-size: 14px;
            }}
            #tabela-agenda th, #tabela-agenda td {{
                padding: 6px 8px;
                font-size: 12px;
            }}
            .proximo-dia, .passado-dia {{
                display: inline-block;
                margin: 2px 4px;
                padding: 2px 8px;
                background: var(--accent);
                border-radius: 20px;
                cursor: pointer;
                font-size: 11px;
                font-weight: bold;
            }}
            .passado-dia {{ opacity: 0.7; }}

            .switch {{
                position: relative;
                display: inline-block;
                width: 50px;
                height: 26px;
                flex-shrink: 0;
            }}
            .switch input {{
                opacity: 0;
                width: 0;
                height: 0;
            }}
            .slider {{
                position: absolute;
                cursor: pointer;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: var(--accent);
                transition: .4s;
                border-radius: 34px;
            }}
            .slider:before {{
                position: absolute;
                content: "";
                height: 18px;
                width: 18px;
                left: 4px;
                bottom: 4px;
                background-color: white;
                transition: .4s;
                border-radius: 50%;
            }}
            input:checked + .slider {{
                background-color: var(--dark);
            }}
            input:checked + .slider:before {{
                transform: translateX(24px);
            }}

            .flatpickr-calendar .custom-fp-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px;
                background: var(--cal-header-bg);
                border-bottom: 1px solid var(--cal-border);
                gap: 10px;
            }}
            .flatpickr-calendar .custom-fp-header .fake-select {{
                position: relative;
                background: var(--fake-select-bg);
                border: 1px solid var(--cal-border);
                border-radius: 4px;
                padding: 6px 12px;
                cursor: pointer;
                font-size: 14px;
                color: var(--fake-select-text);
                min-width: 130px;
                text-align: center;
                flex: 1;
                font-weight: 600;
            }}
            .flatpickr-calendar .custom-fp-header .fake-select .fake-options {{
                position: absolute;
                top: 100%;
                left: 0;
                background: var(--fake-options-bg);
                border: 1px solid var(--cal-border);
                border-radius: 4px;
                width: 100%;
                max-height: 200px;
                overflow-y: auto;
                z-index: 1000;
                display: none;
            }}
            .flatpickr-calendar .custom-fp-header .fake-select.active .fake-options {{
                display: block;
            }}
            .flatpickr-calendar .custom-fp-header .fake-select .fake-options div {{
                padding: 8px 12px;
                cursor: pointer;
                color: var(--fake-select-text);
                text-align: center;
            }}
            .flatpickr-calendar .custom-fp-header .fake-select .fake-options div:hover {{
                background: var(--cal-hover);
            }}

            .tabela-emprestimos {{
                width: 100%;
                border-collapse: collapse;
                font-size: 13px;
            }}
            .tabela-emprestimos th, .tabela-emprestimos td {{
                border: 1px solid var(--accent);
                padding: 10px 8px;
                text-align: center;
                vertical-align: middle;
            }}
            .tabela-emprestimos th {{
                background: var(--accent);
                color: var(--dark);
                font-weight: bold;
            }}
            .capa-mini {{
                width: 40px;
                height: 55px;
                background-size: cover;
                background-position: center;
                border-radius: 4px;
                margin: 0 auto;
            }}
            /* Botões de ação com espaçamento */
            .acoes-botoes {{
                display: flex;
                gap: 8px;
                justify-content: center;
                flex-wrap: wrap;
            }}
            .livro-item span:last-child {{
                display: flex;
                gap: 8px;
                align-items: center;
            }}
            .autocomplete-suggestions {{
                position: absolute;
                background: var(--card-bg);
                border: 1px solid var(--accent);
                border-radius: 8px;
                max-height: 200px;
                overflow-y: auto;
                z-index: 1000;
                width: 100%;
                display: none;
                margin-top: -15px;
            }}
            .autocomplete-suggestions div {{
                padding: 10px 12px;
                cursor: pointer;
                color: var(--text);
                font-size: 14px;
            }}
            .autocomplete-suggestions div:hover {{
                background: var(--accent);
            }}
            .relative-container {{
                position: relative;
            }}
            .instrucao-ordinal {{
                font-size: 11px;
                color: var(--light);
                margin-top: -10px;
                margin-bottom: 10px;
                display: block;
            }}
            .custom-select {{
                position: relative;
                width: 100%;
                margin: 5px 0 15px;
            }}
            .custom-select .select-selected {{
                background: var(--select-bg);
                padding: 8px 12px;
                border: 1px solid var(--select-border);
                border-radius: 8px;
                cursor: pointer;
                display: flex;
                justify-content: space-between;
                align-items: center;
                color: var(--text);
            }}
            .custom-select .select-selected:after {{
                content: "▼";
                font-size: 12px;
                color: var(--select-arrow);
            }}
            .custom-select .select-items {{
                position: absolute;
                background: var(--select-bg);
                top: 100%;
                left: 0;
                right: 0;
                z-index: 99;
                border: 1px solid var(--select-border);
                border-radius: 8px;
                max-height: 200px;
                overflow-y: auto;
                display: none;
            }}
            .custom-select .select-items div {{
                padding: 8px 12px;
                cursor: pointer;
                color: var(--text);
            }}
            .custom-select .select-items div:hover {{
                background: var(--select-hover);
            }}
            .capa-preview {{
                width: 100px; 
                height: 140px; 
                background: #eee; 
                margin: 10px auto;
                border-radius: 8px; 
                background-size: cover; 
                background-position: center;
                border: 1px solid var(--accent);
                position: relative;
                display: flex;
                align-items: center;
                justify-content: center;
                background-color: var(--card-bg);
            }}
            .capa-preview .preview-text {{
                font-size: 10px;
                color: #888;
                text-align: center;
                background: rgba(255,255,255,0.7);
                padding: 4px 8px;
                border-radius: 12px;
                pointer-events: none;
            }}
            .capa-preview.has-image .preview-text {{
                display: none;
            }}
            .config-panel {{
                background: var(--card-bg); padding: 20px; border-radius: 15px; margin: 15px 0;
            }}
            .config-panel .config-subtitulo {{
                margin: 0 0 12px 0;
                padding-bottom: 8px;
                border-bottom: 2px solid var(--accent);
                color: var(--dark);
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .config-panel .config-toggle-row {{
                display: flex;
                flex-direction: column;
                margin-bottom: 15px;
                border-bottom: 1px solid var(--accent);
                padding-bottom: 10px;
            }}
            .config-panel .config-toggle-row:last-of-type {{
                border-bottom: none;
                margin-bottom: 0;
                padding-bottom: 0;
            }}
            .agendamento-destaque {{
                animation: destaqueAgendamento 2.5s ease-out;
            }}
            @keyframes destaqueAgendamento {{
                0% {{ box-shadow: inset 0 0 0 3px var(--today-border); background-color: var(--today-border); }}
                100% {{ box-shadow: inset 0 0 0 3px transparent; }}
            }}
            .pin-simple {{
                font-size: 16px;
                letter-spacing: 4px;
                text-align: center;
                background: var(--select-bg);
                border: 1px solid var(--select-border);
                border-radius: 8px;
                padding: 12px;
                width: 100%;
                color: var(--text);
            }}
            /* Centralização da barra lateral direita */
            .right-bar .detail-capa {{
                margin-left: auto;
                margin-right: auto;
            }}
            .right-bar h4, .right-bar p, .right-bar div {{
                text-align: center;
            }}
            .right-bar #det-temas, .right-bar #det-desc {{
                text-align: center;
            }}

            @media (max-width: 1024px) {{
                .app-container {{ grid-template-columns: 240px 1fr 280px; }}
                .sidebar {{ padding: 15px; }}
                .nav-menu li {{ padding: 8px 8px; }}
                .nav-menu li span.shortcut {{ display: none; }}
            }}
            @media (max-width: 768px) {{
                .app-container {{ grid-template-columns: 1fr; height: auto; }}
                .sidebar, .right-bar {{ width: 100%; border: none; border-bottom: 2px dashed var(--accent); }}
                .right-bar {{ border-left: none; border-top: 2px dashed var(--accent); }}
                .sidebar .nav-menu {{ flex-direction: row; flex-wrap: wrap; justify-content: center; }}
                .sidebar .nav-menu li {{ width: auto; }}
                .sidebar-buttons {{ justify-content: center; }}
                .content-area {{ margin: 10px; }}
            }}
        </style>
    </head>
    <body>
        <div class="toast-container" id="toast-container"></div>
        <div class="app-container">
            <aside class="sidebar">
                <div class="logo" onclick="window.location='/'">
                    <img src="/static/images/icon.png" alt="BIBI" onerror="this.style.display='none'">
                    BIBI
                </div>
                <ul class="nav-menu">
                    {nav_dashboard}
                    <li onclick="tab('acervo')" id="m-acervo" class="active">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-journal" viewBox="0 0 16 16">
                            <path d="M3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2v-1h1v1a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1v1H1V2a2 2 0 0 1 2-2"/>
                            <path d="M1 5v-.5a.5.5 0 0 1 1 0V5h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1zm0 3v-.5a.5.5 0 0 1 1 0V8h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1zm0 3v-.5a.5.5 0 0 1 1 0v.5h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1z"/>
                        </svg>
                        <span>Acervo</span>
                        <span class="shortcut">Ctrl+1</span>
                    </li>
                    {nav_emprestimos}
                    <li onclick="tab('age')" id="m-age">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-calendar-check" viewBox="0 0 16 16">
                            <path d="M10.854 7.146a.5.5 0 0 1 0 .708l-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7.5 9.793l2.646-2.647a.5.5 0 0 1 .708 0"/>
                            <path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h1V.5a.5.5 0 0 1 .5-.5M1 4v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4z"/>
                        </svg>
                        <span>Agenda</span>
                        <span class="shortcut">Ctrl+2</span>
                    </li>
                    {nav_leitores}
                </ul>
                <div class="sidebar-buttons">
                    <div class="theme-item" id="theme-toggle-btn" onclick="toggleTheme()" title="Alternar tema">
                        <svg id="theme-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-moon-stars" viewBox="0 0 16 16">
                            <path d="M6 .278a.77.77 0 0 1 .08.858 7.2 7.2 0 0 0-.878 3.46c0 4.021 3.278 7.277 7.318 7.277q.792-.001 1.533-.16a.79.79 0 0 1 .81.316.73.73 0 0 1-.031.893A8.35 8.35 0 0 1 8.344 16C3.734 16 0 12.286 0 7.71 0 4.266 2.114 1.312 5.124.06A.75.75 0 0 1 6 .278M4.858 1.311A7.27 7.27 0 0 0 1.025 7.71c0 4.02 3.279 7.276 7.319 7.276a7.32 7.32 0 0 0 5.205-2.162q-.506.063-1.029.063c-4.61 0-8.343-3.714-8.343-8.29 0-1.167.242-2.278.681-3.286"/>
                            <path d="M10.794 3.148a.217.217 0 0 1 .412 0l.387 1.162c.173.518.579.924 1.097 1.097l1.162.387a.217.217 0 0 1 0 .412l-1.162.387a1.73 1.73 0 0 0-1.097 1.097l-.387 1.162a.217.217 0 0 1-.412 0l-.387-1.162A1.73 1.73 0 0 0 9.31 6.593l-1.162-.387a.217.217 0 0 1 0-.412l1.162-.387a1.73 1.73 0 0 0 1.097-1.097zM13.863.099a.145.145 0 0 1 .274 0l.258.774c.115.346.386.617.732.732l.774.258a.145.145 0 0 1 0 .274l-.774.258a1.16 1.16 0 0 0-.732.732l-.258.774a.145.145 0 0 1-.274 0l-.258-.774a1.16 1.16 0 0 0-.732-.732l-.774-.258a.145.145 0 0 1 0-.274l.774-.258c.346-.115.617-.386.732-.732z"/>
                        </svg>
                    </div>
                    {config_button}
                </div>
                <div class="cat-container">
                    <video autoplay loop muted playsinline class="cat-waving" src="/static/images/catwaving.webm"></video>
                </div>
            </aside>

            <main class="content-area">
                <div id="dash" class="section">
                    <h2>Dashboard - Bibliometria</h2>
                    <div class="dash-grid">
                        <div class="card"><h3>Total Títulos</h3><p id="stat-total">0</p></div>
                        <div class="card"><h3>Exemplares</h3><p id="stat-exemplares">0</p></div>
                        <div class="card green" onclick="tab('emp'); setTimeout(()=>filtrarEmprestimos('ativos'), 100);"><h3>Empréstimos Ativos</h3><p id="stat-emp">0</p></div>
                        <div class="card alert" onclick="tab('emp'); setTimeout(()=>filtrarEmprestimos('atrasados'), 100);"><h3>Atrasos</h3><p id="stat-atraso">0</p></div>
                        <div class="card today" onclick="tab('emp'); setTimeout(()=>filtrarEmprestimos('hoje'), 100);"><h3>Devoluções Hoje</h3><p id="stat-hoje">0</p></div>
                        <div class="card" onclick="tab('age')"><h3>Agenda</h3><p id="stat-agenda">0</p></div>
                        <div class="card" onclick="tab('lei')"><h3>Leitores</h3><p id="stat-leitores">0</p></div>
                    </div>
                    
                    <div class="dashboard-row">
                        <div class="dashboard-panel">
                            <h3>Gêneros em Circulação</h3>
                            <canvas id="grafico-generos" width="200" height="200"></canvas>
                        </div>
                        <div class="dashboard-panel">
                            <h3>Preferência Histórica</h3>
                            <canvas id="grafico-historico" width="200" height="200"></canvas>
                        </div>
                    </div>
                    
                    <div class="dashboard-row">
                        <div class="dashboard-panel">
                            <h3>Leitores Mais Ativos (Trimestre)</h3>
                            <ol class="ranking-list" id="ranking-leitores"></ol>
                        </div>
                        <div class="dashboard-panel">
                            <h3>Livros Mais Emprestados</h3>
                            <div class="top-livros-grid" id="top-livros"></div>
                        </div>
                    </div>
                    
                    <div class="dashboard-panel" style="margin-top:20px;">
                        <h3>Livros Adormecidos (sem empréstimos há 6 meses)</h3>
                        <div id="lista-adormecidos" style="display:flex; flex-wrap:wrap; gap:6px; margin-top:10px;"></div>
                    </div>
                </div>

                <div id="acervo" class="section active">
                    <div class="section-header">
                        <h2>Gerenciar Acervo</h2>
                        {acervo_header_btn}
                    </div>
                    <div class="search-box">
                        <input type="text" id="busca-acervo" placeholder="Buscar por título ou ISBN..." oninput="filtrarAcervo()">
                    </div>
                    <div id="acervo-prateleiras"></div>
                </div>

                <div id="emp" class="section">
                    <h2>Empréstimos</h2>
                    <div style="display:flex; gap:10px; margin-bottom:20px; flex-wrap:wrap;">
                        <button class="btn-primary btn-filtro active-filtro" id="btn-filtro-todos" onclick="filtrarEmprestimos('todos')">Todos</button>
                        <button class="btn-primary btn-filtro green" id="btn-filtro-ativos" onclick="filtrarEmprestimos('ativos')">Ativos</button>
                        <button class="btn-primary btn-filtro" id="btn-filtro-atrasados" onclick="filtrarEmprestimos('atrasados')" style="background:#b33;">Atrasados</button>
                        <button class="btn-primary btn-filtro" id="btn-filtro-hoje" onclick="filtrarEmprestimos('hoje')" style="background:#CD853F;">Devoluções Hoje</button>
                        <button class="btn-primary btn-filtro" id="btn-filtro-devolvidos" onclick="filtrarEmprestimos('devolvidos')" style="background:#666;">Devolvidos</button>
                    </div>
                    <div id="lista-ativos" style="overflow-x: auto;"></div>
                </div>

                <div id="age" class="section">
                    <div class="section-header">
                        <h2>Agenda da Sala</h2>
                    </div>
                    <div class="agenda-container">
                        <div class="agenda-header">
                            <div class="periodo-selector" style="display:flex; flex-wrap:wrap; align-items:center; gap:15px; margin-bottom:8px;">
                                <div style="display:flex; align-items:center; gap:5px;">
                                    <label>Data:</label>
                                    <input type="hidden" id="agenda-data">
                                    <input type="text" id="agenda-data-alt" readonly placeholder="Selecionar Data">
                                </div>
                                <div style="display:flex; align-items:center; gap:5px;">
                                    <label>Período:</label>
                                    <div id="custom-select-periodo-agenda" class="custom-select" style="width:150px;"></div>
                                    <input type="hidden" id="agenda-periodo" value="Manhã">
                                </div>
                            </div>
                        </div>
                        <div class="agenda-tabela">
                            <table id="tabela-agenda"></table>
                        </div>
                        <div class="agendas-laterais">
                            <h4>Próximos Agendamentos</h4>
                            <div id="lista-proximos"></div>
                        </div>
                        <div class="agendas-laterais">
                            <h4>Últimos Agendamentos</h4>
                            <div id="lista-passados"></div>
                        </div>
                    </div>
                </div>

                <div id="lei" class="section">
                    <h2>Leitores Cadastrados</h2>
                    <div class="search-box" style="margin-bottom:20px;">
                        <input type="text" id="busca-leitor" placeholder="Buscar por nome..." oninput="filtrarLeitores()">
                    </div>
                    <div id="lista-leitores" style="margin-top:20px;"></div>
                    <button class="btn-primary" style="margin-top:20px;" onclick="openModal('modalLeitor')">+ Novo Leitor</button>
                </div>
            </main>

            <aside class="right-bar">
                <h3>Informações</h3>
                <div id="info-vazio" style="margin-top:50px; color:var(--light);">Selecione um livro</div>
                <div id="info-livro" style="display:none;">
                    <div class="detail-capa" id="det-capa"></div>
                    <h4 id="det-titulo"></h4>
                    <p id="det-autor" style="font-size:12px; margin-bottom:5px;"></p>
                    <p id="det-ano" style="font-size:11px; color:var(--light); margin-bottom:10px;"></p>
                    <div style="text-align:center; font-size:12px;" id="det-temas"></div>
                    <div style="text-align:center; font-size:11px; color:var(--light); margin-top:10px;" id="det-desc"></div>
                    <p style="margin:10px 0;"><span id="det-estoque"></span> exemplares disponíveis</p>
                    {right_bar_buttons}
                </div>
            </aside>
        </div>

        {modal_add_livro}
        {modal_leitor}
        {modal_emprestimo_rapido}
        {modal_configuracoes}
        {modal_senha_config}
        <div id="modalAtrasos" class="modal">
            <div class="modal-content">
                <h3>Empréstimos em Atraso</h3>
                <div id="lista-atrasos"></div>
                <button class="btn-cancel" style="margin-top:20px;" onclick="closeModal('modalAtrasos')">Fechar</button>
            </div>
        </div>
        <div id="modalDevolucoesHoje" class="modal">
            <div class="modal-content">
                <h3>Devoluções para Hoje</h3>
                <div id="lista-devolucoes-hoje"></div>
                <button class="btn-cancel" style="margin-top:20px;" onclick="closeModal('modalDevolucoesHoje')">Fechar</button>
            </div>
        </div>
        <div id="modalAgendamento" class="modal">
            <div class="modal-content">
                <h3 id="agenda-titulo">Agendar Aula</h3>
                <input type="hidden" id="agenda-id">
                <input type="hidden" id="agenda-dia">
                <input type="hidden" id="agenda-aula">
                <input type="hidden" id="agenda-periodo-modal">
                <input type="hidden" id="agenda-data-modal">
                <div id="agenda-existente" style="display:none;">
                    <p><strong>Professor:</strong> <span id="agenda-prof-view"></span></p>
                    <p><strong>Matéria:</strong> <span id="agenda-mat-view"></span></p>
                    <p><strong>Uso:</strong> <span id="agenda-uso-view" style="margin-bottom:30px; display:block;"></span></p>
                    <button class="btn-cancel" id="btn-excluir-agendamento" style="background:#b33; margin-bottom:10px;" onclick="excluirAgendamentoAtual()">Excluir Agendamento</button>
                    <button class="btn-cancel" style="margin-top:10px;" onclick="closeModal('modalAgendamento')">Fechar</button>
                </div>
                <div id="agenda-form">
                    <label>Professor</label><input type="text" id="agenda-prof" placeholder="Nome do professor">
                    <label>Matéria</label><input type="text" id="agenda-mat" placeholder="Disciplina">
                    <label>Uso da sala</label><textarea id="agenda-uso" rows="2" placeholder="Descreva a atividade..."></textarea>
                    <button class="btn-primary" id="btn-agendar" onclick="salvarAgendamento()">Agendar</button>
                    <button class="btn-cancel" style="margin-top:10px;" onclick="closeModal('modalAgendamento')">Cancelar</button>
                </div>
            </div>
        </div>
        <div id="modalConfirmacao" class="modal">
            <div class="modal-content" style="max-width:400px;">
                <h3 id="confirm-titulo">Confirmar</h3>
                <p id="confirm-mensagem" style="margin:20px 0;">Tem certeza?</p>
                <div style="display:flex; gap:10px; justify-content:center;">
                    <button class="btn-primary" id="confirm-btn-sim" style="width:auto;">Sim</button>
                    <button class="btn-cancel" style="width:auto;" onclick="closeModal('modalConfirmacao')">Cancelar</button>
                </div>
            </div>
        </div>
        <div id="modalDetalhesAgendamento" class="modal">
            <div class="modal-content">
                <h3>Detalhes do Agendamento</h3>
                <p><strong>Professor:</strong> <span id="detalhe-professor"></span></p>
                <p><strong>Matéria:</strong> <span id="detalhe-materia"></span></p>
                <p><strong>Uso da sala:</strong> <span id="detalhe-uso"></span></p>
                <button class="btn-cancel" id="btn-excluir-agendamento-detalhes" style="background:#b33; margin-bottom:10px; display:none;" onclick="excluirAgendamentoDetalhes()">Excluir Agendamento</button>
                <button class="btn-cancel" style="margin-top:10px;" onclick="closeModal('modalDetalhesAgendamento')">Fechar</button>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
        <script src="https://npmcdn.com/flatpickr/dist/l10n/pt.js"></script>
        <script>
            // Funções auxiliares
            let isAdminGlobal = {str(admin).lower()};
            // Quantidade de aulas injetada do backend (valor salvo no banco de dados)
            let quantidadeAulasGlobal = {quantidade_aulas};

            async function verificarAdmin() {{
                // j� temos isAdminGlobal vindo do backend
                // Aplica restrições visuais no frontend
                const adminElements = document.querySelectorAll('.admin-only');
                adminElements.forEach(el => {{
                    if (!isAdminGlobal) el.style.display = 'none';
                    else el.style.display = '';
                }});
                // Se não for admin, remove a aba ativa que não deveria estar visível
                if (!isAdminGlobal) {{
                    const activeTab = document.querySelector('.section.active');
                    if (activeTab && !['acervo', 'age'].includes(activeTab.id)) {{
                        tab('acervo');
                    }}
                }}
            }}

            function showToast(message, type = 'info') {{
                const container = document.getElementById('toast-container');
                const toast = document.createElement('div');
                toast.className = `toast ${{type}}`;
                toast.innerText = message;
                container.appendChild(toast);
                setTimeout(() => toast.remove(), 4000);
            }}

            function openModal(id) {{ document.getElementById(id).style.display='flex'; }}
            function closeModal(id) {{ document.getElementById(id).style.display='none'; }}

            let confirmCallback = null;
            function confirmAction(titulo, mensagem, callback) {{
                document.getElementById('confirm-titulo').innerText = titulo;
                document.getElementById('confirm-mensagem').innerText = mensagem;
                confirmCallback = callback;
                openModal('modalConfirmacao');
            }}
            document.getElementById('confirm-btn-sim').addEventListener('click', () => {{
                if (confirmCallback) confirmCallback();
                closeModal('modalConfirmacao');
                confirmCallback = null;
            }});

            function toggleTheme(ativar) {{
                if (ativar === undefined) ativar = !document.body.classList.contains('dark-mode');
                if (ativar) {{
                    document.body.classList.add('dark-mode');
                    document.getElementById('theme-icon').innerHTML = '<path d="M8 11a3 3 0 1 1 0-6 3 3 0 0 1 0 6m0 1a4 4 0 1 0 0-8 4 4 0 0 0 0 8M8 0a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 0m0 13a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 13m8-5a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2a.5.5 0 0 1 .5.5M3 8a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2A.5.5 0 0 1 3 8m10.657-5.657a.5.5 0 0 1 0 .707l-1.414 1.415a.5.5 0 1 1-.707-.708l1.414-1.414a.5.5 0 0 1 .707 0m-9.193 9.193a.5.5 0 0 1 0 .707L3.05 13.657a.5.5 0 0 1-.707-.707l1.414-1.414a.5.5 0 0 1 .707 0m9.193 2.121a.5.5 0 0 1-.707 0l-1.414-1.414a.5.5 0 0 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .707M4.464 4.465a.5.5 0 0 1-.707 0L2.343 3.05a.5.5 0 1 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .708"/>';
                }} else {{
                    document.body.classList.remove('dark-mode');
                    document.getElementById('theme-icon').innerHTML = '<path d="M6 .278a.77.77 0 0 1 .08.858 7.2 7.2 0 0 0-.878 3.46c0 4.021 3.278 7.277 7.318 7.277q.792-.001 1.533-.16a.79.79 0 0 1 .81.316.73.73 0 0 1-.031.893A8.35 8.35 0 0 1 8.344 16C3.734 16 0 12.286 0 7.71 0 4.266 2.114 1.312 5.124.06A.75.75 0 0 1 6 .278M4.858 1.311A7.27 7.27 0 0 0 1.025 7.71c0 4.02 3.279 7.276 7.319 7.276a7.32 7.32 0 0 0 5.205-2.162q-.506.063-1.029.063c-4.61 0-8.343-3.714-8.343-8.29 0-1.167.242-2.278.681-3.286"/><path d="M10.794 3.148a.217.217 0 0 1 .412 0l.387 1.162c.173.518.579.924 1.097 1.097l1.162.387a.217.217 0 0 1 0 .412l-1.162.387a1.73 1.73 0 0 0-1.097 1.097l-.387 1.162a.217.217 0 0 1-.412 0l-.387-1.162A1.73 1.73 0 0 0 9.31 6.593l-1.162-.387a.217.217 0 0 1 0-.412l1.162-.387a1.73 1.73 0 0 0 1.097-1.097zM13.863.099a.145.145 0 0 1 .274 0l.258.774c.115.346.386.617.732.732l.774.258a.145.145 0 0 1 0 .274l-.774.258a1.16 1.16 0 0 0-.732.732l-.258.774a.145.145 0 0 1-.274 0l-.258-.774a1.16 1.16 0 0 0-.732-.732l-.774-.258a.145.145 0 0 1 0-.274l.774-.258c.346-.115.617-.386.732-.732z"/>';
                }}
                const config = carregarConfig();
                config.darkMode = ativar;
                salvarConfig(config);
                carregarGraficoGeneros();
                carregarGraficoHistorico();
                verificarObrigarLocalizacao();
            }}

            function aplicarMascaraTelefone(input) {{
                let valor = input.value.replace(/\\D/g, '');
                if (valor.length === 0) return;
                let comCodPais = false;
                if (valor.startsWith('55')) {{
                    comCodPais = true;
                    valor = valor.substring(2);
                }}
                let ddd = '';
                let numero = '';
                if (valor.length >= 2) {{
                    ddd = valor.substring(0, 2);
                    numero = valor.substring(2);
                }} else {{
                    ddd = valor;
                }}
                let formatado = '';
                if (comCodPais) formatado = '+55 ';
                if (ddd) formatado += `(${{ddd}}) `;
                if (numero) {{
                    if (numero.length === 9) {{
                        formatado += `${{numero.substring(0,5)}}-${{numero.substring(5)}}`;
                    }} else if (numero.length === 8) {{
                        formatado += `${{numero.substring(0,4)}}-${{numero.substring(4)}}`;
                    }} else {{
                        formatado += numero;
                    }}
                }}
                input.value = formatado;
            }}

            function setupDragAndDrop(previewId, urlId) {{
                const previewDiv = document.getElementById(previewId);
                if (!previewDiv) return;
                previewDiv.addEventListener('dragover', (e) => {{
                    e.preventDefault();
                    previewDiv.style.opacity = '0.7';
                }});
                previewDiv.addEventListener('dragleave', (e) => {{
                    e.preventDefault();
                    previewDiv.style.opacity = '1';
                }});
                previewDiv.addEventListener('drop', async (e) => {{
                    e.preventDefault();
                    previewDiv.style.opacity = '1';
                    const file = e.dataTransfer.files[0];
                    if (file && file.type.startsWith('image/')) {{
                        await uploadImageFile(file, previewId, urlId);
                    }} else {{
                        showToast("Arraste apenas imagens", "warning");
                    }}
                }});
            }}

            const CONFIG_STORAGE_KEY = 'bibiConfig';
            function carregarConfig() {{
                const str = localStorage.getItem(CONFIG_STORAGE_KEY);
                if (str) {{
                    try {{ return JSON.parse(str); }} catch(e) {{}}
                }}
                return {{
                    darkMode: false,
                    mostrarColunaAula: true,
                    campoDescricaoVisivel: true,
                    campoTemasVisivel: true,
                    campoAnoVisivel: true,
                    campoCategoriaVisivel: true,
                    campoNumeroUsuario: false,
                    bloquearExcluirLivro: false
                }};
            }}
            function salvarConfig(config) {{
                localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(config));
            }}

            class CustomSelect {{
                constructor(container, options, onChange, defaultValue = null) {{
                    this.container = container;
                    this.options = options;
                    this.onChange = onChange;
                    this.selectedValue = defaultValue || (options.length > 0 ? options[0].value : '');
                    this.render();
                }}
                render() {{
                    this.container.innerHTML = '';
                    this.container.className = 'custom-select';
                    const selectedDiv = document.createElement('div');
                    selectedDiv.className = 'select-selected';
                    const selectedOption = this.options.find(opt => opt.value == this.selectedValue) || this.options[0];
                    selectedDiv.innerHTML = `<span>${{selectedOption ? selectedOption.text : ''}}</span>`;
                    this.container.appendChild(selectedDiv);
                    
                    const itemsDiv = document.createElement('div');
                    itemsDiv.className = 'select-items';
                    this.options.forEach(opt => {{
                        const optDiv = document.createElement('div');
                        optDiv.textContent = opt.text;
                        if (opt.value == this.selectedValue) {{
                            optDiv.classList.add('same-as-selected');
                        }}
                        optDiv.addEventListener('click', () => {{
                            this.setValue(opt.value);
                            this.close();
                        }});
                        itemsDiv.appendChild(optDiv);
                    }});
                    this.container.appendChild(itemsDiv);
                    
                    selectedDiv.addEventListener('click', (e) => {{
                        e.stopPropagation();
                        this.toggle();
                    }});
                    document.addEventListener('click', () => this.close());
                }}
                toggle() {{
                    const items = this.container.querySelector('.select-items');
                    items.style.display = items.style.display === 'block' ? 'none' : 'block';
                }}
                close() {{
                    const items = this.container.querySelector('.select-items');
                    if (items) items.style.display = 'none';
                }}
                setValue(value) {{
                    this.selectedValue = value;
                    const selectedOption = this.options.find(opt => opt.value == value);
                    this.container.querySelector('.select-selected span').textContent = selectedOption ? selectedOption.text : '';
                    this.container.querySelectorAll('.select-items div').forEach(div => {{
                        div.classList.remove('same-as-selected');
                        if (div.textContent === (selectedOption ? selectedOption.text : '')) {{
                            div.classList.add('same-as-selected');
                        }}
                    }});
                    if (this.onChange) this.onChange(value);
                }}
                getValue() {{
                    return this.selectedValue;
                }}
            }}

            async function uploadImageFile(file, previewId, urlId) {{
                const formData = new FormData();
                formData.append('file', file);
                const res = await fetch('/api/upload', {{method: 'POST', body: formData}});
                if (res.ok) {{
                    const data = await res.json();
                    document.getElementById(urlId).value = data.url;
                    const previewDiv = document.getElementById(previewId);
                    previewDiv.style.backgroundImage = `url(${{data.url}})`;
                    previewDiv.classList.add('has-image');
                    const textSpan = previewDiv.querySelector('.preview-text');
                    if (textSpan) textSpan.style.display = 'none';
                }} else {{
                    showToast("Erro no upload da capa", "error");
                }}
            }}

            async function handleClipboardPaste(e) {{
                const items = e.clipboardData ? e.clipboardData.items : (e.originalEvent && e.originalEvent.clipboardData ? e.originalEvent.clipboardData.items : []);
                if (!items) return;
                for (let item of items) {{
                    if (item.type.indexOf('image') !== -1) {{
                        const blob = item.getAsFile();
                        if (!blob) continue;
                        let previewId, urlId;
                        const manualModal = document.getElementById('modalManualLivro');
                        const editModal = document.getElementById('modalEditarLivro');
                        if (manualModal && manualModal.style.display === 'flex') {{
                            previewId = 'manual-capa-preview';
                            urlId = 'manual-capa-url';
                        }} else if (editModal && editModal.style.display === 'flex') {{
                            previewId = 'edit-capa-preview';
                            urlId = 'edit-capa-url';
                        }} else {{
                            continue;
                        }}
                        e.preventDefault();
                        await uploadImageFile(blob, previewId, urlId);
                        break;
                    }}
                }}
            }}
            document.addEventListener('paste', handleClipboardPaste);

            function previewCapaManual(event) {{
                const file = event.target.files[0];
                if (file) {{
                    const reader = new FileReader();
                    reader.onload = (e) => {{
                        const previewDiv = document.getElementById('manual-capa-preview');
                        previewDiv.style.backgroundImage = `url(${{e.target.result}})`;
                        previewDiv.classList.add('has-image');
                        const textSpan = previewDiv.querySelector('.preview-text');
                        if (textSpan) textSpan.style.display = 'none';
                    }};
                    reader.readAsDataURL(file);
                    uploadCapa(file, 'manual-capa-url');
                }}
            }}
            function previewCapaEdit(event) {{
                const file = event.target.files[0];
                if (file) {{
                    const reader = new FileReader();
                    reader.onload = (e) => {{
                        const previewDiv = document.getElementById('edit-capa-preview');
                        previewDiv.style.backgroundImage = `url(${{e.target.result}})`;
                        previewDiv.classList.add('has-image');
                        const textSpan = previewDiv.querySelector('.preview-text');
                        if (textSpan) textSpan.style.display = 'none';
                    }};
                    reader.readAsDataURL(file);
                    uploadCapa(file, 'edit-capa-url');
                }}
            }}
            async function uploadCapa(file, targetInputId) {{
                const formData = new FormData();
                formData.append('file', file);
                const res = await fetch('/api/upload', {{method: 'POST', body: formData}});
                if (res.ok) {{
                    const data = await res.json();
                    document.getElementById(targetInputId).value = data.url;
                }} else {{
                    showToast("Erro no upload da capa", "error");
                }}
            }}

            let periodoAgendaSelect;
            let categoriaManualSelect, categoriaEditSelect, tipoLeitorModalSelect;
            let tipoRapidoSelect, prazoRapidoSelect, periodoRapidoSelect;
            
            function initCustomSelects() {{
                const periodoAgendaContainer = document.getElementById('custom-select-periodo-agenda');
                if (periodoAgendaContainer) {{
                    periodoAgendaSelect = new CustomSelect(periodoAgendaContainer, [
                        {{value: 'Manhã', text: 'Manhã'}},
                        {{value: 'Tarde', text: 'Tarde'}},
                        {{value: 'Noite', text: 'Noite'}}
                    ], (val) => {{
                        document.getElementById('agenda-periodo').value = val;
                        periodoAtual = val;
                        carregarAgenda();
                    }}, 'Manhã');
                }}
                const catManualContainer = document.getElementById('custom-select-categoria-manual');
                if (catManualContainer) {{
                    categoriaManualSelect = new CustomSelect(catManualContainer, [
                        {{value: 'Ficção', text: 'Ficção'}},
                        {{value: 'Não-ficção', text: 'Não-ficção'}},
                        {{value: 'Poesia', text: 'Poesia'}},
                        {{value: 'Quadrinhos', text: 'Quadrinhos'}}
                    ], (val) => {{
                        document.getElementById('manual-categoria').value = val;
                    }}, 'Ficção');
                }}
                const catEditContainer = document.getElementById('custom-select-categoria-edit');
                if (catEditContainer) {{
                    categoriaEditSelect = new CustomSelect(catEditContainer, [
                        {{value: 'Ficção', text: 'Ficção'}},
                        {{value: 'Não-ficção', text: 'Não-ficção'}},
                        {{value: 'Poesia', text: 'Poesia'}},
                        {{value: 'Quadrinhos', text: 'Quadrinhos'}}
                    ], (val) => {{
                        document.getElementById('edit-categoria').value = val;
                    }}, 'Ficção');
                }}
                const tipoLeitorModalContainer = document.getElementById('custom-select-tipo-leitor');
                if (tipoLeitorModalContainer) {{
                    tipoLeitorModalSelect = new CustomSelect(tipoLeitorModalContainer, [
                        {{value: 'estudante', text: 'Estudante'}},
                        {{value: 'professor', text: 'Professor'}}
                    ], (val) => {{
                        document.getElementById('leitor-tipo').value = val;
                        toggleLeitorTipo();
                    }}, 'estudante');
                }}
                const tipoRapidoContainer = document.getElementById('custom-select-tipo-rapido');
                if (tipoRapidoContainer) {{
                    tipoRapidoSelect = new CustomSelect(tipoRapidoContainer, [
                        {{value: 'estudante', text: 'Estudante'}},
                        {{value: 'professor', text: 'Professor'}}
                    ], (val) => {{
                        document.getElementById('rapido-tipo').value = val;
                        document.getElementById('rapido-aluno').style.display = val === 'estudante' ? 'block' : 'none';
                        document.getElementById('rapido-professor').style.display = val === 'professor' ? 'block' : 'none';
                        aplicarVisibilidadeCamposEmprestimo();
                    }}, 'estudante');
                }}
                const prazoRapidoContainer = document.getElementById('custom-select-prazo-rapido');
                if (prazoRapidoContainer) {{
                    prazoRapidoSelect = new CustomSelect(prazoRapidoContainer, [
                        {{value: '7', text: '7 dias'}},
                        {{value: '14', text: '14 dias'}},
                        {{value: '21', text: '21 dias'}},
                        {{value: '28', text: '28 dias'}}
                    ], (val) => {{
                        document.getElementById('rapido-prazo').value = val;
                    }}, '7');
                }}
                const periodoRapidoContainer = document.getElementById('custom-select-periodo-rapido');
                if (periodoRapidoContainer) {{
                    periodoRapidoSelect = new CustomSelect(periodoRapidoContainer, [
                        {{value: 'Manhã', text: 'Manhã'}},
                        {{value: 'Tarde', text: 'Tarde'}},
                        {{value: 'Noite', text: 'Noite'}}
                    ], (val) => {{
                        document.getElementById('rapido-periodo').value = val;
                    }}, 'Manhã');
                }}
            }}

            function getOpenModalId() {{
                const modals = ['modalAddLivro', 'modalManualLivro', 'modalEditarLivro', 'modalAgendamento',
                               'modalLeitor', 'modalEmprestimoRapido', 'modalConfigAgenda', 'modalConfirmacao',
                               'modalAtrasos', 'modalDevolucoesHoje', 'modalSenhaConfig', 'modalConfiguracoes', 'modalDetalhesAgendamento'];
                for (const id of modals) {{
                    const el = document.getElementById(id);
                    if (el && el.style.display === 'flex') return id;
                }}
                return null;
            }}

            function triggerModalAction(modalId) {{
                switch (modalId) {{
                    case 'modalAddLivro': document.getElementById('btn-buscar-salvar').click(); break;
                    case 'modalManualLivro': document.getElementById('btn-salvar-manual').click(); break;
                    case 'modalEditarLivro': document.getElementById('btn-salvar-edicao').click(); break;
                    case 'modalAgendamento':
                        if (document.getElementById('agenda-form').style.display !== 'none') document.getElementById('btn-agendar').click();
                        break;
                    case 'modalLeitor': document.getElementById('btn-salvar-leitor').click(); break;
                    case 'modalEmprestimoRapido': document.getElementById('btn-confirmar-emprestimo').click(); break;
                    case 'modalConfigAgenda': document.getElementById('btn-salvar-config').click(); break;
                    case 'modalConfirmacao': document.getElementById('confirm-btn-sim').click(); break;
                    case 'modalSenhaConfig': document.getElementById('btn-senha').click(); break;
                    case 'modalConfiguracoes': salvarConfigGerais(); break;
                    default: break;
                }}
            }}

            document.addEventListener('keydown', (e) => {{
                if (e.ctrlKey && e.key >= '1' && e.key <= '5') {{
                    e.preventDefault();
                    if (!isAdminGlobal) {{
                        // Apenas Ctrl+1 (acervo) e Ctrl+2 (agenda) são permitidos
                        if (e.key === '1') {{
                            tab('acervo');
                        }} else if (e.key === '2') {{
                            tab('age');
                        }}
                        return;
                    }}
                    const tabs = ['dash', 'acervo', 'emp', 'age', 'lei'];
                    tab(tabs[parseInt(e.key) - 1]);
                }}
                if (e.key === 'Enter' && !e.ctrlKey && !e.altKey && !e.metaKey) {{
                    const openModalId = getOpenModalId();
                    if (openModalId) {{
                        e.preventDefault();
                        e.stopPropagation();
                        triggerModalAction(openModalId);
                    }}
                }}
            }});

            async function carregarConfigAgenda() {{
                // Para administradores, buscamos a configuração atualizada via API.
                // Para não administradores, usamos o valor injetado globalmente.
                if (isAdminGlobal) {{
                    try {{
                        const res = await fetch('/api/config/quantidade_aulas/status');
                        const data = await res.json();
                        document.getElementById('cfg-qtd-aulas').value = data.quantidade;
                        configAgenda.aulas = data.quantidade;
                    }} catch(e) {{
                        console.error("Erro ao carregar quantidade de aulas:", e);
                        document.getElementById('cfg-qtd-aulas').value = 6;
                        configAgenda.aulas = 6;
                    }}
                }} else {{
                    configAgenda.aulas = quantidadeAulasGlobal;
                }}
            }}
            async function salvarConfigAgenda() {{
                if (!isAdminGlobal) return;
                const qtd = parseInt(document.getElementById('cfg-qtd-aulas').value);
                const res = await fetch('/api/config/quantidade_aulas/set', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{quantidade: qtd}})
                }});
                if (res.ok) {{
                    configAgenda.aulas = qtd;
                    showToast("Configurações salvas!", "success");
                    closeModal('modalConfigAgenda');
                    carregarAgenda();
                }} else {{
                    showToast("Erro ao salvar quantidade de aulas.", "error");
                }}
            }}

            function tab(id) {{
                document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
                document.querySelectorAll('.nav-menu li').forEach(l => l.classList.remove('active'));
                document.getElementById(id).classList.add('active');
                document.getElementById('m-'+id).classList.add('active');
                if(id === 'acervo') carregarAcervo();
                if(id === 'dash' && isAdminGlobal) carregarDashboard();
                if(id === 'lei' && isAdminGlobal) carregarLeitores();
                if(id === 'age') {{
                    const hiddenInput = document.getElementById('agenda-data');
                    if (!hiddenInput.value && flatpickrInstance) {{
                        const today = new Date();
                        flatpickrInstance.setDate(today);
                    }}
                    carregarAgenda();
                }}
                if(id === 'emp' && isAdminGlobal) {{
                    if (filtroEmprestimosAtual) {{
                        filtrarEmprestimos(filtroEmprestimosAtual);
                    }} else {{
                        carregarEmprestimosAtivos();
                    }}
                }}
            }}

            function openModalManual() {{
                closeModal('modalAddLivro');
                aplicarVisibilidadeCamposLivro(true);
                const previewDiv = document.getElementById('manual-capa-preview');
                previewDiv.style.backgroundImage = '';
                previewDiv.classList.remove('has-image');
                const textSpan = previewDiv.querySelector('.preview-text');
                if (textSpan) textSpan.style.display = 'flex';
                openModal('modalManualLivro');
            }}

            async function carregarAcervo() {{
                const res = await fetch('/api/livros');
                todosLivros = await res.json();
                aplicarFiltroAcervo();
            }}

            function aplicarFiltroAcervo() {{
                const termo = document.getElementById('busca-acervo').value.toLowerCase();
                const filtrados = todosLivros.filter(l => 
                    l.titulo.toLowerCase().includes(termo) || (l.isbn && l.isbn.includes(termo))
                );
                exibirPrateleiras(filtrados);
            }}

            function filtrarAcervo() {{
                aplicarFiltroAcervo();
            }}

            function exibirPrateleiras(livros) {{
                const container = document.getElementById('acervo-prateleiras');
                container.innerHTML = '';
                const categorias = ['Ficção', 'Não-ficção', 'Poesia', 'Quadrinhos'];
                categorias.forEach(cat => {{
                    const livrosCat = livros.filter(l => l.categoria === cat);
                    const shelfDiv = document.createElement('div');
                    shelfDiv.className = 'shelf';
                    shelfDiv.innerHTML = `<h3>${{cat}}</h3><div class="books-grid" id="grid-${{cat.replace(/\\s/g,'')}}"></div><div class="shelf-base"></div>`;
                    container.appendChild(shelfDiv);
                    const grid = shelfDiv.querySelector('.books-grid');
                    if (livrosCat.length > 0) {{
                        livrosCat.forEach(l => {{
                            const div = document.createElement('div');
                            div.className = 'book';
                            div.style.backgroundImage = `url(${{l.capa}})`;
                            div.onclick = () => verDetalhes(l);
                            grid.appendChild(div);
                        }});
                    }} else {{
                        const emptyMsg = document.createElement('p');
                        emptyMsg.style.color = 'var(--light)';
                        emptyMsg.style.fontStyle = 'italic';
                        emptyMsg.innerText = 'Nenhum livro nesta prateleira.';
                        grid.appendChild(emptyMsg);
                    }}
                }});
            }}

            function verDetalhes(l) {{
                livroSelecionado = l;
                document.getElementById('info-vazio').style.display = 'none';
                document.getElementById('info-livro').style.display = 'block';
                document.getElementById('det-capa').style.backgroundImage = `url(${{l.capa}})`;
                document.getElementById('det-titulo').innerText = l.titulo;
                document.getElementById('det-autor').innerText = l.autor || 'Autor desconhecido';
                document.getElementById('det-ano').innerText = l.ano ? `Ano: ${{l.ano}}` : '';
                document.getElementById('det-temas').innerHTML = `<strong>Temas:</strong> ${{l.temas || 'Não informado'}}`;
                document.getElementById('det-desc').innerText = (l.descricao || 'Sem descrição.').substring(0, 250) + (l.descricao && l.descricao.length > 250 ? '...' : '');
                document.getElementById('det-estoque').innerText = l.disponivel;

                const btnEmprestar = document.getElementById('btn-emprestar');
                if (btnEmprestar) {{
                    if (l.disponivel <= 0) {{
                        btnEmprestar.disabled = true;
                        btnEmprestar.title = "Não há exemplares disponíveis";
                    }} else {{
                        btnEmprestar.disabled = false;
                        btnEmprestar.title = "";
                    }}
                }}

                const config = carregarConfig();
                const btnExcluir = document.getElementById('btn-excluir-livro');
                if (btnExcluir) {{
                    btnExcluir.style.display = config.bloquearExcluirLivro ? 'none' : 'block';
                }}
            }}

            async function salvarLivro() {{
                if (!isAdminGlobal) return;
                const isbn = document.getElementById('add-isbn').value;
                const qtd = document.getElementById('add-qtd').value;
                if(!isbn || !qtd) return showToast("Preencha todos os campos", "warning");
                const btn = document.getElementById('btn-buscar-salvar');
                const originalHTML = btn.innerHTML;
                btn.disabled = true;
                btn.innerHTML = '<span class="pulsing-dots"><span></span><span></span><span></span></span>';
                try {{
                    const res = await fetch('/api/livros', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{isbn, quantidade: qtd}})
                    }});
                    if(res.ok) {{
                        showToast("Livro adicionado!", "success");
                        document.getElementById('add-isbn').value = '';
                        document.getElementById('add-qtd').value = '';
                        closeModal('modalAddLivro');
                        carregarAcervo();
                        if (isAdminGlobal) carregarDashboard();
                    }} else {{
                        const err = await res.json();
                        showToast("Erro: " + err.erro, "error");
                        document.getElementById('add-isbn').value = '';
                        document.getElementById('add-qtd').value = '';
                        closeModal('modalAddLivro');
                    }}
                }} finally {{
                    btn.disabled = false;
                    btn.innerHTML = originalHTML;
                }}
            }}

            async function salvarLivroManual() {{
                if (!isAdminGlobal) return;
                const titulo = document.getElementById('manual-titulo').value;
                const autor = document.getElementById('manual-autor').value;
                const qtd = document.getElementById('manual-qtd').value;
                if(!titulo || !autor || !qtd) return showToast("Preencha título, autor e quantidade.", "warning");
                
                let capaUrl = document.getElementById('manual-capa-url').value;
                if (!capaUrl) capaUrl = '/static/images/placeholder.png';
                
                const localizacao = document.getElementById('manual-localizacao') ? document.getElementById('manual-localizacao').value : '';
                const payload = {{
                    manual: true,
                    isbn: document.getElementById('manual-isbn').value || null,
                    titulo: titulo,
                    autor: autor,
                    ano: document.getElementById('manual-ano').value || null,
                    descricao: document.getElementById('manual-descricao').value,
                    temas: document.getElementById('manual-temas').value,
                    categoria: document.getElementById('manual-categoria').value,
                    quantidade: parseInt(qtd),
                    capa: capaUrl,
                    localizacao: localizacao
                }};
                
                const res = await fetch('/api/livros', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(payload)
                }});
                if(res.ok) {{
                    showToast("Livro adicionado manualmente!", "success");
                    document.getElementById('manual-isbn').value = '';
                    document.getElementById('manual-titulo').value = '';
                    document.getElementById('manual-autor').value = '';
                    document.getElementById('manual-ano').value = '';
                    document.getElementById('manual-descricao').value = '';
                    document.getElementById('manual-temas').value = '';
                    document.getElementById('manual-qtd').value = '1';
                    document.getElementById('manual-capa-url').value = '';
                    const previewDiv = document.getElementById('manual-capa-preview');
                    previewDiv.style.backgroundImage = '';
                    previewDiv.classList.remove('has-image');
                    const textSpan = previewDiv.querySelector('.preview-text');
                    if (textSpan) textSpan.style.display = 'flex';
                    document.getElementById('manual-capa-file').value = '';
                    categoriaManualSelect.setValue('Ficção');
                    closeModal('modalManualLivro');
                    carregarAcervo();
                    if (isAdminGlobal) carregarDashboard();
                }} else {{
                    const err = await res.json();
                    showToast("Erro: " + err.erro, "error");
                }}
            }}

            function editarLivroSelecionado() {{
                if (!isAdminGlobal) return;
                if(!livroSelecionado) return;
                document.getElementById('edit-id').value = livroSelecionado.id;
                document.getElementById('edit-titulo').value = livroSelecionado.titulo;
                document.getElementById('edit-autor').value = livroSelecionado.autor;
                document.getElementById('edit-ano').value = livroSelecionado.ano || '';
                document.getElementById('edit-descricao').value = livroSelecionado.descricao || '';
                document.getElementById('edit-temas').value = livroSelecionado.temas || '';
                document.getElementById('edit-categoria').value = livroSelecionado.categoria || 'Ficção';
                categoriaEditSelect.setValue(livroSelecionado.categoria || 'Ficção');
                document.getElementById('edit-estoque').value = livroSelecionado.estoque;
                document.getElementById('edit-disponivel').value = livroSelecionado.disponivel;
                if (document.getElementById('edit-localizacao')) {{
                    document.getElementById('edit-localizacao').value = livroSelecionado.localizacao || '';
                }}
                const previewDiv = document.getElementById('edit-capa-preview');
                previewDiv.style.backgroundImage = `url(${{livroSelecionado.capa}})`;
                if (livroSelecionado.capa && livroSelecionado.capa !== '/static/images/placeholder.png') {{
                    previewDiv.classList.add('has-image');
                    const textSpan = previewDiv.querySelector('.preview-text');
                    if (textSpan) textSpan.style.display = 'none';
                }} else {{
                    previewDiv.classList.remove('has-image');
                    const textSpan = previewDiv.querySelector('.preview-text');
                    if (textSpan) textSpan.style.display = 'flex';
                }}
                document.getElementById('edit-capa-url').value = '';
                aplicarVisibilidadeCamposLivro(false);
                verificarObrigarLocalizacao();
                openModal('modalEditarLivro');
            }}

            function aplicarVisibilidadeCamposLivro(isManual) {{
                const config = carregarConfig();
                const prefixo = isManual ? 'manual' : 'edit';
                document.querySelector(`#modal${{isManual ? 'ManualLivro' : 'EditarLivro'}} .campo-ano`).style.display = config.campoAnoVisivel ? '' : 'none';
                document.querySelector(`#modal${{isManual ? 'ManualLivro' : 'EditarLivro'}} .campo-descricao`).style.display = config.campoDescricaoVisivel ? '' : 'none';
                document.querySelector(`#modal${{isManual ? 'ManualLivro' : 'EditarLivro'}} .campo-temas`).style.display = config.campoTemasVisivel ? '' : 'none';
                document.querySelector(`#modal${{isManual ? 'ManualLivro' : 'EditarLivro'}} .campo-categoria`).style.display = config.campoCategoriaVisivel ? '' : 'none';
            }}

            async function verificarObrigarLocalizacao() {{
                const res = await fetch('/api/config/obrigar_localizacao_livro/status');
                const data = await res.json();
                const obrigar = data.ativo;
                const manualField = document.getElementById('campo-localizacao-manual');
                const editField = document.getElementById('campo-localizacao-edit');
                if (manualField) manualField.style.display = obrigar ? 'block' : 'none';
                if (editField) editField.style.display = obrigar ? 'block' : 'none';
                if (obrigar) {{
                    if (manualField) manualField.querySelector('label').innerHTML = 'Localização (Prateleira) *';
                    if (editField) editField.querySelector('label').innerHTML = 'Localização (Prateleira)';
                }} else {{
                    if (manualField) manualField.querySelector('label').innerHTML = 'Localização (Prateleira)';
                }}
            }}

            async function salvarEdicaoLivro() {{
                if (!isAdminGlobal) return;
                const id = document.getElementById('edit-id').value;
                const payload = {{
                    titulo: document.getElementById('edit-titulo').value,
                    autor: document.getElementById('edit-autor').value,
                    ano: document.getElementById('edit-ano').value,
                    descricao: document.getElementById('edit-descricao').value,
                    temas: document.getElementById('edit-temas').value,
                    categoria: document.getElementById('edit-categoria').value,
                    estoque: parseInt(document.getElementById('edit-estoque').value),
                    disponivel: parseInt(document.getElementById('edit-disponivel').value),
                    localizacao: document.getElementById('edit-localizacao') ? document.getElementById('edit-localizacao').value : ''
                }};
                const novaCapa = document.getElementById('edit-capa-url').value;
                if (novaCapa) payload.capa = novaCapa;
                
                const res = await fetch(`/api/livros/${{id}}`, {{
                    method: 'PUT',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(payload)
                }});
                if(res.ok) {{
                    showToast("Livro atualizado!", "success");
                    closeModal('modalEditarLivro');
                    carregarAcervo();
                    if(livroSelecionado && livroSelecionado.id == id) {{
                        livroSelecionado = {{...livroSelecionado, ...payload}};
                        verDetalhes(livroSelecionado);
                    }}
                }} else {{
                    showToast("Erro ao atualizar", "error");
                }}
            }}

            function confirmarExclusaoLivro() {{
                if (!isAdminGlobal) return;
                if(!livroSelecionado) return;
                confirmAction("Excluir Livro", `Deseja realmente excluir "${{livroSelecionado.titulo}}"?`, async () => {{
                    await fetch(`/api/livros/${{livroSelecionado.id}}`, {{method: 'DELETE'}});
                    showToast("Livro excluído.", "success");
                    livroSelecionado = null;
                    document.getElementById('info-livro').style.display = 'none';
                    document.getElementById('info-vazio').style.display = 'block';
                    carregarAcervo();
                    if (isAdminGlobal) carregarDashboard();
                }});
            }}

            async function verificarExigirSenhaEmprestimo() {{
                const res = await fetch('/api/config/exigir_senha_emprestimo/status');
                const data = await res.json();
                if (!data.ativo) return null;
                
                return new Promise((resolve) => {{
                    const modal = document.getElementById('modalSenhaConfig');
                    document.getElementById('senha-titulo').innerText = 'Senha de Administrador';
                    document.getElementById('senha-mensagem').innerHTML = 'Digite a senha para realizar o empréstimo:';
                    document.getElementById('senha-confirm').style.display = 'none';
                    document.getElementById('senha-input').value = '';
                    const btnOk = document.getElementById('btn-senha');
                    const originalOnclick = btnOk.onclick;
                    btnOk.onclick = async () => {{
                        const senha = document.getElementById('senha-input').value;
                        const resCheck = await fetch('/api/config/senha/verificar', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{senha}})
                        }});
                        const dataCheck = await resCheck.json();
                        if (dataCheck.valido) {{
                            closeModal('modalSenhaConfig');
                            resolve(senha);
                        }} else {{
                            showToast("Senha incorreta", "error");
                            resolve(null);
                        }}
                        btnOk.onclick = originalOnclick;
                    }};
                    openModal('modalSenhaConfig');
                }});
            }}

            function emprestarSelecionado() {{
                if (!isAdminGlobal) return;
                if(!livroSelecionado) return;
                if(livroSelecionado.disponivel <= 0) {{
                    showToast("Não há exemplares disponíveis para este livro no momento.", "warning");
                    return;
                }}
                verificarExigirSenhaEmprestimo().then(senha => {{
                    if (senha === null && (document.getElementById('modalSenhaConfig').style.display === 'flex')) return;
                    window.senhaEmprestimoGlobal = senha;
                    document.getElementById('emprestimo-rapido-livro-id').value = livroSelecionado.id;
                    document.getElementById('rapido-nome').value = '';
                    document.getElementById('rapido-sala').value = '';
                    document.getElementById('rapido-periodo').value = 'Manhã';
                    periodoRapidoSelect.setValue('Manhã');
                    document.getElementById('rapido-email').value = '';
                    document.getElementById('rapido-nome-prof').value = '';
                    document.getElementById('rapido-materia').value = '';
                    document.getElementById('rapido-telefone').value = '';
                    tipoRapidoSelect.setValue('estudante');
                    prazoRapidoSelect.setValue('7');
                    document.getElementById('rapido-aluno').style.display = 'block';
                    document.getElementById('rapido-professor').style.display = 'none';
                    document.getElementById('rapido-nome-suggestions').style.display = 'none';
                    aplicarVisibilidadeCamposEmprestimo();
                    openModal('modalEmprestimoRapido');
                }});
            }}

            async function buscarLeitoresAutocomplete() {{
                const termo = document.getElementById('rapido-nome').value.trim();
                const suggestionsDiv = document.getElementById('rapido-nome-suggestions');
                if (termo.length < 2) {{
                    suggestionsDiv.style.display = 'none';
                    return;
                }}
                const res = await fetch(`/api/leitores/buscar?q=${{encodeURIComponent(termo)}}`);
                const leitores = await res.json();
                if (leitores.length === 0) {{
                    suggestionsDiv.style.display = 'none';
                    return;
                }}
                suggestionsDiv.innerHTML = '';
                leitores.forEach(leitor => {{
                    const div = document.createElement('div');
                    div.textContent = `${{leitor.nome}} (${{leitor.tipo === 'estudante' ? leitor.sala : leitor.materia}})`;
                    div.addEventListener('click', () => {{
                        document.getElementById('rapido-nome').value = leitor.nome;
                        if (leitor.tipo === 'estudante') {{
                            document.getElementById('rapido-tipo').value = 'estudante';
                            tipoRapidoSelect.setValue('estudante');
                            document.getElementById('rapido-aluno').style.display = 'block';
                            document.getElementById('rapido-professor').style.display = 'none';
                            document.getElementById('rapido-sala').value = leitor.sala || '';
                            document.getElementById('rapido-email').value = leitor.email || '';
                            document.getElementById('rapido-periodo').value = leitor.periodo || 'Manhã';
                            periodoRapidoSelect.setValue(leitor.periodo || 'Manhã');
                            document.getElementById('rapido-telefone').value = leitor.telefone || '';
                        }} else {{
                            document.getElementById('rapido-tipo').value = 'professor';
                            tipoRapidoSelect.setValue('professor');
                            document.getElementById('rapido-aluno').style.display = 'none';
                            document.getElementById('rapido-professor').style.display = 'block';
                            document.getElementById('rapido-nome-prof').value = leitor.nome;
                            document.getElementById('rapido-materia').value = leitor.materia || '';
                        }}
                        suggestionsDiv.style.display = 'none';
                    }});
                    suggestionsDiv.appendChild(div);
                }});
                suggestionsDiv.style.display = 'block';
            }}

            document.addEventListener('click', (e) => {{
                const suggestionsDiv = document.getElementById('rapido-nome-suggestions');
                if (suggestionsDiv && !suggestionsDiv.contains(e.target) && e.target.id !== 'rapido-nome') {{
                    suggestionsDiv.style.display = 'none';
                }}
            }});

            function formatarSala() {{
                const input = document.getElementById('rapido-sala');
                let valor = input.value.trim();
                if (!valor) return;
                const matchNumero = valor.match(/^(\\d+)\\s*$/);
                if (matchNumero) {{
                    input.value = matchNumero[1] + '° ano';
                    return;
                }}
                const matchNumeroTexto = valor.match(/^(\\d+)\\s+(.+)$/);
                if (matchNumeroTexto) {{
                    input.value = matchNumeroTexto[1] + '° ' + matchNumeroTexto[2];
                }}
            }}

            async function confirmarEmprestimoRapido() {{
                if (!isAdminGlobal) return;
                const tipo = document.getElementById('rapido-tipo').value;
                const livroId = parseInt(document.getElementById('emprestimo-rapido-livro-id').value);
                let payload = {{tipo, livros: [{{id: livroId, quantidade: 1}}]}};
                
                if (tipo === 'estudante') {{
                    payload.nome = document.getElementById('rapido-nome').value;
                    payload.sala = document.getElementById('rapido-sala').value;
                    payload.periodo = document.getElementById('rapido-periodo').value;
                    payload.email = document.getElementById('rapido-email').value;
                    payload.prazo = document.getElementById('rapido-prazo').value;
                    const telefone = document.getElementById('rapido-telefone').value;
                    if (telefone) payload.telefone = telefone;
                    if (!payload.nome || !payload.sala || !payload.periodo || !payload.email) {{
                        return showToast("Preencha todos os campos do estudante.", "warning");
                    }}
                    const config = carregarConfig();
                    if (config.campoNumeroUsuario && !payload.telefone) {{
                        return showToast("Telefone do aluno é obrigatório conforme configuração.", "warning");
                    }}
                }} else {{
                    payload.nome = document.getElementById('rapido-nome-prof').value;
                    payload.materia = document.getElementById('rapido-materia').value;
                    if (!payload.nome || !payload.materia) {{
                        return showToast("Preencha nome e matéria do professor.", "warning");
                    }}
                    payload.prazo = 0;
                }}

                if (window.senhaEmprestimoGlobal) {{
                    payload.senha = window.senhaEmprestimoGlobal;
                    window.senhaEmprestimoGlobal = null;
                }}

                const res = await fetch('/api/emprestimos', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(payload)
                }});
                if (res.ok) {{
                    const data = await res.json();
                    showToast("Empréstimo realizado!", "success");
                    if (data.email_enviado) {{
                        showToast("E-mail de confirmação enviado com sucesso.", "success");
                    }}
                    closeModal('modalEmprestimoRapido');
                    carregarAcervo();
                    if (isAdminGlobal) carregarDashboard();
                    if (document.getElementById('emp').classList.contains('active')) {{
                        filtrarEmprestimos(filtroEmprestimosAtual);
                    }}
                }} else {{
                    const err = await res.json();
                    showToast("Erro: " + err.erro, "error");
                }}
            }}

            async function filtrarEmprestimos(filtro) {{
                if (!isAdminGlobal) return;
                filtroEmprestimosAtual = filtro;
                document.querySelectorAll('.btn-filtro').forEach(b => b.classList.remove('active-filtro'));
                let btnId = 'btn-filtro-todos';
                if (filtro === 'ativos') btnId = 'btn-filtro-ativos';
                else if (filtro === 'atrasados') btnId = 'btn-filtro-atrasados';
                else if (filtro === 'hoje') btnId = 'btn-filtro-hoje';
                else if (filtro === 'devolvidos') btnId = 'btn-filtro-devolvidos';
                document.getElementById(btnId).classList.add('active-filtro');
                
                let url;
                if (filtro === 'atrasados') url = '/api/emprestimos/atrasos';
                else if (filtro === 'hoje') url = '/api/emprestimos/devolucoes-hoje';
                else if (filtro === 'ativos') url = '/api/emprestimos/ativos';
                else if (filtro === 'devolvidos') url = '/api/emprestimos/devolvidos';
                else url = '/api/emprestimos/todos';
                
                const res = await fetch(url);
                const dados = await res.json();
                const div = document.getElementById('lista-ativos');
                
                if (dados.length === 0) {{
                    div.innerHTML = '<p>Nenhum empréstimo encontrado para este filtro.</p>';
                    return;
                }}
                
                let html = '<table class="tabela-emprestimos"><thead>';
                html += '<th>Capa</th><th>Livro</th><th>Leitor</th><th>Telefone</th><th>Série</th><th>Data Empréstimo</th><th>Data Devolução</th><th>Ações</th>';
                html += '</thead><tbody>';
                
                dados.forEach(e => {{
                    html += '<tr>';
                    html += `<td><div class="capa-mini" style="background-image: url('${{e.capa || '/static/images/placeholder.png'}}');"></div></td>`;
                    html += `<td>${{e.livro}}</td>`;
                    html += `<td>${{e.leitor}}</td>`;
                    html += `<td>${{e.telefone || '-'}}</td>`;
                    html += `<td>${{e.serie || '-'}}</td>`;
                    html += `<td>${{e.data_emprestimo || '-'}}</td>`;
                    html += `<td>${{e.data_vencimento || e.vencimento || '-'}}</td>`;
                    html += `<td class="acoes-botoes">`;
                    if (filtro !== 'devolvidos') {{
                        if (isAdminGlobal) {{
                            html += `<button class="btn-primary btn-small" onclick="devolverEmprestimo(${{e.id}})">Devolver</button>`;
                            html += `<button class="btn-primary btn-small" onclick="renovarEmprestimo(${{e.id}})">Renovar</button>`;
                        }} else {{
                            html += `<span>Sem permissão</span>`;
                        }}
                    }} else {{
                        html += `<span>Devolvido em ${{e.data_devolucao}}</span>`;
                    }}
                    html += `<\/td></tr>`;
                }});
                html += '</tbody></table>';
                div.innerHTML = html;
            }}

            async function devolverEmprestimo(id) {{
                if (!isAdminGlobal) return;
                confirmAction("Devolução", "Confirmar devolução do livro?", async () => {{
                    const res = await fetch(`/api/emprestimos/${{id}}/devolver`, {{method: 'POST'}});
                    if(res.ok) {{
                        showToast("Livro devolvido com sucesso!", "success");
                        filtrarEmprestimos(filtroEmprestimosAtual);
                        if (isAdminGlobal) carregarDashboard();
                        carregarAcervo();
                    }} else {{
                        showToast("Erro na devolução", "error");
                    }}
                }});
            }}

            async function renovarEmprestimo(id) {{
                if (!isAdminGlobal) return;
                confirmAction("Renovar Empréstimo", "Deseja renovar este empréstimo por mais um período?", async () => {{
                    const res = await fetch(`/api/emprestimos/${{id}}/renovar`, {{method: 'POST'}});
                    if(res.ok) {{
                        showToast("Empréstimo renovado!", "success");
                        filtrarEmprestimos(filtroEmprestimosAtual);
                        if (isAdminGlobal) carregarDashboard();
                    }} else {{
                        showToast("Erro ao renovar", "error");
                    }}
                }});
            }}

            async function carregarGraficoGeneros() {{
                const res = await fetch('/api/emprestimos/ativos-por-genero');
                const dados = await res.json();
                const ctx = document.getElementById('grafico-generos').getContext('2d');
                if (graficoGenerosInstance) graficoGenerosInstance.destroy();
                const isDark = document.body.classList.contains('dark-mode');
                const textColor = isDark ? '#f0e7de' : '#3e332a';
                const labels = dados.map(d => d.categoria);
                const valores = dados.map(d => d.total);
                const cores = ['#bc8a5f', '#8c8279', '#d4b59e', '#7d9b5e', '#CD853F', '#a3968c'];
                graficoGenerosInstance = new Chart(ctx, {{
                    type: 'pie',
                    data: {{ labels, datasets: [{{ data: valores, backgroundColor: cores.slice(0, labels.length), borderColor: isDark ? '#3c332c' : '#ffffff', borderWidth: 2 }}] }},
                    options: {{ responsive: true, maintainAspectRatio: true, plugins: {{ legend: {{ position: 'bottom', labels: {{ color: textColor, font: {{ family: 'Nunito', size: 12 }}, padding: 15 }} }}, tooltip: {{ callbacks: {{ label: function(context) {{ const total = context.dataset.data.reduce((a,b)=>a+b,0); const value = context.raw; const percent = total > 0 ? Math.round((value/total)*100) : 0; return ` ${{context.label}}: ${{value}} (${{percent}}%)`; }} }} }} }} }}
                }});
            }}

            async function carregarGraficoHistorico() {{
                const res = await fetch('/api/emprestimos/historico-por-genero');
                const dados = await res.json();
                const ctx = document.getElementById('grafico-historico').getContext('2d');
                if (graficoHistoricoInstance) graficoHistoricoInstance.destroy();
                const isDark = document.body.classList.contains('dark-mode');
                const textColor = isDark ? '#f0e7de' : '#3e332a';
                const labels = dados.map(d => d.categoria);
                const valores = dados.map(d => d.total);
                const cores = ['#bc8a5f', '#8c8279', '#d4b59e', '#7d9b5e', '#CD853F', '#a3968c'];
                graficoHistoricoInstance = new Chart(ctx, {{
                    type: 'pie',
                    data: {{ labels, datasets: [{{ data: valores, backgroundColor: cores.slice(0, labels.length), borderColor: isDark ? '#3c332c' : '#ffffff', borderWidth: 2 }}] }},
                    options: {{ responsive: true, maintainAspectRatio: true, plugins: {{ legend: {{ position: 'bottom', labels: {{ color: textColor, font: {{ family: 'Nunito', size: 12 }}, padding: 15 }} }}, tooltip: {{ callbacks: {{ label: function(context) {{ const total = context.dataset.data.reduce((a,b)=>a+b,0); const value = context.raw; const percent = total > 0 ? Math.round((value/total)*100) : 0; return ` ${{context.label}}: ${{value}} (${{percent}}%)`; }} }} }} }} }}
                }});
            }}

            async function carregarRankingLeitores() {{
                if (!isAdminGlobal) return;
                const res = await fetch('/api/emprestimos/ranking-leitores');
                const ranking = await res.json();
                const container = document.getElementById('ranking-leitores');
                container.innerHTML = '';
                if (ranking.length === 0) {{
                    container.innerHTML = '<li style="color:var(--light);">Nenhum empréstimo no trimestre.</li>';
                    return;
                }}
                ranking.forEach((r, index) => {{
                    const extra = r.tipo === 'estudante' ? ` - ${{r.sala}}` : ` (Prof.)`;
                    const li = document.createElement('li');
                    li.innerHTML = `<strong>${{r.nome}}</strong>${{extra}} — <span style="color:var(--green-earth);">${{r.total}} empréstimos</span>`;
                    container.appendChild(li);
                }});
            }}

            async function carregarTopLivros() {{
                const res = await fetch('/api/emprestimos/mais-emprestados');
                const destaques = await res.json();
                const container = document.getElementById('top-livros');
                container.innerHTML = '';
                if (destaques.length === 0) {{
                    container.innerHTML = '<p style="color:var(--light); font-style:italic;">Nenhum empréstimo registrado ainda.</p>';
                    return;
                }}
                const top3 = destaques.slice(0, 3);
                top3.forEach((l, index) => {{
                    const item = document.createElement('div');
                    item.className = 'top-livro-item';
                    item.onclick = () => {{ 
                        const livroCompleto = todosLivros.find(tl => tl.id === l.id);
                        if (livroCompleto) {{ verDetalhes(livroCompleto); tab('acervo'); }}
                    }};
                    item.innerHTML = `<div class="top-livro-capa" style="background-image: url(${{l.capa}});"></div><div class="top-livro-info"><h4>${{l.titulo}}</h4><p>${{l.autor || 'Autor desconhecido'}}</p></div><div class="top-livro-badge">${{l.total_emprestimos}}x</div>`;
                    container.appendChild(item);
                }});
            }}

            async function carregarLivrosAdormecidos() {{
                const res = await fetch('/api/livros/adormecidos');
                const adormecidos = await res.json();
                const container = document.getElementById('lista-adormecidos');
                container.innerHTML = '';
                if (adormecidos.length === 0) {{
                    container.innerHTML = '<p style="color:var(--light); font-style:italic;">Todos os livros tiveram empréstimos nos últimos 6 meses.</p>';
                    return;
                }}
                adormecidos.forEach(l => {{
                    const tag = document.createElement('span');
                    tag.className = 'adormecido-tag';
                    tag.textContent = l.titulo;
                    tag.title = `${{l.autor || 'Autor desconhecido'}}`;
                    tag.onclick = () => {{
                        const livroCompleto = todosLivros.find(tl => tl.id === l.id);
                        if (livroCompleto) {{ verDetalhes(livroCompleto); tab('acervo'); }}
                    }};
                    container.appendChild(tag);
                }});
            }}

            async function carregarDashboard() {{
                if (!isAdminGlobal) return;
                const resLivros = await fetch('/api/livros');
                const livros = await resLivros.json();
                todosLivros = livros;
                document.getElementById('stat-total').innerText = livros.length;
                const totalExemplares = livros.reduce((acc, l) => acc + (l.estoque || 0), 0);
                document.getElementById('stat-exemplares').innerText = totalExemplares;
                const resAtivos = await fetch('/api/emprestimos/ativos/count');
                const ativosData = await resAtivos.json();
                document.getElementById('stat-emp').innerText = ativosData.count;
                const resAtrasos = await fetch('/api/emprestimos/atrasos');
                const atrasos = await resAtrasos.json();
                document.getElementById('stat-atraso').innerText = atrasos.length;
                const resHoje = await fetch('/api/emprestimos/devolucoes-hoje');
                const hojeList = await resHoje.json();
                document.getElementById('stat-hoje').innerText = hojeList.length;
                const resLeitores = await fetch('/api/leitores');
                const leitores = await resLeitores.json();
                document.getElementById('stat-leitores').innerText = leitores.length;
                const hojeStr = new Date().toISOString().split('T')[0];
                const resAgenda = await fetch('/api/agendamentos?periodo=' + periodoAtual);
                const agenda = await resAgenda.json();
                const agendaFutura = agenda.filter(a => a.data >= hojeStr);
                document.getElementById('stat-agenda').innerText = agendaFutura.length;
                carregarGraficoGeneros();
                carregarGraficoHistorico();
                carregarRankingLeitores();
                carregarTopLivros();
                carregarLivrosAdormecidos();
            }}

            async function carregarAgenda() {{
                const hiddenInput = document.getElementById('agenda-data');
                const dataSelecionada = hiddenInput.value;
                periodoAtual = document.getElementById('agenda-periodo').value;
                let url = '/api/agendamentos?periodo=' + encodeURIComponent(periodoAtual);
                if (dataSelecionada) url += '&data=' + encodeURIComponent(dataSelecionada);
                const res = await fetch(url);
                const agendamentos = await res.json();
                const tabela = document.getElementById('tabela-agenda');
                tabela.innerHTML = '';
                const config = carregarConfig();
                const mostrarColunaAula = config.mostrarColunaAula;
                const qtdAulas = configAgenda.aulas;
                let html = '<thead><tr>';
                if (mostrarColunaAula) html += '<th>Aula</th>';
                html += '<th>Agendamento</th></tr></thead><tbody>';
                for(let aula=1; aula<=qtdAulas; aula++) {{
                    const ag = agendamentos.find(a => a.aula === aula);
                    const texto = ag ? `${{ag.professor}} - ${{ag.materia}}` : '-';
                    const classe = ag ? 'ocupado' : '';
                    const dataId = ag ? ag.id : '';
                    html += '<tr>';
                    if (mostrarColunaAula) html += `<td>${{aula}}ª Aula</td>`;
                    html += `<td class="${{classe}}" data-id="${{dataId}}" data-professor="${{ag ? ag.professor : ''}}" data-materia="${{ag ? ag.materia : ''}}" data-uso="${{ag ? ag.uso : ''}}" data-aula="${{aula}}" onclick="celulaAgendaClick(this)">${{texto}}</td>`;
                    html += '</tr>';
                }}
                tabela.innerHTML = html;
                carregarProximosAgendamentos();
                carregarAgendamentosPassados();
            }}

            let agendamentoDetalhesId = null;
            function celulaAgendaClick(cell) {{
                const professor = cell.getAttribute('data-professor');
                const materia = cell.getAttribute('data-materia');
                const uso = cell.getAttribute('data-uso');
                const aula = parseInt(cell.getAttribute('data-aula'));
                const dataSelecionada = document.getElementById('agenda-data').value;
                const periodo = document.getElementById('agenda-periodo').value;
                if (!dataSelecionada) {{
                    showToast("Selecione uma data primeiro.", "warning");
                    return;
                }}
                if (professor && materia && uso) {{
                    agendamentoDetalhesId = cell.getAttribute('data-id');
                    document.getElementById('detalhe-professor').innerText = professor;
                    document.getElementById('detalhe-materia').innerText = materia;
                    document.getElementById('detalhe-uso').innerText = uso;
                    const btnExcluir = document.getElementById('btn-excluir-agendamento-detalhes');
                    if (isAdminGlobal) {{
                        fetch('/api/config/bloquear_excluir_agendamento/status')
                            .then(res => res.json())
                            .then(data => {{
                                if (data.ativo) btnExcluir.style.display = 'none';
                                else btnExcluir.style.display = 'block';
                            }});
                    }} else {{
                        btnExcluir.style.display = 'none';
                    }}
                    openModal('modalDetalhesAgendamento');
                }} else {{
                    if (!isAdminGlobal) {{
                        showToast("Apenas administradores podem criar agendamentos.", "warning");
                        return;
                    }}
                    const hoje = new Date().toISOString().split('T')[0];
                    if (dataSelecionada < hoje) {{
                        showToast("Não é possível criar agendamentos em datas passadas.", "warning");
                        return;
                    }}
                    document.getElementById('agenda-dia').value = new Date(dataSelecionada + 'T00:00:00').getDay();
                    document.getElementById('agenda-aula').value = aula;
                    document.getElementById('agenda-periodo-modal').value = periodo;
                    document.getElementById('agenda-data-modal').value = dataSelecionada;
                    agendamentoAtualId = null;
                    limparFormAgenda();
                    verificarExigirSenhaAgendamento(() => {{ openModal('modalAgendamento'); }});
                }}
            }}

            async function excluirAgendamentoDetalhes() {{
                if (!isAdminGlobal) return;
                if (!agendamentoDetalhesId) return;
                confirmAction("Excluir Agendamento", "Tem certeza que deseja excluir este agendamento?", async () => {{
                    const res = await fetch(`/api/agendamentos/${{agendamentoDetalhesId}}`, {{method: 'DELETE'}});
                    if (res.ok) {{
                        showToast("Agendamento excluído.", "success");
                        closeModal('modalDetalhesAgendamento');
                        carregarAgenda();
                    }} else {{
                        const err = await res.json();
                        showToast(err.erro || "Erro ao excluir agendamento.", "error");
                    }}
                }});
            }}

            async function verificarExigirSenhaAgendamento(callback) {{
                if (!isAdminGlobal) {{ callback(); return; }}
                const res = await fetch('/api/config/exigir_senha_agendamento/status');
                const data = await res.json();
                if (!data.ativo) {{ callback(); return; }}
                const modal = document.getElementById('modalSenhaConfig');
                document.getElementById('senha-titulo').innerText = 'Senha de Administrador';
                document.getElementById('senha-mensagem').innerHTML = 'Digite a senha para criar um agendamento:';
                document.getElementById('senha-confirm').style.display = 'none';
                document.getElementById('senha-input').value = '';
                const btnOk = document.getElementById('btn-senha');
                const originalOnclick = btnOk.onclick;
                btnOk.onclick = async () => {{
                    const senha = document.getElementById('senha-input').value;
                    const resCheck = await fetch('/api/config/senha/verificar', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{senha}})
                    }});
                    const dataCheck = await resCheck.json();
                    if (dataCheck.valido) {{
                        closeModal('modalSenhaConfig');
                        window.senhaAgendamentoGlobal = senha;
                        callback();
                    }} else {{
                        showToast("Senha incorreta", "error");
                    }}
                    btnOk.onclick = originalOnclick;
                }};
                openModal('modalSenhaConfig');
            }}

            function navegarParaAgendamento(ag) {{
                if (!ag || !ag.data || !ag.periodo) return;

                // 1. Atualiza periodoAtual e o select visual correspondente
                periodoAtual = ag.periodo;
                const periodoInput = document.getElementById('agenda-periodo');
                if (periodoInput) periodoInput.value = ag.periodo;
                if (periodoAgendaSelect) {{
                    periodoAgendaSelect.selectedValue = ag.periodo;
                    const opt = periodoAgendaSelect.options.find(o => o.value === ag.periodo);
                    const selectedSpan = periodoAgendaSelect.container.querySelector('.select-selected span');
                    if (selectedSpan && opt) selectedSpan.textContent = opt.text;
                    periodoAgendaSelect.container.querySelectorAll('.select-items div').forEach(div => {{
                        div.classList.remove('same-as-selected');
                        if (opt && div.textContent === opt.text) div.classList.add('same-as-selected');
                    }});
                }}

                // Atualiza a data (sem disparar o onChange do flatpickr, para evitar
                // uma segunda chamada concorrente de carregarAgenda())
                if (flatpickrInstance) flatpickrInstance.setDate(ag.data, false);
                const dataInput = document.getElementById('agenda-data');
                if (dataInput) dataInput.value = ag.data;

                // 2. Renderiza a tabela correta e, 3. após o carregamento, destaca a célula
                carregarAgenda().then(() => {{
                    if (!ag.aula) return;
                    const celula = document.querySelector(`#tabela-agenda td[data-aula="${{ag.aula}}"]`);
                    if (celula) {{
                        celula.classList.add('agendamento-destaque');
                        setTimeout(() => celula.classList.remove('agendamento-destaque'), 2500);
                    }}
                }});
            }}

            async function carregarProximosAgendamentos() {{
                const res = await fetch('/api/agendamentos/datas-com-agendamentos');
                const proximos = await res.json();
                const container = document.getElementById('lista-proximos');
                container.innerHTML = '';
                if (proximos.length === 0) {{
                    container.innerHTML = '<p style="color:var(--light); font-style:italic;">Nenhum agendamento futuro.</p>';
                    return;
                }}
                proximos.slice(0, 5).forEach(ag => {{
                    const span = document.createElement('span');
                    span.className = 'proximo-dia';
                    const dataFormatada = new Date(ag.data + 'T00:00:00').toLocaleDateString('pt-BR');
                    span.textContent = dataFormatada;
                    span.title = `${{ag.professor}} - ${{ag.materia}}`;
                    span.addEventListener('click', () => navegarParaAgendamento(ag));
                    container.appendChild(span);
                }});
            }}

            async function carregarAgendamentosPassados() {{
                const res = await fetch('/api/agendamentos/passados');
                const datas = await res.json();
                const container = document.getElementById('lista-passados');
                container.innerHTML = '';
                if (datas.length === 0) {{
                    container.innerHTML = '<p style="color:var(--light); font-style:italic;">Nenhum agendamento passado.</p>';
                    return;
                }}
                datas.forEach(ag => {{
                    const span = document.createElement('span');
                    span.className = 'passado-dia';
                    const dataFormatada = new Date(ag.data + 'T00:00:00').toLocaleDateString('pt-BR');
                    span.textContent = dataFormatada;
                    span.title = `${{ag.professor}} - ${{ag.materia}}`;
                    span.addEventListener('click', () => navegarParaAgendamento(ag));
                    container.appendChild(span);
                }});
            }}

            function limparFormAgenda() {{
                document.getElementById('agenda-titulo').innerText = 'Novo Agendamento';
                document.getElementById('agenda-existente').style.display = 'none';
                document.getElementById('agenda-form').style.display = 'block';
                document.getElementById('agenda-prof').value = '';
                document.getElementById('agenda-mat').value = '';
                document.getElementById('agenda-uso').value = '';
            }}

            async function salvarAgendamento() {{
                if (!isAdminGlobal) return;
                const prof = document.getElementById('agenda-prof').value;
                const mat = document.getElementById('agenda-mat').value;
                const uso = document.getElementById('agenda-uso').value;
                if(!prof || !mat || !uso) return showToast("Preencha todos os campos.", "warning");
                const dia = parseInt(document.getElementById('agenda-dia').value);
                const aula = parseInt(document.getElementById('agenda-aula').value);
                const periodo = document.getElementById('agenda-periodo-modal').value;
                const data = document.getElementById('agenda-data-modal').value;
                let payload = {{data, periodo, dia, aula, professor: prof, materia: mat, uso}};
                if (window.senhaAgendamentoGlobal) {{
                    payload.senha = window.senhaAgendamentoGlobal;
                    window.senhaAgendamentoGlobal = null;
                }}
                const res = await fetch('/api/agendamentos', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(payload)
                }});
                if (res.status === 400) {{
                    const err = await res.json();
                    showToast(err.erro || "Erro ao agendar.", "error");
                    return;
                }}
                if (res.ok) {{
                    showToast("Agendamento salvo!", "success");
                    closeModal('modalAgendamento');
                    carregarAgenda();
                }} else {{
                    showToast("Erro ao agendar.", "error");
                }}
            }}

            async function excluirAgendamentoAtual() {{
                if (!isAdminGlobal) return;
                if(!agendamentoAtualId) return;
                confirmAction("Excluir Agendamento", "Tem certeza que deseja excluir este agendamento?", async () => {{
                    const res = await fetch(`/api/agendamentos/${{agendamentoAtualId}}`, {{method: 'DELETE'}});
                    if (res.ok) {{
                        showToast("Agendamento excluído.", "success");
                        closeModal('modalAgendamento');
                        agendamentoAtualId = null;
                        carregarAgenda();
                    }} else {{
                        const err = await res.json();
                        showToast(err.erro || "Erro ao excluir agendamento.", "error");
                    }}
                }});
            }}

            async function carregarLeitores() {{
                if (!isAdminGlobal) return;
                const res = await fetch('/api/leitores');
                todosLeitores = await res.json();
                aplicarFiltroLeitores();
            }}

            function aplicarFiltroLeitores() {{
                const termo = document.getElementById('busca-leitor').value.toLowerCase();
                const filtrados = todosLeitores.filter(l => l.nome.toLowerCase().includes(termo));
                exibirListaLeitores(filtrados);
            }}

            function filtrarLeitores() {{ aplicarFiltroLeitores(); }}

            function exibirListaLeitores(leitores) {{
                const div = document.getElementById('lista-leitores');
                div.innerHTML = '';
                leitores.forEach(l => {{
                    const extra = l.tipo === 'estudante' ? `Sala: ${{l.sala}} - Período: ${{l.periodo}}` : `Matéria: ${{l.materia}}`;
                    const telefoneInfo = l.telefone ? `<br><small>Tel: ${{l.telefone}}</small>` : '';
                    const item = document.createElement('div');
                    item.className = 'livro-item';
                    let buttons = '';
                    if (isAdminGlobal) {{
                        buttons = `<button class="btn-primary btn-small" onclick="editarLeitor(${{l.id}})">Editar</button><button class="btn-primary btn-small" style="background:#b33;" onclick="excluirLeitor(${{l.id}})">Excluir</button>`;
                    }}
                    item.innerHTML = `<span><strong>${{l.nome}}</strong> (${{l.tipo}}) - ${{extra}}${{telefoneInfo}}</span><span style="display:flex; gap:8px;">${{buttons}}</span>`;
                    div.appendChild(item);
                }});
            }}

            function toggleLeitorTipo() {{
                const tipo = document.getElementById('leitor-tipo').value;
                document.getElementById('leitor-aluno').style.display = tipo === 'estudante' ? 'block' : 'none';
                document.getElementById('leitor-prof').style.display = tipo === 'professor' ? 'block' : 'none';
            }}

            function editarLeitor(id) {{
                if (!isAdminGlobal) return;
                const leitor = todosLeitores.find(l => l.id === id);
                if(!leitor) return;
                document.getElementById('leitor-id').value = leitor.id;
                document.getElementById('leitor-titulo').innerText = 'Editar Leitor';
                document.getElementById('leitor-tipo').value = leitor.tipo;
                tipoLeitorModalSelect.setValue(leitor.tipo);
                toggleLeitorTipo();
                if(leitor.tipo === 'estudante') {{
                    document.getElementById('leitor-nome').value = leitor.nome;
                    document.getElementById('leitor-sala').value = leitor.sala || '';
                    document.getElementById('leitor-periodo').value = leitor.periodo || '';
                    document.getElementById('leitor-email').value = leitor.email || '';
                    document.getElementById('leitor-telefone').value = leitor.telefone || '';
                }} else {{
                    document.getElementById('leitor-nome-prof').value = leitor.nome;
                    document.getElementById('leitor-materia').value = leitor.materia || '';
                    document.getElementById('leitor-email-prof').value = leitor.email || '';
                }}
                openModal('modalLeitor');
            }}

            async function salvarLeitor() {{
                if (!isAdminGlobal) return;
                const id = document.getElementById('leitor-id').value;
                const tipo = document.getElementById('leitor-tipo').value;
                let payload = {{tipo}};
                if(tipo === 'estudante') {{
                    payload.nome = document.getElementById('leitor-nome').value;
                    payload.sala = document.getElementById('leitor-sala').value;
                    payload.periodo = document.getElementById('leitor-periodo').value;
                    payload.email = document.getElementById('leitor-email').value;
                    payload.telefone = document.getElementById('leitor-telefone').value;
                    if(!payload.nome || !payload.sala || !payload.periodo) return showToast("Preencha todos os campos.", "warning");
                }} else {{
                    payload.nome = document.getElementById('leitor-nome-prof').value;
                    payload.materia = document.getElementById('leitor-materia').value;
                    payload.email = document.getElementById('leitor-email-prof').value;
                    if(!payload.nome || !payload.materia) return showToast("Preencha todos os campos.", "warning");
                }}
                const url = id ? `/api/leitores/${{id}}` : '/api/leitores';
                const method = id ? 'PUT' : 'POST';
                const res = await fetch(url, {{
                    method: method,
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(payload)
                }});
                if(res.ok) {{
                    showToast(id ? "Leitor atualizado!" : "Leitor cadastrado!", "success");
                    document.getElementById('leitor-id').value = '';
                    document.getElementById('leitor-nome').value = '';
                    document.getElementById('leitor-sala').value = '';
                    document.getElementById('leitor-periodo').value = '';
                    document.getElementById('leitor-email').value = '';
                    document.getElementById('leitor-nome-prof').value = '';
                    document.getElementById('leitor-materia').value = '';
                    document.getElementById('leitor-email-prof').value = '';
                    document.getElementById('leitor-telefone').value = '';
                    tipoLeitorModalSelect.setValue('estudante');
                    document.getElementById('leitor-aluno').style.display = 'block';
                    document.getElementById('leitor-prof').style.display = 'none';
                    closeModal('modalLeitor');
                    carregarLeitores();
                    document.getElementById('leitor-id').value = '';
                    document.getElementById('leitor-titulo').innerText = 'Novo Leitor';
                }} else {{
                    showToast("Erro ao salvar leitor", "error");
                }}
            }}

            async function excluirLeitor(id) {{
                if (!isAdminGlobal) return;
                confirmAction("Excluir Leitor", "Tem certeza que deseja excluir este leitor?", async () => {{
                    await fetch(`/api/leitores/${{id}}`, {{method: 'DELETE'}});
                    showToast("Leitor excluído.", "success");
                    carregarLeitores();
                }});
            }}

            async function abrirConfiguracoes() {{
                if (!isAdminGlobal) return;
                const statusRes = await fetch('/api/config/senha/status');
                const data = await statusRes.json();
                if (!data.set) {{
                    document.getElementById('senha-confirm').style.display = 'block';
                    document.getElementById('senha-titulo').innerText = 'Criar Senha de Administrador';
                    document.getElementById('senha-mensagem').innerText = 'Defina uma senha de 4 dígitos para proteger as configurações:';
                    document.getElementById('senha-input').value = '';
                    document.getElementById('senha-confirm').value = '';
                    document.getElementById('btn-senha').onclick = async () => {{
                        const senha = document.getElementById('senha-input').value;
                        const confirm = document.getElementById('senha-confirm').value;
                        if (!senha || senha.length !== 4) {{ showToast("A senha deve ter 4 caracteres", "warning"); return; }}
                        if (senha !== confirm) {{ showToast("As senhas não conferem", "warning"); return; }}
                        const res = await fetch('/api/config/senha/definir', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{senha}})
                        }});
                        if (res.ok) {{
                            showToast("Senha criada com sucesso!", "success");
                            closeModal('modalSenhaConfig');
                            abrirModalConfiguracoes();
                        }} else {{
                            const err = await res.json();
                            showToast("Erro: " + err.erro, "error");
                        }}
                    }};
                    openModal('modalSenhaConfig');
                }} else {{
                    document.getElementById('senha-confirm').style.display = 'none';
                    document.getElementById('senha-titulo').innerText = 'Senha de Administrador';
                    document.getElementById('senha-mensagem').innerText = 'Digite a senha para acessar as configurações:';
                    document.getElementById('senha-input').value = '';
                    document.getElementById('btn-senha').onclick = async () => {{
                        const senha = document.getElementById('senha-input').value;
                        if (!senha) {{ showToast("Digite a senha", "warning"); return; }}
                        const res = await fetch('/api/config/senha/verificar', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{senha}})
                        }});
                        const data = await res.json();
                        if (data.valido) {{
                            closeModal('modalSenhaConfig');
                            abrirModalConfiguracoes();
                        }} else {{
                            showToast("Senha incorreta", "error");
                        }}
                    }};
                    openModal('modalSenhaConfig');
                }}
            }}

            async function abrirModalConfiguracoes() {{
                const config = carregarConfig();
                const container = document.getElementById('lista-config-toggles');
                container.innerHTML = '';

                const respExigirSenhaEmprestimo = await fetch('/api/config/exigir_senha_emprestimo/status');
                const exigirSenhaEmprestimo = (await respExigirSenhaEmprestimo.json()).ativo;
                const respObrigarLocalizacao = await fetch('/api/config/obrigar_localizacao_livro/status');
                const obrigarLocalizacao = (await respObrigarLocalizacao.json()).ativo;
                const respExigirSenhaAgendamento = await fetch('/api/config/exigir_senha_agendamento/status');
                const exigirSenhaAgendamento = (await respExigirSenhaAgendamento.json()).ativo;
                const respBloqEmail = await fetch('/api/config/bloquear_email/status');
                const bloqueioEmail = (await respBloqEmail.json()).bloqueado;
                const respBloqExcluirAgenda = await fetch('/api/config/bloquear_excluir_agendamento/status');
                const bloquearExcluirAgenda = (await respBloqExcluirAgenda.json()).ativo;
                const respQtdAulas = await fetch('/api/config/quantidade_aulas/status');
                const quantidadeAulas = (await respQtdAulas.json()).quantidade;
                const respEmailStatus = await fetch('/api/config/email/status');
                const emailOrganizacaoAtual = (await respEmailStatus.json()).email || '';

                // Categorias visuais do modal de configurações (Tarefa 3)
                const categorias = [
                    {{
                        titulo: 'Cadastro de Livros',
                        toggles: [
                            {{ label: 'Campo "Descrição" no cadastro de livros', key: 'campoDescricaoVisivel', checked: config.campoDescricaoVisivel, desc: 'Mostra ou oculta o campo de descrição ao adicionar/editar livros.' }},
                            {{ label: 'Campo "Temas" no cadastro de livros', key: 'campoTemasVisivel', checked: config.campoTemasVisivel, desc: 'Mostra ou oculta o campo de temas ao adicionar/editar livros.' }},
                            {{ label: 'Campo "Ano" no cadastro de livros', key: 'campoAnoVisivel', checked: config.campoAnoVisivel, desc: 'Mostra ou oculta o campo de ano de publicação.' }},
                            {{ label: 'Campo "Categoria" no cadastro de livros', key: 'campoCategoriaVisivel', checked: config.campoCategoriaVisivel, desc: 'Mostra ou oculta o campo de categoria.' }},
                            {{ label: 'Obrigar preenchimento da localização física/prateleira ao cadastrar livros', key: 'obrigarLocalizacao', checked: obrigarLocalizacao, desc: 'Torna o campo de localização (prateleira) obrigatório ao adicionar/editar livros.' }},
                            {{ label: 'Bloquear botão "Excluir Livro"', key: 'bloquearExcluirLivro', checked: config.bloquearExcluirLivro, desc: 'Remove o botão de excluir livro da interface.' }}
                        ]
                    }},
                    {{
                        titulo: 'Agenda e Agendamentos',
                        toggles: [
                            {{ label: 'Mostrar coluna "Aula" na agenda', key: 'mostrarColunaAula', checked: config.mostrarColunaAula, desc: 'Exibe ou oculta a coluna de numeração das aulas na tabela de agenda.' }},
                            {{ label: 'Exigir senha de administrador para agendamentos de salas', key: 'exigirSenhaAgendamento', checked: exigirSenhaAgendamento, desc: 'Solicita a senha de 4 dígitos antes de criar um agendamento.' }},
                            {{ label: 'Bloquear botão "Excluir Agendamento"', key: 'bloquearExcluirAgendamento', checked: bloquearExcluirAgenda, desc: 'Remove ou desabilita o botão de excluir agendamento na interface.' }}
                        ],
                        extra: 'aulas'
                    }},
                    {{
                        titulo: 'Empréstimos',
                        toggles: [
                            {{ label: 'Campo "Telefone do Aluno" no empréstimo', key: 'campoNumeroUsuario', checked: config.campoNumeroUsuario, desc: 'Exibe o campo para registrar o telefone do estudante durante o empréstimo.' }},
                            {{ label: 'Exigir senha de administrador ao realizar empréstimos', key: 'exigirSenhaEmprestimo', checked: exigirSenhaEmprestimo, desc: 'Solicita a senha de 4 dígitos antes de confirmar um empréstimo.' }}
                        ]
                    }},
                    {{
                        titulo: 'E-mails',
                        toggles: [
                            {{ label: 'Bloquear envio de e-mails', key: 'bloquearEmail', checked: bloqueioEmail, desc: 'Impede o sistema de enviar qualquer e-mail de notificação ou confirmação.' }}
                        ],
                        extra: 'email'
                    }}
                ];

                categorias.forEach(cat => {{
                    const painel = document.createElement('div');
                    painel.className = 'config-panel';

                    const subtitulo = document.createElement('h4');
                    subtitulo.className = 'config-subtitulo';
                    subtitulo.innerText = cat.titulo;
                    painel.appendChild(subtitulo);

                    cat.toggles.forEach(tgl => {{
                        const row = document.createElement('div');
                        row.className = 'config-toggle-row';
                        row.innerHTML = `
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span>${{tgl.label}}</span>
                                <label class="switch">
                                    <input type="checkbox" id="cfg-${{tgl.key}}" ${{tgl.checked ? 'checked' : ''}} onchange="if('${{tgl.key}}'==='bloquearEmail') atualizarBloqueioEmail(this.checked); else if('${{tgl.key}}'==='exigirSenhaEmprestimo') atualizarExigirSenhaEmprestimo(this.checked); else if('${{tgl.key}}'==='obrigarLocalizacao') atualizarObrigarLocalizacao(this.checked); else if('${{tgl.key}}'==='exigirSenhaAgendamento') atualizarExigirSenhaAgendamento(this.checked); else if('${{tgl.key}}'==='bloquearExcluirAgendamento') atualizarBloquearExcluirAgendamento(this.checked);">
                                    <span class="slider"></span>
                                </label>
                            </div>
                            <small style="color:var(--light); font-size:11px; margin-top:5px;">${{tgl.desc}}</small>
                        `;
                        painel.appendChild(row);
                    }});

                    if (cat.extra === 'aulas') {{
                        const aulaRow = document.createElement('div');
                        aulaRow.style.marginTop = '15px';
                        aulaRow.innerHTML = `
                            <label>Quantidade de aulas diárias:</label>
                            <input type="number" id="cfg-quantidade-aulas" min="1" max="20" value="${{quantidadeAulas}}" style="width:100%; margin-top:5px;">
                            <small style="color:var(--light); font-size:11px;">Define quantas linhas (horários) serão exibidas na tabela de agenda.</small>
                        `;
                        painel.appendChild(aulaRow);
                    }}

                    if (cat.extra === 'email') {{
                        const emailRow = document.createElement('div');
                        emailRow.style.marginTop = '15px';
                        emailRow.innerHTML = `
                            <label>E-mail da Organização:</label>
                            <input type="email" id="cfg-email-organizacao" placeholder="biblioteca@escola.com" value="${{emailOrganizacaoAtual}}" style="width:100%; margin-top:5px;">
                            <label style="margin-top:10px; display:block;">Chave de App (senha de aplicativo):</label>
                            <input type="password" id="cfg-email-app-password" placeholder="Deixe em branco para não alterar" style="width:100%; margin-top:5px;" autocomplete="new-password">
                            <small style="color:var(--light); font-size:11px;">Credenciais usadas para o envio de e-mails de notificação. A chave de app não é reexibida por segurança.</small>
                        `;
                        painel.appendChild(emailRow);
                    }}

                    container.appendChild(painel);
                }});

                openModal('modalConfiguracoes');
            }}

            async function atualizarBloqueioEmail(bloqueado) {{
                await fetch('/api/config/bloquear_email/set', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{bloqueado}}) }});
            }}
            async function atualizarExigirSenhaEmprestimo(ativo) {{
                await fetch('/api/config/exigir_senha_emprestimo/set', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{ativo}}) }});
            }}
            async function atualizarObrigarLocalizacao(ativo) {{
                await fetch('/api/config/obrigar_localizacao_livro/set', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{ativo}}) }});
                verificarObrigarLocalizacao();
            }}
            async function atualizarExigirSenhaAgendamento(ativo) {{
                await fetch('/api/config/exigir_senha_agendamento/set', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{ativo}}) }});
            }}
            async function atualizarBloquearExcluirAgendamento(ativo) {{
                await fetch('/api/config/bloquear_excluir_agendamento/set', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{ativo}}) }});
            }}

            async function salvarConfigGerais() {{
                if (!isAdminGlobal) return;
                const config = carregarConfig();
                config.mostrarColunaAula = document.getElementById('cfg-mostrarColunaAula')?.checked ?? config.mostrarColunaAula;
                config.campoDescricaoVisivel = document.getElementById('cfg-campoDescricaoVisivel')?.checked ?? config.campoDescricaoVisivel;
                config.campoTemasVisivel = document.getElementById('cfg-campoTemasVisivel')?.checked ?? config.campoTemasVisivel;
                config.campoAnoVisivel = document.getElementById('cfg-campoAnoVisivel')?.checked ?? config.campoAnoVisivel;
                config.campoCategoriaVisivel = document.getElementById('cfg-campoCategoriaVisivel')?.checked ?? config.campoCategoriaVisivel;
                config.campoNumeroUsuario = document.getElementById('cfg-campoNumeroUsuario')?.checked ?? config.campoNumeroUsuario;
                config.bloquearExcluirLivro = document.getElementById('cfg-bloquearExcluirLivro')?.checked ?? config.bloquearExcluirLivro;
                salvarConfig(config);
                
                const novaQtdAulas = parseInt(document.getElementById('cfg-quantidade-aulas')?.value);
                if (novaQtdAulas && novaQtdAulas >= 1 && novaQtdAulas <= 20) {{
                    await fetch('/api/config/quantidade_aulas/set', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{quantidade: novaQtdAulas}})
                    }});
                    configAgenda.aulas = novaQtdAulas;
                    carregarAgenda();
                }}

                const emailOrganizacaoInput = document.getElementById('cfg-email-organizacao');
                const emailAppPasswordInput = document.getElementById('cfg-email-app-password');
                if (emailOrganizacaoInput) {{
                    const emailOrganizacao = emailOrganizacaoInput.value.trim();
                    const emailAppPassword = emailAppPasswordInput ? emailAppPasswordInput.value.trim() : '';
                    const resEmail = await fetch('/api/config/email/set', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{email_organizacao: emailOrganizacao, email_app_password: emailAppPassword}})
                    }});
                    if (!resEmail.ok) {{
                        const errEmail = await resEmail.json();
                        showToast(errEmail.erro || "Erro ao salvar configuração de e-mail.", "error");
                    }}
                }}

                aplicarVisibilidadeCamposLivro(true);
                aplicarVisibilidadeCamposLivro(false);
                aplicarVisibilidadeCamposEmprestimo();
                if (livroSelecionado) verDetalhes(livroSelecionado);
                carregarGraficoGeneros();
                carregarGraficoHistorico();
                closeModal('modalConfiguracoes');
                showToast("Configurações aplicadas!", "success");
            }}

            function aplicarVisibilidadeCamposEmprestimo() {{
                const config = carregarConfig();
                const campoTelefone = document.querySelector('.campo-telefone-aluno');
                if (campoTelefone) campoTelefone.style.display = config.campoNumeroUsuario ? 'block' : 'none';
            }}

            function initFlatpickr() {{
                const currentYear = new Date().getFullYear();
                const meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
                const years = [currentYear];
                flatpickrInstance = flatpickr("#agenda-data-alt", {{
                    locale: "pt",
                    dateFormat: "Y-m-d",
                    altInput: true,
                    altFormat: "d/m/Y",
                    defaultDate: new Date(),
                    minDate: new Date(currentYear, 0, 1),
                    maxDate: new Date(currentYear, 11, 31),
                    disableMobile: true,
                    onChange: function(selectedDates, dateStr, instance) {{
                        document.getElementById('agenda-data').value = dateStr;
                        carregarAgenda();
                    }},
                    onReady: function(selectedDates, dateStr, instance) {{
                        document.getElementById('agenda-data').value = dateStr;
                        const navigation = instance.calendarContainer.querySelector('.flatpickr-months');
                        if (navigation) navigation.style.display = 'none';
                        const header = document.createElement('div');
                        header.className = 'custom-fp-header';
                        const monthSelectHtml = `<div class="fake-select" id="month-trigger"><span id="month-label">${{meses[new Date().getMonth()]}}</span><div class="fake-options" id="month-list">${{meses.map((m, i) => `<div data-val="${{i}}">${{m}}</div>`).join('')}}</div></div>`;
                        const yearSelectHtml = `<div class="fake-select" id="year-trigger"><span id="year-label">${{currentYear}}</span><div class="fake-options" id="year-list">${{years.map(y => `<div data-val="${{y}}">${{y}}</div>`).join('')}}</div></div>`;
                        header.innerHTML = monthSelectHtml + yearSelectHtml;
                        instance.calendarContainer.prepend(header);
                        document.querySelectorAll('.fake-select').forEach(select => {{
                            select.addEventListener('click', function(e) {{ e.stopPropagation(); this.classList.toggle('active'); }});
                        }});
                        header.querySelectorAll('#month-list div').forEach(opt => {{
                            opt.addEventListener('click', (e) => {{ const val = parseInt(e.target.dataset.val); instance.changeMonth(val, false); document.getElementById('month-label').innerText = meses[val]; }});
                        }});
                        header.querySelectorAll('#year-list div').forEach(opt => {{
                            opt.addEventListener('click', (e) => {{ const val = parseInt(e.target.dataset.val); if (val === currentYear) {{ instance.changeYear(val); document.getElementById('year-label').innerText = val; }} }});
                        }});
                        document.addEventListener('click', () => {{ document.querySelectorAll('.fake-select').forEach(s => s.classList.remove('active')); }});
                    }}
                }});
            }}

            let todosLivros = [];
            let todosLeitores = [];
            let livroSelecionado = null;
            let agendamentoAtualId = null;
            let periodoAtual = 'Manhã';
            let configAgenda = {{ aulas: quantidadeAulasGlobal }};
            let flatpickrInstance = null;
            let graficoGenerosInstance = null;
            let graficoHistoricoInstance = null;
            let filtroEmprestimosAtual = 'todos';
            let senhaEmprestimoGlobal = null;
            let senhaAgendamentoGlobal = null;

            window.onload = () => {{
                verificarAdmin();
                const config = carregarConfig();
                if (config.darkMode) toggleTheme(true);
                else toggleTheme(false);
                initCustomSelects();
                carregarConfigAgenda();
                initFlatpickr();
                carregarAcervo();
                if (isAdminGlobal) {{
                    carregarDashboard();
                    carregarLeitores();
                }}
                carregarAgenda();
                aplicarVisibilidadeCamposLivro(true);
                aplicarVisibilidadeCamposLivro(false);
                aplicarVisibilidadeCamposEmprestimo();
                setupDragAndDrop('manual-capa-preview', 'manual-capa-url');
                setupDragAndDrop('edit-capa-preview', 'edit-capa-url');
                verificarObrigarLocalizacao();
                setInterval(async () => {{ if (isAdminGlobal) await fetch('/api/emprestimos/ativos'); }}, 30 * 60 * 1000);
            }};
        </script>
    </body>
    </html>
    """
    return html

# Landing page (sem alterações significativas)
LANDING_PAGE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BIBI - Biblioteca Inteligente</title>
    <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-light: #fdfaf5;
            --container-bg: #ffffff;
            --accent-clay: #bc8a5f;
            --text-dark: #2d2926;
            --text-muted: #7d756d;
            --border-color: #eee9e0;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-light);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            color: var(--text-dark);
            transition: all 0.3s ease;
        }

        .container {
            background-color: var(--container-bg);
            width: 92%;
            max-width: 1100px;
            border-radius: 40px;
            padding: 60px;
            border: 1px solid var(--border-color);
            box-shadow: 0 20px 40px rgba(0,0,0,0.05);
            position: relative;
            min-height: 650px;
        }

        .navbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 60px;
        }

        .logo-img { 
            height: 40px;
            width: auto;
        }

        .nav-links {
            display: flex;
            list-style: none;
            gap: 30px;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .nav-links a {
            text-decoration: none;
            color: var(--text-muted);
            transition: color 0.3s;
            cursor: pointer;
        }

        .nav-links a:hover { color: var(--accent-clay); }

        #home-section, #about-section { display: none; }
        #home-section.active, #about-section.active { display: flex; }

        .content-wrapper { align-items: center; gap: 60px; }
        .text-section { flex: 1.2; }
        .main-title {
            font-family: 'Playfair Display', serif;
            font-size: 4.2rem;
            line-height: 1;
            margin-bottom: 35px;
            color: var(--text-dark);
        }
        .discover-row { display: flex; align-items: center; gap: 15px; }
        .inline-icon { height: 45px; width: auto; opacity: 0.9; }
        .sub-title {
            display: block;
            font-style: italic;
            font-weight: 400;
            font-size: 3.8rem;
            color: var(--accent-clay);
        }
        .quote {
            font-size: 1.15rem;
            max-width: 420px;
            line-height: 1.7;
            margin-bottom: 40px;
            color: var(--text-muted);
            font-style: italic;
        }
        .cta-button {
            background-color: var(--text-dark);
            color: #ffffff;
            border: none;
            padding: 18px 40px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
        }
        .cta-button:hover {
            background-color: var(--accent-clay);
            transform: translateY(-2px);
        }

        .image-section { flex: 1; }
        .image-container {
            width: 100%;
            aspect-ratio: 0.85 / 1;
            background-color: #f0f0f0;
            border-radius: 200px 200px 20px 20px;
            overflow: hidden;
            border: 1px solid var(--border-color);
        }
        #hero-image { width: 100%; height: 100%; object-fit: cover; }

        .about-content {
            flex-direction: column;
            max-width: 800px;
            margin: 0 auto;
        }
        .about-title {
            font-family: 'Playfair Display', serif;
            font-size: 3rem;
            margin-bottom: 30px;
            text-align: center;
        }
        .about-text {
            line-height: 1.8;
            color: var(--text-dark);
            font-size: 1.05rem;
            text-align: justify;
        }
        .about-text p { margin-bottom: 20px; }
        
        .social-footer {
            margin-top: 40px;
            text-align: center;
            border-top: 1px solid var(--border-color);
            padding-top: 20px;
            display: flex;
            justify-content: center;
            gap: 25px;
            flex-wrap: wrap;
        }
        .social-link {
            text-decoration: none;
            color: var(--text-dark);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 2px;
            opacity: 0.8;
            font-weight: 600;
            transition: opacity 0.3s;
        }
        .social-link:hover { opacity: 1; color: var(--accent-clay); }

        body.dark-mode {
            --bg-light: #1e1e1e;
            --container-bg: #2d2a26;
            --accent-clay: #a0522d;
            --text-dark: #f0e7de;
            --text-muted: #a3968c;
            --border-color: #5a4e44;
        }
        body.dark-mode .cta-button {
            background-color: #2d2926;
            color: #f0e7de;
            border: 1px solid var(--accent-clay);
        }
        body.dark-mode .cta-button:hover {
            background-color: var(--accent-clay);
            color: #ffffff;
        }

        @media (max-width: 900px) {
            .content-wrapper { flex-direction: column-reverse; text-align: center; }
            .discover-row { justify-content: center; }
            .main-title { font-size: 3rem; }
            .sub-title { font-size: 2.5rem; }
        }
    </style>
</head>
<body>

    <div class="container">
        <nav class="navbar">
            <div class="logo">
                <a href="#" onclick="showSection('home')">
                    <img src="static/images/philocode.png" alt="Philocode" class="logo-img">
                </a>
            </div>
            <ul class="nav-links">
                <li><a onclick="showSection('about')">Sobre nós</a></li>
                <li><a href="mailto:philocode5@gmail.com">Contato</a></li>
            </ul>
        </nav>

        <main id="home-section" class="content-wrapper active">
            <section class="text-section">
                <h1 class="main-title">
                    <div class="discover-row">
                        <img src="static/images/icon.png" alt="icon" class="inline-icon">
                        <span>BIBI</span>
                    </div>
                    <span class="sub-title">Biblioteca Inteligente</span>
                </h1>
                <p class="quote">
                    "A educação exige os maiores cuidados, porque influi sobre toda a vida" <br>
                    <span style="color: var(--accent-clay); font-weight: bold; font-style: normal;">— Sêneca</span>
                </p>
                <button class="cta-button" onclick="window.location.href='/app'">Entrar no Sistema</button>
            </section>

            <section class="image-section">
                <div class="image-container">
                    <img id="hero-image" src="" alt="Biblioteca">
                </div>
            </section>
        </main>

        <main id="about-section" class="content-wrapper about-content">
            <h2 class="about-title">Sobre nós</h2>
            <div class="about-text">
                <p>A BIBI — Biblioteca Inteligente é um projeto desenvolvido pela startup Philocode, uma iniciativa que nasce com um compromisso claro: fortalecer a educação por meio da tecnologia.</p>
                <p>Na Philocode, acreditamos que a educação é o pilar fundamental para o desenvolvimento de qualquer indivíduo e que seu acesso deve ser cada vez mais democrático. Por isso, todos os nossos projetos são pensados para apoiar o processo educacional de adolescentes e jovens, criando soluções que unem inovação, simplicidade e impacto real.</p>
                <p>A BIBI surge com esse propósito, automatizando o gerenciamento de acervos escolares e facilitando o acesso à informação dentro do ambiente educacional. Da mesma forma, desenvolvemos o jogo O.F.F: Onde Falta Futuro, que propõe reflexões sobre problemas urbanos por meio de uma experiência gamificada, estimulando o pensamento crítico e o engajamento social.</p>
                <p>Mais do que desenvolver ferramentas, buscamos criar caminhos para que o conhecimento seja acessível, relevante e transformador. Valorizamos a inclusão, a acessibilidade e a construção coletiva, porque entendemos que a educação só cumpre seu papel quando alcança a todos.</p>
                <p>Inspirados pelo pensamento de Sêneca — “A educação exige os maiores cuidados, porque influi sobre toda a vida” —, seguimos comprometidos em desenvolver soluções que não apenas acompanhem o futuro, mas ajudem a construí-lo.</p>
                <p>Essa é apenas a primeira etapa da nossa jornada, e queremos que você faça parte dessa transformação.</p>
            </div>
            <footer class="social-footer">
                <a href="https://www.instagram.com/philo_code" target="_blank" class="social-link">Instagram</a>
                <a href="https://www.linkedin.com/in/philocode/" target="_blank" class="social-link">LinkedIn</a>
                <a href="https://github.com/C3ss2k/BIBI-Biblioteca-Inteligente" target="_blank" class="social-link">GitHub</a>
            </footer>
        </main>
    </div>

    <script>
        function showSection(section) {
            document.getElementById('home-section').classList.remove('active');
            document.getElementById('about-section').classList.remove('active');
            
            if(section === 'home') {
                document.getElementById('home-section').classList.add('active');
            } else {
                document.getElementById('about-section').classList.add('active');
            }
        }

        async function carregarHeroImage() {
            const heroImg = document.getElementById('hero-image');
            try {
                const resp = await fetch('/api/hero-image');
                const data = await resp.json();
                heroImg.src = data.url;
            } catch (error) {
                console.error('Erro ao carregar hero image:', error);
                heroImg.src = 'static/images/hero/hero.jpg';
            }
            heroImg.onerror = function() {
                this.src = 'static/images/hero/hero.jpg';
            };
        }

        document.addEventListener('DOMContentLoaded', () => {
            carregarHeroImage();
            if (localStorage.getItem('darkMode') === 'true') {
                document.body.classList.add('dark-mode');
            }
        });
    </script>
</body>
</html>
"""

def buscar_open_library(isbn):
    """API #1 - Open Library"""
    try:
        url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            key = f"ISBN:{isbn}"
            if key in data:
                book = data[key]
                titulo = book.get('title', 'Título Desconhecido')
                autores = book.get('authors')
                autor = autores[0]['name'] if autores else 'Autor Desconhecido'
                ano = None
                if 'publish_date' in book:
                    import re
                    match = re.search(r'\d{4}', book['publish_date'])
                    if match:
                        ano = int(match.group())
                descricao = ''
                if 'excerpts' in book and book['excerpts']:
                    descricao = book['excerpts'][0]['text']
                temas = ''
                if 'subjects' in book:
                    temas = ', '.join([s['name'] for s in book['subjects'][:3]])
                categoria = 'Ficção'
                capa = ''
                if 'cover' in book and book['cover']:
                    capa_id = book['cover']['large'] if 'large' in book['cover'] else book['cover']['medium'] if 'medium' in book['cover'] else ''
                    if capa_id:
                        capa = capa_id
                if not capa:
                    capa = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
                return {
                    "titulo": titulo,
                    "autor": autor,
                    "ano_publicacao": ano,
                    "descricao": descricao,
                    "temas": temas,
                    "categoria": categoria,
                    "capa": capa
                }
    except Exception as e:
        print(f"Erro Open Library: {e}")
    return None

def buscar_brasil_api(isbn):
    """API #2 - BrasilAPI (ISBN)"""
    try:
        url = f"https://brasilapi.com.br/api/isbn/v1/{isbn}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            titulo = data.get('title', 'Título Desconhecido')
            autor = ''
            autores = data.get('authors', [])
            if autores:
                autor = autores[0] if isinstance(autores[0], str) else autores[0].get('name', '')
            if not autor:
                autor = data.get('author', 'Autor Desconhecido')
            ano = None
            if data.get('year'):
                try:
                    ano = int(data['year'])
                except:
                    pass
            descricao = data.get('synopsis', '') or ''
            temas = data.get('subjects', '') or ''
            if isinstance(temas, list):
                temas = ', '.join(temas[:3])
            categoria = data.get('categories', '') or ''
            if isinstance(categoria, list):
                categoria = categoria[0] if categoria else 'Ficção'
            if not categoria:
                categoria = 'Ficção'
            capa = data.get('cover_url', '') or ''
            if not capa:
                capa = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
            return {
                "titulo": titulo,
                "autor": autor,
                "ano_publicacao": ano,
                "descricao": descricao,
                "temas": temas,
                "categoria": categoria,
                "capa": capa
            }
    except Exception as e:
        print(f"Erro BrasilAPI: {e}")
    return None

def buscar_google_books_por_isbn(isbn):
    """API #3 - Google Books (por ISBN primeiro)"""
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if 'items' in data and len(data['items']) > 0:
                book = data['items'][0]['volumeInfo']
                return _extrair_dados_google(book, isbn)
    except Exception as e:
        print(f"Erro Google Books (ISBN): {e}")
    return None

def buscar_google_books_por_titulo(titulo):
    """API #3 - Google Books (fallback por título)"""
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q=intitle:{requests.utils.quote(titulo)}&maxResults=1"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if 'items' in data and len(data['items']) > 0:
                book = data['items'][0]['volumeInfo']
                return _extrair_dados_google(book, None)
    except Exception as e:
        print(f"Erro Google Books (Título): {e}")
    return None

def _extrair_dados_google(book, isbn):
    titulo = book.get('title', 'Título Desconhecido')
    autores = book.get('authors', [])
    autor = autores[0] if autores else 'Autor Desconhecido'
    ano = None
    if 'publishedDate' in book:
        try:
            ano = int(book['publishedDate'][:4])
        except:
            pass
    descricao = book.get('description', '') or ''
    # Limpar tags HTML da descrição
    descricao = re.sub(r'<[^>]+>', '', descricao)
    temas_list = book.get('categories', [])
    temas = ', '.join(temas_list[:3]) if temas_list else ''
    categoria = temas_list[0] if temas_list else 'Ficção'
    capa = ''
    if 'imageLinks' in book:
        capa = book['imageLinks'].get('thumbnail', '') or ''
        if capa:
            capa = capa.replace('http://', 'https://')
    if not capa and isbn:
        capa = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
    return {
        "titulo": titulo,
        "autor": autor,
        "ano_publicacao": ano,
        "descricao": descricao,
        "temas": temas,
        "categoria": categoria,
        "capa": capa
    }

def buscar_livro_cascata(isbn):
    """
    Busca dados do livro em cascata usando múltiplas APIs.
    Preenche incrementalmente: se a primeira retornar parcialmente,
    as seguintes complementam sem sobrescrever dados existentes.
    """
    # Dicionário vazio para acumular dados
    dados = {
        "titulo": None,
        "autor": None,
        "ano_publicacao": None,
        "descricao": None,
        "temas": None,
        "categoria": None,
        "capa": None
    }

    def preencher_faltantes(fonte):
        """Preenche apenas campos que ainda estão vazios"""
        modificado = False
        for campo in dados:
            if (dados[campo] is None or dados[campo] == '') and fonte.get(campo):
                dados[campo] = fonte[campo]
                modificado = True
        return modificado

    # 1. Open Library
    print(f"Buscando ISBN {isbn} na Open Library...")
    ol = buscar_open_library(isbn)
    if ol:
        preencher_faltantes(ol)
        if all(v is not None and v != '' for v in dados.values() if v is not None):
            return dados

    # 2. BrasilAPI
    print(f"Buscando ISBN {isbn} na BrasilAPI...")
    br = buscar_brasil_api(isbn)
    if br:
        preencher_faltantes(br)
        if all(v is not None and v != '' for v in dados.values() if v is not None):
            return dados

    # 3. Google Books (primeiro por ISBN)
    print(f"Buscando ISBN {isbn} no Google Books...")
    gb = buscar_google_books_por_isbn(isbn)
    if gb:
        preencher_faltantes(gb)
        if all(v is not None and v != '' for v in dados.values() if v is not None):
            return dados

    # 4. Google Books (fallback por título, se tiver título)
    if dados.get("titulo"):
        print(f"Buscando '{dados['titulo']}' no Google Books (fallback por título)...")
        gb_titulo = buscar_google_books_por_titulo(dados["titulo"])
        if gb_titulo:
            preencher_faltantes(gb_titulo)

    # Se pelo menos título e autor foram preenchidos, considera sucesso
    if dados.get("titulo") and dados.get("autor"):
        return dados
    return None

if __name__ == '__main__':

    iniciar_verificacao_notificacoes()

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