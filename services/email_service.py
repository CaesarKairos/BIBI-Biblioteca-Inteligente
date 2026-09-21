from config import STATIC_DIR, TEMPLATE_DIR
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
import logging

logger = logging.getLogger(__name__)
_notification_lock = threading.Lock()


# Email rendering must also work in background threads, without Flask context.
# Escape user data while keeping the original email layout.
EMAIL_TEMPLATES = Environment(
    loader=FileSystemLoader(os.path.join(TEMPLATE_DIR, 'emails')),
    autoescape=True,
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
        logger.info("Envio de e-mail concluído ou indisponível conforme configuração")
        return False
    try:
        EMAIL_USER, EMAIL_PASSWORD = get_email_credenciais()
        if not EMAIL_USER or not EMAIL_PASSWORD:
            logger.info("Envio de e-mail concluído ou indisponível conforme configuração")
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

        logo_path = os.path.join(STATIC_DIR, "images", "icon.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                img = MIMEImage(img_file.read())
                img.add_header("Content-ID", "<logo_bibi>")
                msg.attach(img)

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)

        logger.info("Envio de e-mail concluído ou indisponível conforme configuração")
        return True
    except Exception as e:
        logger.exception("Falha no envio de e-mail")
        return False


def enviar_email_renovacao(destinatario, nome_usuario, titulo_livro, nova_data_devolucao, capa_url=None):
    if is_email_blocked():
        logger.info("Envio de e-mail concluído ou indisponível conforme configuração")
        return False
    try:
        EMAIL_USER, EMAIL_PASSWORD = get_email_credenciais()
        if not EMAIL_USER or not EMAIL_PASSWORD:
            logger.info("Envio de e-mail concluído ou indisponível conforme configuração")
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

        logo_path = os.path.join(STATIC_DIR, "images", "icon.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                img = MIMEImage(img_file.read())
                img.add_header("Content-ID", "<logo_bibi>")
                msg.attach(img)

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)

        logger.info("Envio de e-mail concluído ou indisponível conforme configuração")
        return True
    except Exception as e:
        logger.exception("Falha no envio de e-mail")
        return False


def enviar_email_devolucao(destinatario, nome_usuario, titulo_livro, data_devolucao_real, capa_url=None):
    if is_email_blocked():
        logger.info("Envio de e-mail concluído ou indisponível conforme configuração")
        return False
    try:
        EMAIL_USER, EMAIL_PASSWORD = get_email_credenciais()
        if not EMAIL_USER or not EMAIL_PASSWORD:
            logger.info("Envio de e-mail concluído ou indisponível conforme configuração")
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

        logo_path = os.path.join(STATIC_DIR, "images", "icon.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                img = MIMEImage(img_file.read())
                img.add_header("Content-ID", "<logo_bibi>")
                msg.attach(img)

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)

        logger.info("Envio de e-mail concluído ou indisponível conforme configuração")
        return True
    except Exception as e:
        logger.exception("Falha no envio de e-mail")
        return False


def enviar_email_notificacao(destinatario, nome_usuario, titulo_livro, data_devolucao, dias_faltantes, capa_url=None):
    if is_email_blocked():
        logger.info("Envio de e-mail concluído ou indisponível conforme configuração")
        return False
    try:
        EMAIL_USER, EMAIL_PASSWORD = get_email_credenciais()
        if not EMAIL_USER or not EMAIL_PASSWORD:
            logger.info("Envio de e-mail concluído ou indisponível conforme configuração")
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

        logo_path = os.path.join(STATIC_DIR, "images", "icon.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                img = MIMEImage(img_file.read())
                img.add_header("Content-ID", "<logo_bibi>")
                msg.attach(img)

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)

        logger.info("Envio de e-mail concluído ou indisponível conforme configuração")
        return True
    except Exception as e:
        logger.exception("Falha no envio de e-mail")
        return False


def atualizar_atrasos():
    with db_manager.connection() as conn:
        conn.execute("UPDATE Emprestimo SET status = 'Atrasado' WHERE status = 'Aprovado' AND data_devolucao IS NULL AND encerramento IS NULL AND date(data_vencimento) < ?", (get_brasilia_today().isoformat(),))
        conn.commit()


def verificar_e_enviar_notificacoes():
    """Uma rotina única: eventos internos persistentes e envio só a e-mails verificados."""
    if not _notification_lock.acquire(blocking=False):
        return
    try:
        from services.contas_service import configurado
        if not configurado():
            return
        from services.circulacao_service import processar_expiracoes,notificar
        from services.mensagens_service import processar_fila
        processar_expiracoes()
        atualizar_atrasos()
        with db_manager.connection() as conn:
            for id,leitor,prazo,nome in conn.execute("SELECT e.id,e.usuarios_id,e.data_vencimento,l.nome FROM Emprestimo e JOIN Livros l ON l.id=e.livros_id WHERE e.status IN ('Aprovado','Atrasado') AND e.encerramento IS NULL").fetchall():
                dias=(datetime.strptime(prazo,'%Y-%m-%d').date()-get_brasilia_today()).days
                if dias in (0,3) or dias<0:
                    notificar(conn,leitor,f'prazo:{id}:{prazo}:{"atraso" if dias<0 else dias}',f'{nome}: devolução prevista para {prazo}.')
            conn.commit()
        processar_fila()
    finally:
        _notification_lock.release()


def iniciar_verificacao_notificacoes(app):
    if app.extensions.get('notification_worker'):
        return app.extensions['notification_worker']
    def _executar_periodicamente():
        while True:
            try:
                with app.app_context():
                    verificar_e_enviar_notificacoes()
            except Exception:
                logger.exception('Falha na verificação periódica de notificações')
            time.sleep(1800)

    thread = threading.Thread(target=_executar_periodicamente, daemon=True)
    app.extensions['notification_worker'] = thread
    thread.start()
    return thread
