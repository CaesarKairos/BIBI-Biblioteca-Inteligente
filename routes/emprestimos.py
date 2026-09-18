from flask import Blueprint
from flask import request
from routes import json_response
from services import emprestimos_service
from utils.auth import admin_required


bp = Blueprint('emprestimos', __name__)


@bp.route('/api/emprestimos', methods=['POST'])
@admin_required
def realizar_emprestimo():
    return json_response(emprestimos_service.realizar_emprestimo(data=request.json))


@bp.route('/api/emprestimos/ativos/count', methods=['GET'])
@admin_required
def contar_emprestimos_ativos():
    return json_response(emprestimos_service.contar_emprestimos_ativos())


@bp.route('/api/emprestimos/ativos', methods=['GET'])
@admin_required
def listar_emprestimos_ativos():
    return json_response(emprestimos_service.listar_emprestimos_ativos())


@bp.route('/api/emprestimos/todos', methods=['GET'])
@admin_required
def listar_todos_emprestimos():
    return json_response(emprestimos_service.listar_todos_emprestimos())


@bp.route('/api/emprestimos/devolvidos', methods=['GET'])
@admin_required
def listar_emprestimos_devolvidos():
    return json_response(emprestimos_service.listar_emprestimos_devolvidos())


@bp.route('/api/emprestimos/devolucoes-hoje', methods=['GET'])
@admin_required
def listar_devolucoes_hoje():
    return json_response(emprestimos_service.listar_devolucoes_hoje())


@bp.route('/api/emprestimos/atrasos', methods=['GET'])
@admin_required
def listar_atrasos():
    return json_response(emprestimos_service.listar_atrasos())


@bp.route('/api/emprestimos/<int:id>/devolver', methods=['POST'])
@admin_required
def devolver_emprestimo(id):
    return json_response(emprestimos_service.devolver_emprestimo(id=id))


@bp.route('/api/emprestimos/<int:id>/renovar', methods=['POST'])
@admin_required
def renovar_emprestimo(id):
    return json_response(emprestimos_service.renovar_emprestimo(id=id))


@bp.route('/api/emprestimos/mais-emprestados', methods=['GET'])
def listar_mais_emprestados():
    return json_response(emprestimos_service.listar_mais_emprestados())


@bp.route('/api/emprestimos/ativos-por-genero', methods=['GET'])
def listar_ativos_por_genero():
    return json_response(emprestimos_service.listar_ativos_por_genero())


@bp.route('/api/emprestimos/historico-por-genero', methods=['GET'])
def listar_historico_por_genero():
    return json_response(emprestimos_service.listar_historico_por_genero())


@bp.route('/api/emprestimos/ranking-leitores', methods=['GET'])
def listar_ranking_leitores():
    return json_response(emprestimos_service.listar_ranking_leitores())


@bp.route('/api/livros/adormecidos', methods=['GET'])
def listar_livros_adormecidos():
    return json_response(emprestimos_service.listar_livros_adormecidos())
