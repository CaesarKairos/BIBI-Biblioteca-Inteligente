from config import EXTERNAL_FOLDER
from config import UPLOAD_FOLDER
from flask import Blueprint
from flask import current_app
from flask import request
from flask import send_from_directory
from routes import json_response
from services import image_service
from services import livros_service
from utils.auth import admin_required
from utils.auth import is_admin


bp = Blueprint('livros', __name__)


@bp.route('/api/livros', methods=['GET', 'POST'])
def api_livros():
    if request.method=='GET' and request.args.get('paginado')=='1':
        from services.catalogo_service import search
        return json_response(search(request.args))
    return json_response(livros_service.api_livros(admin=is_admin(), data=request.json if request.method == 'POST' and is_admin() else None, method=request.method))


@bp.get('/api/livros/<int:id>')
def detalhe_livro(id):
    from services.catalogo_service import detail
    return json_response(detail(id))


@bp.route('/api/upload', methods=['POST'])
@admin_required
def upload_imagem():
    return json_response(image_service.upload_imagem(files=request.files, upload_folder=current_app.config['UPLOAD_FOLDER']))


@bp.route('/uploadedcovers/<filename>', methods=['GET'])
def uploaded_file(filename):
    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        filename
    )


@bp.route('/externalcovers/<filename>', methods=['GET'])
def external_file(filename):
    return send_from_directory(
        __import__('os').path.join(current_app.config['DATA_DIR'], 'externalcovers'),
        filename
    )


@bp.route('/api/livros/<int:id>', methods=['PUT'])
@admin_required
def editar_livro(id):
    return json_response(livros_service.editar_livro(id=id, data=request.json))


@bp.route('/api/livros/<int:id>', methods=['DELETE'])
@admin_required
def excluir_livro(id):
    return json_response(livros_service.excluir_livro(id=id))
