"""Audita somente dados bibliográficos. Não abre contas nem segredos da escola.

Por padrão não altera o catálogo. --aplicar grava apenas candidatos de ISBN
confirmado, preservando uma cópia SQLite consistente antes da alteração.
Imagens Open Library são exibidas pela URL, sem redistribuição dos arquivos.
"""
import argparse
from difflib import SequenceMatcher
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
import unicodedata
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import requests
from PIL import Image
from services.image_service import validate_image


def normal(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.lower()) if not unicodedata.combining(c))


def image_valid(data):
    validate_image(data)
    with Image.open(BytesIO(data)) as image:
        if min(image.size) < 40:
            raise ValueError('Imagem vazia ou placeholder remoto')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, default=Path(os.environ['LOCALAPPDATA'])/'BIBI')
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--aplicar', action='store_true')
    args = parser.parse_args()
    root = args.data_dir.resolve()
    conn = sqlite3.connect((root/'Biblioteca.db').as_uri()+'?mode=ro', uri=True)
    rows = conn.execute('SELECT id,isbn,nome,autor,capa_url FROM Livros WHERE arquivado=0').fetchall()
    session = requests.Session()
    session.headers['User-Agent'] = 'BIBI/1.1 (https://github.com/CaesarKairos/BIBI-Biblioteca-Inteligente)'
    results = []
    valid = 0
    for bid, isbn, title, author, url in rows:
        reason = 'Sem capa'
        try:
            if not url or 'placeholder' in url:
                raise ValueError('Sem capa')
            if url.startswith('https://'):
                r = session.get(url, timeout=15)
                r.raise_for_status()
                image_valid(r.content)
                time.sleep(1)
            else:
                path = None
                for prefix, folder in [('/uploadedcovers/', root/'uploadedcovers'), ('/externalcovers/', root/'externalcovers'), ('/static/', Path(__file__).resolve().parents[1]/'static')]:
                    if url.startswith(prefix):
                        path = (folder/url[len(prefix):]).resolve()
                        if not path.is_relative_to(folder.resolve()):
                            raise ValueError('Caminho inválido')
                        break
                if path is None:
                    raise ValueError('Referência desconhecida')
                image_valid(path.read_bytes())
            valid += 1
            continue
        except (ValueError, OSError, requests.RequestException) as error:
            reason = str(error).split('\n')[0][:200]
        item = dict(id=bid, titulo=title, isbn=isbn, motivo=reason, anterior=url, estado='pendente')
        digits = re.sub(r'[^0-9X]', '', isbn or '')
        if len(digits) in (10, 13):
            try:
                time.sleep(1.1)
                r = session.get(f'https://openlibrary.org/isbn/{digits}.json', timeout=15)
                r.raise_for_status()
                edition = r.json()
                candidate_title = edition.get('title', '')
                # A correspondência do ISBN não basta: títulos traduzidos ou
                # incompatíveis permanecem para revisão humana.
                match = SequenceMatcher(None, normal(title), normal(candidate_title)).ratio()
                covers = [x for x in edition.get('covers', []) if x > 0]
                item['titulo_fonte'] = candidate_title
                item['fonte'] = f'https://openlibrary.org/isbn/{digits}'
                item['edicao'] = edition.get('key')
                item['similaridade'] = round(match, 3)
                if match >= .83 and covers:
                    candidate = f'https://covers.openlibrary.org/b/id/{covers[0]}-L.jpg?default=false'
                    r = session.get(candidate, timeout=15)
                    r.raise_for_status()
                    image_valid(r.content)
                    item['nova'] = candidate
                    item['estado'] = 'candidato ISBN e título confirmados'
            except (ValueError, OSError, requests.RequestException) as error:
                item['busca'] = str(error).split('\n')[0][:200]
        else:
            item['busca'] = 'Edição/ISBN não informado; não associar capa de edição arbitrária.'
        results.append(item)
        print(title, item['estado'], flush=True)
    if args.aplicar and any('nova' in x for x in results):
        backup = root/'backups'/f'antes-capas-{time.time_ns()}.db'
        backup.parent.mkdir(exist_ok=True)
        dest = sqlite3.connect(backup)
        conn.backup(dest)
        dest.close()
        write = sqlite3.connect(root/'Biblioteca.db')
        try:
            with write:
                for item in results:
                    if 'nova' not in item:
                        continue
                    changed = write.execute('UPDATE Livros SET capa_url=? WHERE id=? AND capa_url IS ?', (item['nova'], item['id'], item['anterior'])).rowcount
                    item['estado'] = 'corrigida' if changed else 'preservada: alteração concorrente'
        finally:
            write.close()
    conn.close()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(dict(total=len(rows), validas_antes=valid, resultados=results, politica='URLs Open Library; nenhum arquivo de capa baixado é persistido ou redistribuído.', termos='https://openlibrary.org/dev/docs/api/covers'), ensure_ascii=False, indent=2), encoding='utf-8')
    print('Relatório:', args.report)


if __name__ == '__main__':
    main()
