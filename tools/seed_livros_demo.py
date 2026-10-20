"""Seed: adiciona 8 livros demo por categoria, via ISBN."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database.database import DatabaseManager
from services.livros_service import buscar_open_library
from utils.datetime import get_brasilia_today

DB_PATH = r'C:\Users\cesar\AppData\Local\BIBI\Biblioteca.db'

ISBNS_POR_CATEGORIA = {
    'Ficcao': [
        '9780451524935',
        '9780141439518',
        '9780439023528',
        '9780140449136',
        '9780553213119',
        '9780743273565',
        '9780061120084',
        '9780141439594',
    ],
    'Nao-ficcao': [
        '9780140449143',
        '9780140449334',
        '9780140449341',
        '9780140449358',
        '9780140449433',
        '9780140449457',
        '9780140449464',
        '9780140449488',
    ],
    'Poesia': [
        '9780140449297',
        '9780140424447',
        '9780140449310',
        '9780140449389',
        '9780140449419',
        '9780140449471',
        '9780140449532',
        '9780140449518',
    ],
    'Quadrinhos': [
        '9781401208449',
        '9781401207657',
        '9781401237586',
        '9781401233465',
        '9781401223025',
        '9781401264537',
        '9781401235155',
        '9781401223032',
    ],
}

QUANTIDADE_POR_LIVRO = 3

FALLBACK_DADOS = {
    '9781401208449': {'titulo': 'Watchmen', 'autor': 'Alan Moore', 'ano': 1987, 'descricao': 'Obra prima de Alan Moore.', 'temas': 'quadrinho, herois, distopia', 'capa': ''},
    '9781401207657': {'titulo': 'V de Vinganca', 'autor': 'Alan Moore', 'ano': 1982, 'descricao': 'Distopia em quadrinhos por Alan Moore.', 'temas': 'quadrinho, distopia, politica', 'capa': ''},
    '9781401237586': {'titulo': 'Batman: Ano Um', 'autor': 'Frank Miller', 'ano': 1987, 'descricao': 'Origem do Batman por Frank Miller.', 'temas': 'quadrinho, herois, origem', 'capa': ''},
    '9781401233465': {'titulo': 'Sandman Vol. 1', 'autor': 'Neil Gaiman', 'ano': 1989, 'descricao': 'Sonho e os Eternos por Neil Gaiman.', 'temas': 'quadrinho, fantasia, mitologia', 'capa': ''},
    '9781401223025': {'titulo': 'Maus', 'autor': 'Art Spiegelman', 'ano': 1986, 'descricao': 'Historia do Holocausto em quadrinhos.', 'temas': 'quadrinho, historia, holocausto', 'capa': ''},
    '9781401264537': {'titulo': 'Sandman Vol. 2', 'autor': 'Neil Gaiman', 'ano': 1990, 'descricao': 'Casa de Bonecas por Neil Gaiman.', 'temas': 'quadrinho, fantasia, mitologia', 'capa': ''},
    '9781401235155': {'titulo': 'Batman: Cavaleiro das Trevas', 'autor': 'Frank Miller', 'ano': 1986, 'descricao': 'Batman em futuro distopico por Frank Miller.', 'temas': 'quadrinho, herois, distopia', 'capa': ''},
    '9781401223032': {'titulo': 'Maus Volume 2', 'autor': 'Art Spiegelman', 'ano': 1991, 'descricao': 'Continuacao de Maus por Art Spiegelman.', 'temas': 'quadrinho, historia, holocausto', 'capa': ''},
}

def main(categoria_alvo=None):
    manager = DatabaseManager(DB_PATH, initialize=False)
    hoje = get_brasilia_today().isoformat()
    total_inseridos = 0
    total_falhas = 0

    with manager.connection() as conn:
        cursor = conn.cursor()

        existentes = {
            ''.join(ch for ch in (r[0] or '') if ch.isdigit())
            for r in cursor.execute('SELECT isbn FROM Livros WHERE arquivado=0').fetchall()
        }

        categorias = ISBNS_POR_CATEGORIA
        if categoria_alvo:
            if categoria_alvo not in categorias:
                print('Categoria invalida: ' + categoria_alvo)
                return
            categorias = {categoria_alvo: ISBNS_POR_CATEGORIA[categoria_alvo]}

        for categoria, isbns in categorias.items():
            print('\n=== Categoria: ' + categoria + ' ===')
            for isbn in isbns:
                isbn_digitos = ''.join(ch for ch in isbn if ch.isdigit())
                if isbn_digitos in existentes:
                    print('  [PULADO] ' + isbn + ' ja existe no acervo')
                    continue

                print('  Buscando ISBN ' + isbn + '...', end=' ')
                info = buscar_open_library(isbn)

                if not info:
                    fb = FALLBACK_DADOS.get(isbn)
                    if fb:
                        info = {
                            'titulo': fb['titulo'],
                            'autor': fb['autor'],
                            'ano_publicacao': fb['ano'],
                            'descricao': fb['descricao'],
                            'temas': fb['temas'],
                            'categoria': categoria,
                            'capa': fb['capa'],
                            'numero_paginas': None,
                        }
                        print('FALLBACK (dados manuais) | ' + fb['titulo'])
                    else:
                        print('FALHA - sem metadados e sem fallback')
                        total_falhas += 1
                        continue
                else:
                    print('OK via API | ' + str(info.get('titulo', ''))[:40])
                    info['categoria'] = categoria

                numero_paginas = info.get('numero_paginas')

                try:
                    cursor.execute(
                        '''
                        INSERT INTO Livros
                            (isbn, nome, autor, ano_publicacao, capa_url,
                             descricao, temas, categoria, estoque,
                             quantidade_disponivel, data_cadastro, localizacao, numero_paginas)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''',
                        (
                            isbn,
                            info.get('titulo') or 'Titulo Desconhecido',
                            info.get('autor') or 'Autor Desconhecido',
                            info.get('ano_publicacao'),
                            info.get('capa') or '',
                            info.get('descricao') or '',
                            info.get('temas') or '',
                            categoria,
                            QUANTIDADE_POR_LIVRO,
                            QUANTIDADE_POR_LIVRO,
                            hoje,
                            '',
                            numero_paginas,
                        ),
                    )
                    livro_id = cursor.lastrowid
                    existentes.add(isbn_digitos)
                    total_inseridos += 1
                except Exception as e:
                    print('ERRO ao inserir: ' + str(e))
                    total_falhas += 1

        conn.commit()

    print('\n===============================')
    print('Inseridos com sucesso: ' + str(total_inseridos))
    print('Falhas: ' + str(total_falhas))
    print('===============================')

if __name__ == '__main__':
    import sys
    cat = sys.argv[1] if len(sys.argv) > 1 else None
    main(cat)