from flask import Blueprint
from flask import request
from routes import json_response
from services import configuracoes_service
from utils.auth import admin_required


bp = Blueprint('configuracoes', __name__)


@bp.before_request
def confirm_security_change():
    if request.path in ('/api/config/exigir_senha_emprestimo/set','/api/config/exigir_senha_agendamento/set'):
        from utils.auth import verificar_senha_admin
        from werkzeug.exceptions import Forbidden
        if not verificar_senha_admin(request.get_json().get('senha_atual')):
            raise Forbidden('Confirme sua senha atual para modificar a segurança.')


@bp.route('/api/config/cadastro', methods=['GET','PUT'])
@admin_required
def cadastro():
    import json
    from database.database import db_manager
    from flask import jsonify
    from werkzeug.exceptions import BadRequest
    from services.contas_service import auditar
    keys={'campoDescricaoVisivel','campoTemasVisivel','campoAnoVisivel','campoCategoriaVisivel',
          'bloquearExcluirLivro','campoNumeroUsuario','mostrarColunaAula'}
    with db_manager.connection() as conn:
        if request.method=='PUT':
            data=request.get_json()
            if not isinstance(data,dict) or set(data)-keys or any(type(v) is not bool for v in data.values()):
                raise BadRequest('Preferências de cadastro inválidas.')
            conn.execute('BEGIN IMMEDIATE')
            previous=conn.execute("SELECT valor FROM Configuracoes WHERE chave='campos_cadastro'").fetchone()
            merged=(json.loads(previous[0]) if previous else {}) | data
            conn.execute("INSERT OR REPLACE INTO Configuracoes VALUES ('campos_cadastro',?)",(json.dumps(merged),))
            auditar(conn,'campos_cadastro','biblioteca');conn.commit()
        row=conn.execute("SELECT valor FROM Configuracoes WHERE chave='campos_cadastro'").fetchone()
        return jsonify(json.loads(row[0]) if row else {})


@bp.route('/api/config/senha/status', methods=['GET'])
@admin_required
def senha_status():
    return json_response(configuracoes_service.senha_status())


@bp.route('/api/config/senha/definir', methods=['POST'])
@admin_required
def definir_senha():
    return json_response(configuracoes_service.definir_senha(data=request.json))


@bp.route('/api/config/senha/verificar', methods=['POST'])
def verificar_senha():
    return json_response(configuracoes_service.verificar_senha(data=request.json))


@bp.route('/api/config/bloquear_email/status', methods=['GET'])
@admin_required
def bloquear_email_status():
    return json_response(configuracoes_service.bloquear_email_status())


@bp.route('/api/config/bloquear_email/set', methods=['POST'])
@admin_required
def set_bloquear_email():
    return json_response(configuracoes_service.set_bloquear_email(data=request.json))


@bp.route('/api/config/exigir_senha_emprestimo/status', methods=['GET'])
@admin_required
def exigir_senha_emprestimo_status():
    return json_response(configuracoes_service.exigir_senha_emprestimo_status())


@bp.route('/api/config/exigir_senha_emprestimo/set', methods=['POST'])
@admin_required
def set_exigir_senha_emprestimo():
    return json_response(configuracoes_service.set_exigir_senha_emprestimo(data=request.json))


@bp.route('/api/config/obrigar_localizacao_livro/status', methods=['GET'])
@admin_required
def obrigar_localizacao_livro_status():
    return json_response(configuracoes_service.obrigar_localizacao_livro_status())


@bp.route('/api/config/obrigar_localizacao_livro/set', methods=['POST'])
@admin_required
def set_obrigar_localizacao_livro():
    return json_response(configuracoes_service.set_obrigar_localizacao_livro(data=request.json))


@bp.route('/api/config/exigir_senha_agendamento/status', methods=['GET'])
@admin_required
def exigir_senha_agendamento_status():
    return json_response(configuracoes_service.exigir_senha_agendamento_status())


@bp.route('/api/config/exigir_senha_agendamento/set', methods=['POST'])
@admin_required
def set_exigir_senha_agendamento():
    return json_response(configuracoes_service.set_exigir_senha_agendamento(data=request.json))


@bp.route('/api/config/bloquear_excluir_agendamento/status', methods=['GET'])
@admin_required
def bloquear_excluir_agendamento_status():
    return json_response(configuracoes_service.bloquear_excluir_agendamento_status())


@bp.route('/api/config/bloquear_excluir_agendamento/set', methods=['POST'])
@admin_required
def set_bloquear_excluir_agendamento():
    return json_response(configuracoes_service.set_bloquear_excluir_agendamento(data=request.json))


@bp.route('/api/config/quantidade_aulas/status', methods=['GET'])
def quantidade_aulas_status():
    return json_response(configuracoes_service.quantidade_aulas_status())


@bp.route('/api/config/quantidade_aulas/set', methods=['POST'])
@admin_required
def set_quantidade_aulas_route():
    return json_response(configuracoes_service.set_quantidade_aulas_route(data=request.json))


@bp.route('/api/config/email/status', methods=['GET'])
@admin_required
def config_email_status():
    return json_response(configuracoes_service.config_email_status())


@bp.route('/api/config/email/set', methods=['POST'])
@admin_required
def set_config_email():
    return json_response(configuracoes_service.set_config_email(data=request.json))
