"""Adaptacao HTTP e registro explicito dos Blueprints."""
from flask import jsonify

def json_response(result):
    if isinstance(result, tuple):
        payload, status = result
        return jsonify(payload), status
    return jsonify(result)

def register_blueprints(app):
    from routes import pages, admin, livros, leitores, emprestimos, agendamentos, configuracoes
    for module in (pages, admin, configuracoes, livros, leitores, emprestimos, agendamentos):
        app.register_blueprint(module.bp)
