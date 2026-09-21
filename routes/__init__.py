"""Adaptacao HTTP e registro explicito dos Blueprints."""
from flask import jsonify, request
from werkzeug.exceptions import HTTPException
import sqlite3

def json_response(result):
    if isinstance(result, tuple):
        payload, status = result
        return jsonify(payload), status
    return jsonify(result)

def register_blueprints(app):
    from routes import pages, admin, livros, leitores, emprestimos, agendamentos, configuracoes, contas, perfil, gestao
    for module in (pages, admin, configuracoes, livros, leitores, emprestimos, agendamentos, contas, perfil, gestao):
        app.register_blueprint(module.bp)


def register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def http_error(error):
        if not request.path.startswith('/api/'):
            return error
        messages = {400: 'Dados da solicitação inválidos.', 403: 'Acesso negado.',
                    404: 'Recurso não encontrado.', 413: 'Arquivo maior que o limite permitido.',
                    415: 'Envie os dados no formato JSON.'}
        return jsonify(erro=error.description or messages.get(error.code)), error.code

    @app.errorhandler(sqlite3.IntegrityError)
    def integrity_error(error):
        app.logger.warning('Conflito de integridade em %s', request.path, exc_info=True)
        return jsonify(erro='Os dados informados conflitam com um registro existente ou são inválidos.'), 409

    @app.errorhandler(Exception)
    def unexpected_error(error):
        app.logger.error('Falha em %s', request.path, exc_info=True)
        if request.path.startswith('/api/'):
            return jsonify(erro='Não foi possível concluir a operação. Tente novamente.'), 500
        return 'Não foi possível carregar a página.', 500
