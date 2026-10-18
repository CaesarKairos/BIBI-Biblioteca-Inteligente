"""Seleção local verificável, sem inferir identidade de autoria pelo nome."""
import hashlib
import json
from flask import current_app
from database.database import db_manager
from services.catalogo_service import SELECT, record, normalize

def message_filters(message):
    """Reconhece pedidos explícitos apenas contra metadados do acervo real."""
    text=normalize(message);filters={}
    if any(term in text for term in ('autora','mulher','mulheres','feminina')):
        filters['feminina']=True
    if any(term in text for term in ('brasileir','do brasil','nacional')):
        filters['brasileira']=True
    if 'disponiv' in text:
        filters['disponivel']=True
    with db_manager.connection() as conn:
        for (category,) in conn.execute('SELECT DISTINCT categoria FROM Livros WHERE arquivado=0'):
            if category and normalize(category) in text:
                filters['genero']=category
        for (author,) in conn.execute('SELECT DISTINCT autor FROM Livros WHERE arquivado=0'):
            if author and len(author)>3 and normalize(author) in text:
                filters['autor']=author
    return filters

def recommend(account, filters=None):
    filters = filters or {}
    with db_manager.connection() as conn:
        rows = conn.execute(SELECT.replace(' FROM Livros', ',autoria_genero,autoria_pais,autoria_fonte FROM Livros')+' WHERE arquivado=0').fetchall()
        favorites = [r[0] for r in conn.execute('SELECT livro_id FROM Favoritos WHERE conta_id=?',(account['id'],))]
        loans, ratings, wishes = [], [], []
        if account['leitor_id']:
            loans = [r[0] for r in conn.execute('SELECT DISTINCT livros_id FROM Emprestimo WHERE usuarios_id=?',(account['leitor_id'],))]
            ratings = conn.execute('SELECT livro_id,estrelas FROM Avaliacoes WHERE leitor_id=?',(account['leitor_id'],)).fetchall()
            wishes = [r[0] for r in conn.execute('SELECT livro_id FROM QueroLer WHERE leitor_id=?',(account['leitor_id'],))]
    # A assinatura inclui todos os dados relevantes: alterações invalidam imediatamente.
    signature = hashlib.sha256(json.dumps([rows,favorites,loans,ratings,wishes,filters],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    cache = current_app.extensions.setdefault('ai_recommendations', {})
    key = (account['id'],signature)
    if key in cache:
        return cache[key]
    books = []
    interests = set()
    positive = set(favorites+wishes+loans+[i for i,stars in ratings if stars>=4])
    rejected = {i for i,stars in ratings if stars<=2}
    def tags(book):
        return set(normalize((book['categoria'] or '')+' '+(book['temas'] or '')).replace(',',' ').split())
    for row in rows:
        book = record(row[:14]);book.update(autoria_genero=row[14],autoria_pais=row[15],autoria_fonte=row[16])
        books.append(book)
        if book['id'] in positive:
            interests.update(tags(book))
    candidates = []
    for book in books:
        trusted = bool(book['autoria_fonte'])
        female = trusted and book['autoria_genero']=='feminina'
        brazil = trusted and normalize(book['autoria_pais']) in ('br','brasil','brazil')
        if filters.get('genero') and normalize(filters['genero']) not in normalize(book['categoria'] or ''):
            continue
        if filters.get('prateleira') and book['prateleira']!=filters['prateleira']:
            continue
        if filters.get('q') and not all(term in normalize(' '.join(str(book.get(k) or '') for k in ('titulo','autor','isbn','categoria','temas','localizacao'))) for term in normalize(filters['q']).split()):
            continue
        if filters.get('autor') and normalize(filters['autor']) not in normalize(book['autor']):
            continue
        if filters.get('feminina') and not female:
            continue
        if filters.get('brasileira') and not brazil:
            continue
        if filters.get('disponivel') and book['disponivel']<=0:
            continue
        if filters.get('indisponivel') and book['disponivel']>0:
            continue
        affinity = len(tags(book) & interests)
        priority = 3 if female and brazil else 2 if female or brazil else 0
        book['motivo'] = ('Autora brasileira com metadados documentados.' if priority==3 else
                          'Valorização de autoria feminina ou literatura brasileira.' if priority else 'Descoberta no catálogo da escola.')
        if affinity:
            book['motivo'] += ' Temas em comum com suas escolhas.'
        # Afinidade vem antes do desempate CIÊNCIA DELAS. Disponibilidade é explícita.
        score = (book['id'] not in rejected, affinity, priority, book['disponivel']>0, book['id'] not in loans)
        candidates.append((score,book))
    candidates.sort(key=lambda pair: tuple(-int(x) for x in pair[0])+(pair[1]['id'],))
    selected, counts = [], {}
    while candidates and len(selected)<12:
        # Diversidade apenas dentro do mesmo patamar de afinidade e prioridade.
        top = candidates[0][0][:3]
        peers = [i for i,pair in enumerate(candidates) if pair[0][:3]==top]
        index = min(peers,key=lambda i: counts.get(candidates[i][1]['prateleira'],0))
        _,book = candidates.pop(index);selected.append(book)
        counts[book['prateleira']] = counts.get(book['prateleira'],0)+1
    if len(cache)>256:
        cache.clear()
    cache[key]=selected
    return selected

def aggregates():
    with db_manager.connection() as conn:
        total = conn.execute('SELECT COUNT(*) FROM Emprestimo').fetchone()[0]
        monthly = conn.execute("SELECT substr(data_emprestimo,1,7),COUNT(*) FROM Emprestimo GROUP BY 1 ORDER BY 1 DESC LIMIT 12").fetchall()
        books = conn.execute('''SELECT l.id,l.nome,COUNT(e.id) AS circulacao FROM Livros l
            LEFT JOIN Emprestimo e ON e.livros_id=l.id WHERE l.arquivado=0 GROUP BY l.id ORDER BY circulacao,l.id LIMIT 10''').fetchall()
        demand = conn.execute('''SELECT l.nome,COUNT(*) FROM Reservas r JOIN Livros l ON l.id=r.livro_id
            WHERE r.estado='fila' GROUP BY l.id ORDER BY COUNT(*) DESC LIMIT 5''').fetchall()
        categories=conn.execute('''SELECT COALESCE(l.categoria,'Não informada'),COUNT(e.id) FROM Livros l
            LEFT JOIN Emprestimo e ON e.livros_id=l.id WHERE l.arquivado=0 GROUP BY l.categoria ORDER BY COUNT(e.id)''').fetchall()
        popular=conn.execute('''SELECT l.nome,COUNT(e.id) FROM Livros l JOIN Emprestimo e ON e.livros_id=l.id
            WHERE l.arquivado=0 GROUP BY l.id ORDER BY COUNT(e.id) DESC,l.id LIMIT 5''').fetchall()
    return {'emprestimos_registrados':total,'mensal':monthly,'menor_circulacao':books,'reservas_em_fila':demand,'categorias':categories,'maior_circulacao':popular}
