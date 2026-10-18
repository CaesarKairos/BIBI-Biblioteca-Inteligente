"""Autorizacao por conta e sessao."""
from functools import wraps
from urllib.parse import urlsplit
import secrets
from flask import g, request, session, jsonify, redirect, current_app
from werkzeug.exceptions import Forbidden, BadRequest,RequestEntityTooLarge
from database.database import db_manager,operation_lock,maintenance_lock,external_gate


def is_admin():
    return bool(getattr(g,'conta',None) and g.conta['papel'] == 'bibliotecario')


def admin_required(f):
    @wraps(f)
    def decorated(*args,**kwargs):
        if not is_admin():
            return jsonify(erro='Acesso permitido apenas a bibliotecários autenticados.'),403
        return f(*args,**kwargs)
    return decorated


def verificar_senha_admin(senha):
    from werkzeug.security import check_password_hash
    from services.contas_service import limitar
    if not is_admin() or not isinstance(senha,str) or len(senha)>128:
        return False
    with db_manager.connection() as conn:
        row=conn.execute('SELECT senha_hash FROM Contas WHERE id=?',(g.conta['id'],)).fetchone()
        return bool(row and check_password_hash(row[0],senha))


def local_only():
    if request.remote_addr not in ('127.0.0.1','::1') or urlsplit(request.host_url).hostname not in ('127.0.0.1','::1','localhost'):
        raise Forbidden('Esta operação só pode ser feita no computador da biblioteca.')


def install_security(app):
    from services.contas_service import conta_atual, configurado

    @app.before_request
    def guard():
        if request.path in ('/api/gestao/restaurar','/api/ia/modelos','/api/ia/testar','/api/ia/insights','/api/minha-conta/ia/chat'):
            g.external_restore=request.path=='/api/gestao/restaurar'
            external_gate.acquire(g.external_restore)
            g.external_gate_locked=True
        if request.path=='/api/gestao/restaurar':
            # Mesma ordem do worker: manutenção antes de conexões/operações.
            maintenance_lock.acquire()
            g.maintenance_locked=True
        operation_lock.acquire()
        g.operation_locked = True
        g.conta = None
        if request.path!='/api/gestao/restaurar' and request.content_length and request.content_length>16*1024*1024:
            raise RequestEntityTooLarge()
        if request.is_json and request.method not in ('GET','HEAD','OPTIONS') and not isinstance(request.get_json(),dict):
            raise BadRequest('Envie os dados em um objeto JSON.')
        hostname = urlsplit(request.host_url).hostname
        allowed = set(current_app.config['ALLOWED_HOSTS'])
        network=current_app.extensions.get('network_runtime')
        if network:
            allowed.update(network.hosts)
        if request.environ.get('bibi.lan'):
            from services.rede_service import private_peer
            if not private_peer(request.remote_addr):
                raise Forbidden('Este servidor atende somente à rede local da biblioteca.')
        with db_manager.connection() as conn:
            row = conn.execute("SELECT valor FROM Configuracoes WHERE chave='endereco_rede'").fetchone()
            if row and row[0]:
                allowed.add(urlsplit(row[0]).hostname)
        if hostname not in allowed:
            raise BadRequest('Endereço de acesso não configurado.')
        if request.remote_addr not in ('127.0.0.1','::1') and not request.is_secure:
            raise Forbidden('Use o endereço HTTPS exibido em Configurações → Biblioteca. Credenciais não são aceitas por HTTP na rede.')
        if request.method not in ('GET','HEAD','OPTIONS'):
            origin = request.headers.get('Origin')
            if origin and origin.rstrip('/') != request.host_url.rstrip('/'):
                raise Forbidden('Origem da solicitação inválida.')
            if request.headers.get('Sec-Fetch-Site') == 'cross-site':
                raise Forbidden('Origem da solicitação inválida.')
            csrf = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            if not csrf or not secrets.compare_digest(str(csrf),session.get('csrf','')):
                raise Forbidden('Sessão do formulário expirou. Atualize a página.')
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(32)
        static = request.path.startswith('/static/')
        auth = request.blueprint == 'contas' and request.path in ('/acesso','/configuracao-inicial','/recuperacao-local') or request.path.startswith('/api/acesso/')
        if not configurado():
            if static:
                return
            local_only()
            if request.endpoint not in ('contas.setup','contas.setup_api','contas.csrf','pages.instituicao'):
                if request.path.startswith('/api/'):
                    return jsonify(erro='Conclua a configuração inicial no computador da biblioteca.'),503
                return redirect('/configuracao-inicial')
        g.conta = conta_atual()
        if static or auth or request.path in ('/','/api/hero-image','/instituicao'):
            return
        if not g.conta:
            if request.path.startswith('/api/'):
                return jsonify(erro='Entre na sua conta para continuar.'),401
            return redirect('/acesso')
        if request.method not in ('GET','HEAD','OPTIONS') and is_admin():
            payload=request.get_json(silent=True) or request.form
            if payload.get('senha') or payload.get('senha_atual'):
                from services.contas_service import limitar
                limitar('confirmar-senha',str(g.conta['id']),limite=12)
        if request.method == 'GET' and request.path in ('/app','/perfil','/configuracoes') and not g.conta['onboarding_concluido_em']:
            return redirect('/boas-vindas')
        reader_allowed = request.path.startswith('/api/minha-conta') or request.path in ('/perfil','/boas-vindas','/configuracoes')
        reader_allowed |= request.method == 'GET' and request.path in ('/app','/api/livros','/api/admin/status','/api/config/quantidade_aulas/status')
        reader_allowed |= request.method == 'GET' and request.endpoint=='livros.detalhe_livro'
        reader_allowed |= request.method == 'GET' and request.path.startswith(('/uploadedcovers/','/externalcovers/'))
        if not is_admin() and not reader_allowed:
            return jsonify(erro='Acesso permitido apenas a bibliotecários.'),403

    @app.context_processor
    def security_context():
        return {'csrf_token':session.get('csrf',''),'conta':getattr(g,'conta',None)}

    @app.after_request
    def headers(response):
        if request.method not in ('GET','HEAD','OPTIONS') and request.blueprint in ('configuracoes','agendamentos','admin') and is_admin():
            from services.contas_service import auditar
            with db_manager.connection() as conn:
                auditar(conn,'administracao_legada',request.path,resultado=str(response.status_code))
                conn.commit()
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Referrer-Policy'] = 'same-origin'
        if not request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.teardown_request
    def release(error):
        if getattr(g,'operation_locked',False):
            g.operation_locked=False
            operation_lock.release()
        if getattr(g,'maintenance_locked',False):
            g.maintenance_locked=False
            maintenance_lock.release()
        if getattr(g,'external_gate_locked',False):
            g.external_gate_locked=False
            external_gate.release(g.external_restore)
