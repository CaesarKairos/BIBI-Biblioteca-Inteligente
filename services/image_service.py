import logging

logger = logging.getLogger(__name__)

from config import ALLOWED_EXTENSIONS
from config import STATIC_DIR, EXTERNAL_FOLDER
from config import HERO_FOLDER
from config import UPLOAD_FOLDER
from werkzeug.utils import secure_filename
import os
import random
import requests
import uuid
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit
import warnings
from PIL import Image, UnidentifiedImageError


def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def download_image_from_url(url, timeout=10):
    try:
        if urlsplit(url).scheme not in ('http', 'https'):
            return None, None
        with requests.get(url, timeout=timeout, stream=True) as response:
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_content(65536):
                data.extend(chunk)
                if len(data) > MAX_IMAGE_BYTES:
                    raise ValueError('Imagem externa excede 16 MB.')
            content = bytes(data)
            return content, validate_image(content)
    except (requests.RequestException, ValueError):
        logger.warning('Não foi possível obter uma capa externa válida', exc_info=True)
        return None, None


def get_book_cover_image_bytes(cover_url):
    if not cover_url:
        return None, None
    if cover_url.startswith(('http://', 'https://')):
        return download_image_from_url(cover_url)
    roots = {'/uploadedcovers/': UPLOAD_FOLDER, '/externalcovers/': EXTERNAL_FOLDER, '/static/': STATIC_DIR}
    for prefix, directory in roots.items():
        if cover_url.startswith(prefix):
            root = Path(directory).resolve()
            path = (root / urlsplit(cover_url).path[len(prefix):]).resolve()
            if os.path.commonpath([str(root), str(path)]) != str(root):
                return None, None
            try:
                with path.open('rb') as file:
                    data = file.read(MAX_IMAGE_BYTES + 1)
                return data, validate_image(data)
            except (OSError, ValueError):
                logger.warning('Capa local indisponível ou inválida', exc_info=True)
                return None, None
    return None, None


def hero_image():
    hero_dir = HERO_FOLDER
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
    images = []
    if os.path.exists(hero_dir):
        for f in os.listdir(hero_dir):
            if f.lower().endswith(image_extensions):
                images.append(f)
    if not images:
        fallback = 'hero.jpg'
        if not os.path.exists(os.path.join(hero_dir, fallback)):
            try:
                from PIL import Image, ImageDraw
                img = Image.new('RGB', (1200, 600), color=(100, 80, 70))
                draw = ImageDraw.Draw(img)
                draw.text((500, 280), "BIBI", fill=(255,255,255))
                img.save(os.path.join(hero_dir, fallback))
            except OSError:
                logger.exception("Falha ao criar imagem hero padrão")
        images = [fallback] if os.path.exists(os.path.join(hero_dir, fallback)) else []
    if images:
        chosen = random.choice(images)
        return {"url": f"/static/images/hero/{chosen}"}
    return {"url": "/static/images/hero/hero.jpg"}, 200


def upload_imagem(files, upload_folder):
    if 'file' not in files:
        return {"erro": "Nenhum arquivo enviado"}, 400
    file = files['file']
    if not file.filename:
        return {"erro": "Nome de arquivo vazio"}, 400
    if not allowed_file(file.filename):
        return {"erro": "Tipo de arquivo não permitido"}, 400
    data = file.read(MAX_IMAGE_BYTES + 1)
    try:
        extension = validate_image(data)
    except ValueError as error:
        return {"erro": str(error)}, 400
    name = secure_filename(file.filename)
    stem = name.rsplit('.', 1)[0] or 'capa'
    filename = f'{uuid.uuid4()}_{stem}.{extension}'
    with open(os.path.join(upload_folder, filename), 'wb') as output:
        output.write(data)
    return {"url": f"/uploadedcovers/{filename}"}


MAX_IMAGE_BYTES = 16 * 1024 * 1024


def validate_image(data):
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise ValueError('A imagem está vazia ou excede o limite de 16 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                image_format = image.format
                if image_format not in {'PNG', 'JPEG', 'GIF', 'WEBP'}:
                    raise ValueError('Formato de imagem não permitido.')
                image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ValueError('O arquivo não contém uma imagem válida.') from error
    return {'JPEG': 'jpg', 'PNG': 'png', 'GIF': 'gif', 'WEBP': 'webp'}[image_format]
