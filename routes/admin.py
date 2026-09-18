from flask import Blueprint
from flask import jsonify
from utils.auth import is_admin


bp = Blueprint('admin', __name__)


@bp.route('/api/admin/status', methods=['GET'])
def admin_status():
    """Endpoint para o frontend saber se o usuário é administrador (localhost)."""
    return jsonify({"admin": is_admin()})
