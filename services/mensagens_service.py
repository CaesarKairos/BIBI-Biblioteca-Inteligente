"""SMTP autenticado com TLS e fila durável de eventos sem códigos secretos."""
from email.message import EmailMessage
import json
import secrets
import smtplib
import ssl
import time
from flask import current_app,g
from werkzeug.exceptions import BadRequest
from werkzeug.security import check_password_hash
from database.database import db_manager
from services.contas_service import digest,email_normalizado,auditar,limitar


def smtp_config():
    with db_manager.connection() as conn:
        settings=dict(conn.execute('SELECT chave,valor FROM Configuracoes'))
    return {'host':settings.get('smtp_host','smtp.gmail.com'),'port':int(settings.get('smtp_port','587')),
            'email':settings.get('email_organizacao',''),'senha':current_app.extensions['secrets'].get('smtp_password','')}


def enviar(destinatario,assunto,corpo,html=None,capa=None):
    cfg=smtp_config()
    if not cfg['email'] or not cfg['senha']:
        return False
    msg=EmailMessage();msg['From']=cfg['email'];msg['To']=destinatario;msg['Subject']=assunto;msg.set_content(corpo)
    if html:
        msg.add_alternative(html,subtype='html')
        from pathlib import Path
        from config import STATIC_DIR
        logo=Path(STATIC_DIR)/'images'/'icon.png'
        if logo.exists():
            msg.get_payload()[-1].add_related(logo.read_bytes(),maintype='image',subtype='png',cid='<logo_bibi>')
        if capa:
            from services.image_service import get_book_cover_image_bytes
            content,extension=get_book_cover_image_bytes(capa)
            if content:
                msg.get_payload()[-1].add_related(content,maintype='image',subtype='jpeg' if extension=='jpg' else extension,cid='<capa_livro>')
    try:
        tls=ssl.create_default_context()
        if cfg['port']==465:
            server=smtplib.SMTP_SSL(cfg['host'],cfg['port'],timeout=15,context=tls)
        else:
            server=smtplib.SMTP(cfg['host'],cfg['port'],timeout=15)
        with server:
            if cfg['port']!=465:
                server.starttls(context=tls)
            server.login(cfg['email'],cfg['senha'])
            server.send_message(msg)
        return True
    except (OSError,smtplib.SMTPException):
        # Não registrar respostas SMTP que possam conter credenciais ou códigos.
        return False


def enviar_codigo(info,finalidade):
    with db_manager.connection() as conn:
        row=conn.execute("SELECT valor FROM Configuracoes WHERE chave='endereco_rede'").fetchone()
    endereco=row[0] if row and row[0] else 'o endereço informado pela biblioteca'
    accepted=enviar(info['email'],'BIBI — '+finalidade,
        f"Seu código de {finalidade}: {info['codigo']}\nVálido por {info.get('validade_horas',24)} horas, uma única vez.\nAcesse {endereco} na rede escolar, enquanto o servidor da biblioteca estiver funcionando. Não compartilhe este código.")
    with db_manager.connection() as conn:
        if not accepted:
            conn.execute('UPDATE Codigos SET consumido=1 WHERE id=?',(info['id'],))
        auditar(conn,'envio_codigo',info['id'],resultado='aceito_smtp' if accepted else 'falha')
        conn.commit()
    return accepted


def criar_codigo_conta(conta,email,finalidade):
    code=''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(16))
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('UPDATE Codigos SET consumido=1 WHERE conta_id=? AND finalidade=?',(conta,finalidade))
        cur=conn.execute("INSERT INTO Codigos(conta_id,email,finalidade,entrega,hash,expira) VALUES (?,?,?,'email',?,?)",(conta,email,finalidade,digest(code),int(time.time())+3600))
        conn.commit()
    return {'id':cur.lastrowid,'email':email,'codigo':code,'validade_horas':1}


def pedir_recuperacao(data):
    email=str(data.get('email','')).strip().casefold();limitar('recuperacao_email',email,limite=4,janela=3600)
    with db_manager.connection() as conn:
        row=conn.execute('SELECT id FROM Contas WHERE email=? AND ativa=1 AND email_verificado=1',(email,)).fetchone()
    if row:
        enviar_codigo(criar_codigo_conta(row[0],email,'recuperacao'),'recuperação de senha')
    return {'mensagem':'Se houver uma conta elegível e envio disponível, você receberá um código. Se o e-mail não foi verificado ou a mensagem não chegar, procure o bibliotecário.'}


def pedir_verificacao(data):
    limitar('verificar_email',str(g.conta['id']),limite=4,janela=3600)
    email=email_normalizado(data.get('email'))
    with db_manager.connection() as conn:
        row=conn.execute('SELECT senha_hash FROM Contas WHERE id=?',(g.conta['id'],)).fetchone()
        if not check_password_hash(row[0],str(data.get('senha_atual',''))):
            raise BadRequest('Confirme sua senha atual.')
        if conn.execute('SELECT 1 FROM Contas WHERE email=? AND id!=?',(email,g.conta['id'])).fetchone():
            raise BadRequest('Não foi possível utilizar este endereço.')
    info=criar_codigo_conta(g.conta['id'],email,'verificacao')
    if not enviar_codigo(info,'verificação de e-mail'):
        raise BadRequest('Envio indisponível ou recusado. A conta continua funcionando. Procure a biblioteca.')
    return {'mensagem':'Mensagem aceita pelo SMTP. Isso não garante chegada à caixa de entrada. Confirme o código recebido.'}


def confirmar_email(data):
    email=email_normalizado(data.get('email'));limitar('verificar_codigo',str(g.conta['id']))
    code=str(data.get('codigo','')).replace('-','').replace(' ','').upper()
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute("SELECT id FROM Codigos WHERE conta_id=? AND finalidade='verificacao' AND email=? AND hash=? AND consumido=0 AND expira>?",(g.conta['id'],email,digest(code),int(time.time()))).fetchone()
        if not row:
            raise BadRequest('Código inválido ou expirado.')
        if g.conta['leitor_id']:
            conn.execute('UPDATE Usuarios SET email=? WHERE id=?',(email,g.conta['leitor_id']))
        conn.execute('UPDATE Contas SET email=?,email_verificado=1,versao_sessao=versao_sessao+1 WHERE id=?',(email,g.conta['id']))
        conn.execute('UPDATE Codigos SET consumido=1 WHERE conta_id=?',(g.conta['id'],))
        auditar(conn,'verificar_email',g.conta['id'])
        conn.commit()
    return {'status':'ok'}


def processar_fila():
    cfg=smtp_config()
    if not cfg['email'] or not cfg['senha']:
        return
    with db_manager.connection() as conn:
        if conn.execute("SELECT 1 FROM Configuracoes WHERE chave='bloquear_email' AND valor='true'").fetchone():
            return
        # Um envio interrompido tem resultado incerto: não reenviar automaticamente.
        conn.execute("UPDATE FilaEmail SET estado='incerto' WHERE estado='enviando' AND atualizada_em<?",(int(time.time())-300,))
        conn.execute("""INSERT OR IGNORE INTO FilaEmail(evento,destinatario,assunto,corpo)
            SELECT n.evento,c.email,'BIBI — Biblioteca',n.mensagem FROM Notificacoes n JOIN Contas c ON c.leitor_id=n.leitor_id
            WHERE c.email_verificado=1 AND c.ativa=1""")
        conn.commit()
    for _ in range(20):
        with db_manager.connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row=conn.execute("SELECT id,destinatario,assunto,corpo,evento FROM FilaEmail WHERE estado IN ('pendente','falha') AND tentativas<3 AND proxima<=? ORDER BY id LIMIT 1",(int(time.time()),)).fetchone()
            if not row:
                break
            conn.execute("UPDATE FilaEmail SET estado='enviando',tentativas=tentativas+1,atualizada_em=? WHERE id=?",(int(time.time()),row[0]));conn.commit()
        # Conferir novamente verificação: troca de e-mail/bloqueio pode ocorrer depois da fila.
        with db_manager.connection() as conn:
            allowed=conn.execute('SELECT 1 FROM Contas c JOIN Notificacoes n ON n.leitor_id=c.leitor_id WHERE c.email=? AND c.email_verificado=1 AND c.ativa=1 AND n.evento=?',(row[1],row[4])).fetchone()
        html,capa=email_evento(row[4])
        accepted=bool(allowed) and enviar(*row[1:4],html=html,capa=capa)
        with db_manager.connection() as conn:
            conn.execute('UPDATE FilaEmail SET estado=?,proxima=?,atualizada_em=? WHERE id=?',('aceito' if accepted else 'falha',int(time.time())+1800,int(time.time()),row[0]));conn.commit()


def email_evento(evento):
    """Mantém os quatro templates editoriais existentes nas mensagens de circulação."""
    parts=evento.split(':')
    templates={'emprestimo':'confirmacao','devolucao':'devolucao','renovacao':'renovacao','prazo':'notificacao'}
    if parts[0] not in templates or len(parts)<2 or not parts[1].isdigit():
        return None,None
    with db_manager.connection() as conn:
        row=conn.execute('SELECT u.nome,l.nome,l.capa_url,e.data_vencimento,e.data_devolucao FROM Emprestimo e JOIN Usuarios u ON u.id=e.usuarios_id JOIN Livros l ON l.id=e.livros_id WHERE e.id=?',(int(parts[1]),)).fetchone()
    if not row:
        return None,None
    from services.email_service import EMAIL_TEMPLATES
    from datetime import date
    due=date.fromisoformat(row[3]).strftime('%d/%m/%Y')
    html=EMAIL_TEMPLATES.get_template(templates[parts[0]]+'.html').render(nome_usuario=row[0],titulo_livro=row[1],data_devolucao=due,data_devolucao_real=row[4],nova_data_devolucao=due,status_texto='Prazo de devolução',cid_capa='cid:capa_livro' if row[2] else None)
    return html,row[2]
