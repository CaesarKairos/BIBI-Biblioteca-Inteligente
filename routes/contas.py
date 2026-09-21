from flask import Blueprint,request,jsonify,render_template,session,g,redirect
from werkzeug.exceptions import BadRequest,Forbidden
from database.database import db_manager
from services import contas_service as service
from utils.auth import local_only,admin_required

bp = Blueprint('contas',__name__)


def data():
    payload = request.get_json()
    if not isinstance(payload,dict):
        raise BadRequest('Envie um objeto JSON.')
    return payload


@bp.get('/api/acesso/csrf')
def csrf():
    return jsonify(csrf=session['csrf'])


@bp.get('/configuracao-inicial')
def setup():
    local_only()
    if service.configurado():
        return redirect('/acesso')
    return render_template('acesso.html',modo='setup')


@bp.post('/api/acesso/configurar')
def setup_api():
    local_only()
    if service.configurado():
        raise Forbidden('A configuração inicial já foi concluída.')
    service.limitar('setup',limite=10)
    return jsonify(service.configurar(data()))


@bp.get('/acesso')
def acesso():
    return render_template('acesso.html',modo='login')


@bp.post('/api/acesso/entrar')
def entrar():
    return jsonify(service.login(data()))


@bp.post('/api/acesso/recuperacao-email')
def recovery_email():
    from services.mensagens_service import pedir_recuperacao
    return jsonify(pedir_recuperacao(data()))


@bp.post('/api/contas/leitores/<int:leitor_id>/email')
@admin_required
def email_invite(leitor_id):
    from services.mensagens_service import enviar_codigo
    info=service.emitir_codigo(leitor_id,'ativacao','email')
    if not enviar_codigo(info,'ativação da conta'):
        raise BadRequest('Envio falhou ou remetente não configurado. Use um convite presencial.')
    return jsonify(mensagem='Convite aceito pelo SMTP; entrega e ativação ainda não confirmadas.')


@bp.post('/api/acesso/sair')
def sair():
    with db_manager.connection() as conn:
        conn.execute('DELETE FROM Sessoes WHERE hash=?',(service.digest(session.get('sid','')),))
        conn.commit()
    session.clear()
    return jsonify(status='ok')


@bp.post('/api/acesso/ativar')
def ativar():
    return jsonify(service.consumir_codigo(data(),'ativacao'))


@bp.post('/api/acesso/redefinir')
def redefinir():
    return jsonify(service.consumir_codigo(data(),'recuperacao'))


@bp.get('/recuperacao-local')
def offline_page():
    local_only()
    return render_template('acesso.html',modo='offline')


@bp.post('/api/acesso/recuperacao-local')
def offline():
    local_only()
    return jsonify(service.recuperar_offline(data()))


@bp.post('/api/contas/leitores/<int:leitor_id>/codigo')
@admin_required
def convite(leitor_id):
    payload = data()
    if payload.get('entrega','presencial') != 'presencial':
        raise BadRequest('Utilize a operação de envio por e-mail.')
    return jsonify(service.emitir_codigo(leitor_id,payload.get('finalidade','ativacao')))


@bp.delete('/api/contas/leitores/<int:leitor_id>/codigo')
@admin_required
def revogar(leitor_id):
    with db_manager.connection() as conn:
        conn.execute('UPDATE Codigos SET consumido=1 WHERE leitor_id=?',(leitor_id,))
        service.auditar(conn,'revogar_codigos',leitor_id)
        conn.commit()
    return jsonify(status='ok')


@bp.get('/api/contas/leitores/<int:leitor_id>/estado')
@admin_required
def estado(leitor_id):
    import time
    with db_manager.connection() as conn:
        account=conn.execute('SELECT ativa,email_verificado,ativacao FROM Contas WHERE leitor_id=?',(leitor_id,)).fetchone()
        code=conn.execute("SELECT entrega,expira,consumido,id FROM Codigos WHERE leitor_id=? AND finalidade='ativacao' ORDER BY id DESC LIMIT 1",(leitor_id,)).fetchone()
        if account:
            return jsonify(estado='conta ativa' if account[0] else 'conta bloqueada',email_verificado=bool(account[1]),entrega=account[2])
        state='sem conta' if not code or code[2] else 'convite pendente' if code[1]>int(time.time()) else 'convite expirado'
        sent=conn.execute("SELECT resultado FROM Auditoria WHERE acao='envio_codigo' AND recurso=? ORDER BY id DESC LIMIT 1",(str(code[3]),)).fetchone() if code else None
        return jsonify(estado=state,email_verificado=False,entrega=code[0] if code else None,envio=sent[0] if sent else None)


@bp.get('/api/contas')
@admin_required
def contas():
    with db_manager.connection() as conn:
        cur = conn.execute('SELECT id,leitor_id,nome,email,papel,ativa,email_verificado,ativacao FROM Contas ORDER BY nome,id')
        return jsonify([dict(zip([d[0] for d in cur.description],r)) for r in cur.fetchall()])


@bp.put('/api/contas/<int:conta_id>')
@admin_required
def alterar(conta_id):
    service.limitar('privilegios',str(g.conta['id']))
    return jsonify(service.alterar_acesso(conta_id,data()))
