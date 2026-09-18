from flask import Blueprint
from flask import request
from routes import json_response
from services import agendamentos_service
from utils.auth import admin_required


bp = Blueprint('agendamentos', __name__)


@bp.route('/api/agendamentos', methods=['GET'])
def api_agendamentos():
    return json_response(agendamentos_service.api_agendamentos(query=request.args))


@bp.route('/api/agendamentos/datas-com-agendamentos', methods=['GET'])
def datas_com_agendamentos():
    return json_response(agendamentos_service.datas_com_agendamentos())


@bp.route('/api/agendamentos/passados', methods=['GET'])
def agendamentos_passados():
    return json_response(agendamentos_service.agendamentos_passados())


@bp.route('/api/agendamentos', methods=['POST'])
@admin_required
def criar_agendamento():
    return json_response(agendamentos_service.criar_agendamento(data=request.json))


@bp.route('/api/agendamentos/<int:id>', methods=['DELETE'])
@admin_required
def excluir_agendamento(id):
    return json_response(agendamentos_service.excluir_agendamento(id=id))
