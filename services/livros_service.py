import logging

logger = logging.getLogger(__name__)

from database.database import db_manager
from services.configuracoes_service import is_obrigar_localizacao_livro
from utils.datetime import get_brasilia_today
import re
import requests
import uuid


def validar_numero_paginas(valor):
    """Campo opcional; não trunca decimais nem aceita booleanos como inteiros."""
    if valor is None or valor == '':
        return None
    if isinstance(valor, str) and re.fullmatch(r'[0-9]+', valor.strip()):
        valor = int(valor.strip())
    if type(valor) is not int or not 0 < valor <= 9007199254740991:
        raise ValueError('Número de páginas deve ser um inteiro positivo válido.')
    return valor


def paginas_da_fonte(valor):
    """Metadados externos inválidos são ausência de informação, não erro de cadastro."""
    try:
        return validar_numero_paginas(valor)
    except ValueError:
        return None


def buscar_open_library(isbn):
    """API #1 - Open Library"""
    try:
        url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            key = f"ISBN:{isbn}"
            if key in data:
                book = data[key]
                titulo = book.get('title', 'Título Desconhecido')
                autores = book.get('authors')
                autor = autores[0]['name'] if autores else 'Autor Desconhecido'
                ano = None
                if 'publish_date' in book:
                    import re
                    match = re.search(r'\d{4}', book['publish_date'])
                    if match:
                        ano = int(match.group())
                descricao = ''
                if 'excerpts' in book and book['excerpts']:
                    descricao = book['excerpts'][0]['text']
                temas = ''
                if 'subjects' in book:
                    temas = ', '.join([s['name'] for s in book['subjects'][:3]])
                categoria = 'Ficção'
                capa = ''
                if 'cover' in book and book['cover']:
                    capa_id = book['cover']['large'] if 'large' in book['cover'] else book['cover']['medium'] if 'medium' in book['cover'] else ''
                    if capa_id:
                        capa = capa_id
                if not capa:
                    capa = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
                return {
                    "titulo": titulo,
                    "autor": autor,
                    "ano_publicacao": ano,
                    "numero_paginas": paginas_da_fonte(book.get('number_of_pages')),
                    "descricao": descricao,
                    "temas": temas,
                    "categoria": categoria,
                    "capa": capa
                }
    except Exception as e:
        logger.exception("Falha na integração externa")
    return None


def buscar_brasil_api(isbn):
    """API #2 - BrasilAPI (ISBN)"""
    try:
        url = f"https://brasilapi.com.br/api/isbn/v1/{isbn}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            titulo = data.get('title', 'Título Desconhecido')
            autor = ''
            autores = data.get('authors', [])
            if autores:
                autor = autores[0] if isinstance(autores[0], str) else autores[0].get('name', '')
            if not autor:
                autor = data.get('author', 'Autor Desconhecido')
            ano = None
            if data.get('year'):
                try:
                    ano = int(data['year'])
                except (TypeError, ValueError):
                    pass
            descricao = data.get('synopsis', '') or ''
            temas = data.get('subjects', '') or ''
            if isinstance(temas, list):
                temas = ', '.join(temas[:3])
            categoria = data.get('categories', '') or ''
            if isinstance(categoria, list):
                categoria = categoria[0] if categoria else 'Ficção'
            if not categoria:
                categoria = 'Ficção'
            capa = data.get('cover_url', '') or ''
            if not capa:
                capa = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
            return {
                "titulo": titulo,
                "autor": autor,
                "ano_publicacao": ano,
                "numero_paginas": paginas_da_fonte(data.get('page_count')),
                "descricao": descricao,
                "temas": temas,
                "categoria": categoria,
                "capa": capa
            }
    except Exception as e:
        logger.exception("Falha na integração externa")
    return None


def buscar_google_books_por_isbn(isbn):
    """API #3 - Google Books (por ISBN primeiro)"""
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if 'items' in data and len(data['items']) > 0:
                book = data['items'][0]['volumeInfo']
                return _extrair_dados_google(book, isbn)
    except Exception as e:
        logger.exception("Falha na integração externa")
    return None


def buscar_google_books_por_titulo(titulo):
    """API #3 - Google Books (fallback por título)"""
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q=intitle:{requests.utils.quote(titulo)}&maxResults=1"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if 'items' in data and len(data['items']) > 0:
                book = data['items'][0]['volumeInfo']
                return _extrair_dados_google(book, None)
    except Exception as e:
        logger.exception("Falha na integração externa")
    return None


def _extrair_dados_google(book, isbn):
    titulo = book.get('title', 'Título Desconhecido')
    autores = book.get('authors', [])
    autor = autores[0] if autores else 'Autor Desconhecido'
    ano = None
    if 'publishedDate' in book:
        try:
            ano = int(book['publishedDate'][:4])
        except (TypeError, ValueError):
            pass
    descricao = book.get('description', '') or ''
    # Limpar tags HTML da descrição
    descricao = re.sub(r'<[^>]+>', '', descricao)
    temas_list = book.get('categories', [])
    temas = ', '.join(temas_list[:3]) if temas_list else ''
    categoria = temas_list[0] if temas_list else 'Ficção'
    capa = ''
    if 'imageLinks' in book:
        capa = book['imageLinks'].get('thumbnail', '') or ''
        if capa:
            capa = capa.replace('http://', 'https://')
    if not capa and isbn:
        capa = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
    return {
        "titulo": titulo,
        "autor": autor,
        "ano_publicacao": ano,
        "numero_paginas": paginas_da_fonte(book.get('pageCount')),
        "descricao": descricao,
        "temas": temas,
        "categoria": categoria,
        "capa": capa
    }


def buscar_livro_cascata(isbn):
    """
    Busca dados do livro em cascata usando múltiplas APIs.
    Preenche incrementalmente: se a primeira retornar parcialmente,
    as seguintes complementam sem sobrescrever dados existentes.
    """
    # Dicionário vazio para acumular dados
    dados = {
        "titulo": None,
        "autor": None,
        "ano_publicacao": None,
        "numero_paginas": None,
        "descricao": None,
        "temas": None,
        "categoria": None,
        "capa": None
    }

    def preencher_faltantes(fonte):
        """Preenche apenas campos que ainda estão vazios"""
        modificado = False
        for campo in dados:
            if (dados[campo] is None or dados[campo] == '') and fonte.get(campo):
                dados[campo] = fonte[campo]
                modificado = True
        return modificado

    # 1. Open Library
    logger.debug(f"Buscando ISBN {isbn} na Open Library...")
    ol = buscar_open_library(isbn)
    if ol:
        preencher_faltantes(ol)
        if all(v is not None and v != '' for v in dados.values()):
            return dados

    # 2. BrasilAPI
    logger.debug(f"Buscando ISBN {isbn} na BrasilAPI...")
    br = buscar_brasil_api(isbn)
    if br:
        preencher_faltantes(br)
        if all(v is not None and v != '' for v in dados.values()):
            return dados

    # 3. Google Books (primeiro por ISBN)
    logger.debug(f"Buscando ISBN {isbn} no Google Books...")
    gb = buscar_google_books_por_isbn(isbn)
    if gb:
        preencher_faltantes(gb)
        if all(v is not None and v != '' for v in dados.values()):
            return dados

    # 4. Google Books (fallback por título, se tiver título)
    if dados.get("titulo"):
        logger.debug(f"Buscando '{dados['titulo']}' no Google Books (fallback por título)...")
        gb_titulo = buscar_google_books_por_titulo(dados["titulo"])
        if gb_titulo:
            preencher_faltantes(gb_titulo)

    # Se pelo menos título e autor foram preenchidos, considera sucesso
    if dados.get("titulo") and dados.get("autor"):
        return dados
    return None


def api_livros(admin, data, method):
    with db_manager.connection() as conn:
        cursor = conn.cursor()

        if method == 'POST':
            if not admin:
                return {"erro": "Acesso negado. Operação permitida apenas para administradores."}, 403
            if not isinstance(data, dict):
                return {"erro": "Envie os dados do livro em um objeto JSON."}, 400
            try:
                numero_paginas = validar_numero_paginas(data.get('numero_paginas'))
            except ValueError as error:
                return {"erro": str(error)}, 400
            hoje = get_brasilia_today().isoformat()
        
            localizacao = data.get('localizacao', '').strip()
            if is_obrigar_localizacao_livro() and not localizacao:
                return {"erro": "O campo Localização (prateleira) é obrigatório conforme configuração do sistema."}, 400

            if data.get('manual'):
                isbn = data.get('isbn', 'MANUAL_' + str(uuid.uuid4())[:8])
                titulo = data['titulo']
                autor = data['autor']
                ano = data.get('ano')
                descricao = data.get('descricao', '')
                temas = data.get('temas', '')
                categoria = data.get('categoria', 'Ficção')
                quantidade = int(data['quantidade'])
                capa = data.get('capa', '')
                if not capa:
                    capa = '/static/images/placeholder.png'
            else:
                isbn = data['isbn']
                quantidade = int(data['quantidade'])
                info = buscar_livro_cascata(isbn)
                if not info:
                    return {"erro": "ISBN não encontrado ou serviço indisponível"}, 404
                titulo = info['titulo']
                autor = info['autor']
                ano = info['ano_publicacao']
                descricao = info['descricao']
                temas = info['temas']
                categoria = info['categoria']
                capa = info['capa']
                numero_paginas = paginas_da_fonte(info.get('numero_paginas'))

            cursor.execute('''
                INSERT INTO Livros (isbn, nome, autor, ano_publicacao, capa_url, descricao, temas, categoria, estoque, quantidade_disponivel, data_cadastro, localizacao, numero_paginas)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (isbn, titulo, autor, ano, capa, descricao, temas, categoria, quantidade, quantidade, hoje, localizacao, numero_paginas))
            conn.commit()
            livro_id = cursor.lastrowid
            return {
                "id": livro_id, "isbn": isbn, "titulo": titulo, "autor": autor,
                "ano": ano, "capa": capa, "descricao": descricao, "temas": temas,
                "categoria": categoria, "estoque": quantidade, "disponivel": quantidade,
                "data_cadastro": hoje, "localizacao": localizacao, "numero_paginas": numero_paginas
            }, 201

        else:
            cursor.execute('''
                SELECT id, isbn, nome, autor, ano_publicacao, capa_url, descricao, temas, categoria, estoque, quantidade_disponivel, data_cadastro, localizacao, numero_paginas
                FROM Livros
            ''')
            livros = []
            for row in cursor.fetchall():
                livros.append({
                    "id": row[0], "isbn": row[1], "titulo": row[2], "autor": row[3],
                    "ano": row[4], "capa": row[5], "descricao": row[6], "temas": row[7],
                    "categoria": row[8], "estoque": row[9], "disponivel": row[10],
                    "data_cadastro": row[11], "localizacao": row[12], "numero_paginas": row[13]
                })
            return livros


def editar_livro(id, data):
    if not isinstance(data, dict):
        return {"erro": "Envie os dados do livro em um objeto JSON."}, 400
    try:
        numero_paginas = validar_numero_paginas(data.get('numero_paginas'))
    except ValueError as error:
        return {"erro": str(error)}, 400
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        # Clientes anteriores que não enviam o novo campo preservam seu valor.
        if 'numero_paginas' in data:
            cursor.execute('UPDATE Livros SET numero_paginas = ? WHERE id = ?', (numero_paginas, id))
        capa_url = data.get('capa')
        if capa_url:
            cursor.execute('UPDATE Livros SET capa_url = ? WHERE id = ?', (capa_url, id))
        cursor.execute('''
            UPDATE Livros
            SET nome = ?, autor = ?, ano_publicacao = ?, descricao = ?, temas = ?, estoque = ?, quantidade_disponivel = ?, categoria = ?, localizacao = ?
            WHERE id = ?
        ''', (
            data.get('titulo'), data.get('autor'), data.get('ano'),
            data.get('descricao'), data.get('temas'), data.get('estoque'), data.get('disponivel'),
            data.get('categoria'), data.get('localizacao', ''), id
        ))
        conn.commit()
        return {"status": "ok"}


def excluir_livro(id):
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM Livros WHERE id = ?', (id,))
        conn.commit()
        return {"status": "ok"}
