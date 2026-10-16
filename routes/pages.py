from config import STATIC_DIR
from flask import Blueprint
from flask import render_template
from flask import send_from_directory
from routes import json_response
from services import image_service
from services.configuracoes_service import get_quantidade_aulas
from utils.auth import is_admin
import os


bp = Blueprint('pages', __name__)


@bp.get('/instituicao')
def instituicao():
    from database.database import db_manager
    with db_manager.connection() as conn:
        textos=dict(conn.execute("SELECT chave,valor FROM Configuracoes WHERE chave IN ('biblioteca_nome','termos_uso','aviso_privacidade')"))
    from services.termos_service import TERMOS, PRIVACIDADE
    textos.setdefault('termos_uso',TERMOS)
    textos.setdefault('aviso_privacidade',PRIVACIDADE)
    return render_template('instituicao.html',textos=textos)


@bp.route('/', methods=['GET'])
def landing():
    return render_template('index.html')


@bp.route('/app', methods=['GET'])
def app_principal():
    return render_template('app.html', admin=is_admin(), quantidade_aulas=get_quantidade_aulas())


@bp.route('/static/images/<path:filename>', methods=['GET'])
def serve_images(filename):
    return send_from_directory(
        os.path.join(STATIC_DIR, 'images'),
        filename
    )


@bp.route('/api/hero-image', methods=['GET'])
def hero_image():
    return json_response(image_service.hero_image())


@bp.get('/configuracoes')
def settings_page():
    from database.database import db_manager
    sobre={'versao':'2.0-dev'}
    if is_admin():
        with db_manager.connection() as conn:
            values=dict(conn.execute('SELECT chave,valor FROM Configuracoes'))
            schema=conn.execute('SELECT MAX(versao) FROM Migracoes').fetchone()[0]
            sobre['migracoes']=[r[0] for r in conn.execute('SELECT versao FROM Migracoes ORDER BY versao')]
            sobre['integridade']=conn.execute('PRAGMA quick_check').fetchone()[0]
        from pathlib import Path
        from flask import current_app
        backups=list((Path(current_app.config['DATA_DIR'])/'backups').glob('*.zip'))
        sobre['ultimo_backup']=max(backups,key=lambda p:p.stat().st_mtime).name if backups else None
        sobre.update(nome=values.get('biblioteca_nome','BIBI'),criada=values.get('instalacao_criada_em'),estimada=values.get('instalacao_data_estimada')=='true',schema=schema)
    return render_template('configuracoes.html',ativo='configuracoes',sobre=sobre)
