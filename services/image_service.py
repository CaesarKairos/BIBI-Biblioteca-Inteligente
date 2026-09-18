from config import ALLOWED_EXTENSIONS
from config import BASE_DIR
from config import HERO_FOLDER
from config import UPLOAD_FOLDER
from werkzeug.utils import secure_filename
import os
import random
import requests
import uuid


def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def download_image_from_url(url, timeout=10):
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            ext = 'jpg'
            if 'png' in content_type:
                ext = 'png'
            elif 'gif' in content_type:
                ext = 'gif'
            elif 'webp' in content_type:
                ext = 'webp'
            else:
                url_ext = url.split('.')[-1].split('?')[0].lower()
                if url_ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    ext = url_ext
            return response.content, ext
    except Exception as e:
        print(f"Erro ao baixar imagem para e-mail: {e}")
    return None, None


def get_book_cover_image_bytes(cover_url):
    if not cover_url:
        return None, None

    if cover_url.startswith('/uploadedcovers/'):
        filename = cover_url.split('/')[-1]
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                return f.read(), file_path.split('.')[-1].lower()

    elif cover_url.startswith('/static/'):
        file_path = os.path.join(BASE_DIR, cover_url[1:])

        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                return f.read(), file_path.split('.')[-1].lower()

    elif cover_url.startswith('http://') or cover_url.startswith('https://'):
        return download_image_from_url(cover_url)

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
            except:
                pass
        images = [fallback] if os.path.exists(os.path.join(hero_dir, fallback)) else []
    if images:
        chosen = random.choice(images)
        return {"url": f"/static/images/hero/{chosen}"}
    return {"url": "/static/images/hero/hero.jpg"}, 200


def upload_imagem(files, upload_folder):
    if 'file' not in files:
        return {"erro": "Nenhum arquivo enviado"}, 400

    file = files['file']

    if file.filename == '':
        return {"erro": "Nome de arquivo vazio"}, 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4()}_{filename}"

        filepath = os.path.join(upload_folder, unique_name)

        file.save(filepath)

        return {
            "url": f"/uploadedcovers/{unique_name}"
        }

    return {"erro": "Tipo de arquivo não permitido"}, 400
