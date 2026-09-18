from flask import Blueprint
from flask import request
from routes import json_response
from services import leitores_service
from utils.auth import admin_required


bp = Blueprint('leitores', __name__)


@bp.route('/api/leitores', methods=['GET'])
@admin_required
def api_leitores():
    return json_response(leitores_service.api_leitores())


@bp.route('/api/leitores/buscar', methods=['GET'])
@admin_required
def buscar_leitor():
    return json_response(leitores_service.buscar_leitor(query=request.args))


@bp.route('/api/leitores', methods=['POST'])
@admin_required
def criar_leitor():
    return json_response(leitores_service.criar_leitor(data=request.json))


@bp.route('/api/leitores/<int:id>', methods=['PUT'])
@admin_required
def editar_leitor(id):
    return json_response(leitores_service.editar_leitor(id=id, data=request.json))


@bp.route('/api/leitores/<int:id>', methods=['DELETE'])
@admin_required
def excluir_leitor(id):
    return json_response(leitores_service.excluir_leitor(id=id))
