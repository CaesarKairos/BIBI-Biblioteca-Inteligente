from config import BASE_DIR, TEMPLATE_DIR
from jinja2 import Environment, FileSystemLoader
from database.database import db_manager
from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from services.configuracoes_service import get_email_credenciais
from services.configuracoes_service import is_email_blocked
from services.image_service import get_book_cover_image_bytes
from utils.datetime import get_brasilia_today
import os
import smtplib
import threading
import time


# Email rendering must also work in background threads, without Flask context.
# autoescape=False preserves the exact interpolation of the original messages.
EMAIL_TEMPLATES = Environment(
    loader=FileSystemLoader(os.path.join(TEMPLATE_DIR, 'emails')),
    autoescape=False,
    keep_trailing_newline=True,
)


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

        html = EMAIL_TEMPLATES.get_template('confirmacao.html').render(
            nome_usuario=nome_usuario,
            titulo_livro=titulo_livro,
            data_devolucao=data_devolucao,
            cid_capa=cid_capa,
        )
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

        html = EMAIL_TEMPLATES.get_template('renovacao.html').render(
            nome_usuario=nome_usuario,
            titulo_livro=titulo_livro,
            nova_data_devolucao=nova_data_devolucao,
            cid_capa=cid_capa,
        )
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

        html = EMAIL_TEMPLATES.get_template('devolucao.html').render(
            nome_usuario=nome_usuario,
            titulo_livro=titulo_livro,
            data_devolucao_real=data_devolucao_real,
            cid_capa=cid_capa,
        )
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

        html = EMAIL_TEMPLATES.get_template('notificacao.html').render(
            nome_usuario=nome_usuario,
            titulo_livro=titulo_livro,
            status_texto=status_texto,
            data_devolucao=data_devolucao,
            cid_capa=cid_capa,
        )
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


def iniciar_verificacao_notificacoes(app):
    def _executar_periodicamente():
        while True:
            with app.app_context():
                verificar_e_enviar_notificacoes()
            time.sleep(1800)

    thread = threading.Thread(target=_executar_periodicamente, daemon=True)
    thread.start()
