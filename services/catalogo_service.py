import unicodedata
from werkzeug.exceptions import BadRequest,NotFound
from database.database import db_manager

CATEGORIES=('Ficção','Não-ficção','Poesia','Quadrinhos')


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFD',str(value or '').casefold()) if not unicodedata.combining(c))


def shelf(category):
    value=normalize(category)
    if 'poe' in value:
        return 'Poesia'
    if any(word in value for word in ('comic','quadrin','manga','graphic')):
        return 'Quadrinhos'
    if any(word in value for word in ('nao','nonfiction','non-fiction','history','histor','science','ciencia','biograph','biograf','relig','educ','filosof','philosoph')):
        return 'Não-ficção'
    return 'Ficção'  # Categoria desconhecida continua descoberta; metadado original preservado.


def record(row):
    names=['id','isbn','titulo','autor','ano','capa','descricao','temas','categoria','estoque','disponivel','data_cadastro','localizacao','numero_paginas']
    result=dict(zip(names,row));result['prateleira']=shelf(result['categoria']);return result

SELECT='SELECT id,isbn,nome,autor,ano_publicacao,capa_url,descricao,temas,categoria,estoque,quantidade_disponivel,data_cadastro,localizacao,numero_paginas FROM Livros'


def search(args):
    try:
        page=max(1,int(args.get('pagina',1)));size=min(120,max(1,int(args.get('limite',60))))
    except (ValueError,TypeError):
        raise BadRequest('Paginação inválida.')
    where=['arquivado=0'];params=[]
    for term in normalize(args.get('q','')).split():
        where.append("instr(normalizar(nome||' '||autor||' '||COALESCE(isbn,'')||' '||COALESCE(categoria,'')||' '||COALESCE(temas,'')||' '||COALESCE(localizacao,'')),?)>0");params.append(term)
    if args.get('categoria'):
        if args['categoria'] not in CATEGORIES:
            raise BadRequest('Categoria de prateleira inválida.')
        where.append('prateleira(categoria)=?');params.append(args['categoria'])
    if args.get('disponibilidade')=='disponivel':
        where.append('quantidade_disponivel>0')
    elif args.get('disponibilidade')=='indisponivel':
        where.append('quantidade_disponivel<=0')
    clause=' WHERE '+' AND '.join(where)
    with db_manager.connection() as conn:
        conn.create_function('normalizar',1,normalize,deterministic=True);conn.create_function('prateleira',1,shelf,deterministic=True)
        total=conn.execute('SELECT COUNT(*) FROM Livros'+clause,params).fetchone()[0]
        rows=conn.execute(SELECT+clause+' ORDER BY nome COLLATE NOCASE,id LIMIT ? OFFSET ?',params+[size,(page-1)*size]).fetchall()
    return {'livros':[record(r) for r in rows],'total':total,'pagina':page,'mais':page*size<total}


def detail(id):
    with db_manager.connection() as conn:
        row=conn.execute(SELECT+' WHERE id=? AND arquivado=0',(id,)).fetchone()
        if not row:
            raise NotFound('Livro não encontrado.')
        return record(row)
