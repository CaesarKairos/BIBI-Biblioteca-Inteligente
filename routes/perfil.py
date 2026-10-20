"""Operações pessoais derivam a identidade exclusivamente da sessão."""
import json
import time
from flask import Blueprint,g,jsonify,request,render_template
from werkzeug.exceptions import BadRequest,NotFound
from werkzeug.security import check_password_hash
from database.database import db_manager
from services.contas_service import auditar,senha_validada,limitar
from services.circulacao_service import reservar,cancelar_reserva,notificar

bp=Blueprint('perfil',__name__)


@bp.route('/api/minha-conta/favoritos',methods=['GET','PUT'])
def favorites():
    from werkzeug.exceptions import Forbidden
    if g.conta['papel'] != 'leitor':
        raise Forbidden('Favoritos pertencem ao perfil de leitor.')
    with db_manager.connection() as conn:
        if request.method == 'PUT':
            ids=request.get_json().get('livros')
            if not isinstance(ids,list) or len(ids)>4 or any(type(i) is not int for i in ids) or len(set(ids))!=len(ids):
                raise BadRequest('Escolha até quatro livros diferentes.')
            conn.execute('BEGIN IMMEDIATE')
            previous={r[0] for r in conn.execute('SELECT livro_id FROM Favoritos WHERE conta_id=?',(g.conta['id'],))}
            for book in ids:
                row=conn.execute('SELECT arquivado FROM Livros WHERE id=?',(book,)).fetchone()
                if not row or (row[0] and book not in previous):
                    raise BadRequest('Selecione um livro ativo do acervo.')
            conn.execute('DELETE FROM Favoritos WHERE conta_id=?',(g.conta['id'],))
            conn.executemany('INSERT INTO Favoritos VALUES (?,?,?)',[(g.conta['id'],book,order) for order,book in enumerate(ids)])
            conn.commit()
        return jsonify(records(conn,'SELECT l.id,l.nome,l.capa_url,l.arquivado,f.ordem FROM Favoritos f JOIN Livros l ON l.id=f.livro_id WHERE f.conta_id=? ORDER BY f.ordem',(g.conta['id'],)))


@bp.route('/api/minha-conta/preferencias',methods=['GET','PUT'])
def preferences():
    with db_manager.connection() as conn:
        if request.method=='PUT':
            tema=request.get_json().get('tema')
            if tema not in ('claro','escuro'):
                raise BadRequest('Tema inválido.')
            conn.execute('INSERT INTO Preferencias VALUES (?,?) ON CONFLICT(conta_id) DO UPDATE SET tema=excluded.tema',(g.conta['id'],tema))
            conn.commit()
        row=conn.execute('SELECT tema FROM Preferencias WHERE conta_id=?',(g.conta['id'],)).fetchone()
        return jsonify(tema=row[0] if row else 'claro')


@bp.post('/api/minha-conta/email/enviar')
def email_send():
    from services.mensagens_service import pedir_verificacao
    return jsonify(pedir_verificacao(request.get_json()))


@bp.post('/api/minha-conta/email/confirmar')
def email_confirm():
    from services.mensagens_service import confirmar_email
    return jsonify(confirmar_email(request.get_json()))


@bp.get('/api/minha-conta/avatar')
def avatar():
    from services import avatar_service as avatars
    with db_manager.connection() as conn:
        saved=conn.execute('SELECT avatar FROM Contas WHERE id=?',(g.conta['id'],)).fetchone()[0]
    config=json.loads(saved) if saved else avatars.default()
    return jsonify(config=config,imagem=avatars.render(config),opcoes=avatars.FIELDS)


@bp.post('/api/minha-conta/avatar/previa')
def avatar_preview():
    from services import avatar_service as avatars
    return jsonify(imagem=avatars.render(request.get_json()))


@bp.put('/api/minha-conta/avatar')
def avatar_save():
    from services import avatar_service as avatars
    config=avatars.validate(request.get_json())
    image=avatars.render(config)
    with db_manager.connection() as conn:
        conn.execute('UPDATE Contas SET avatar=?,onboarding_concluido_em=COALESCE(onboarding_concluido_em,CURRENT_TIMESTAMP) WHERE id=?',(json.dumps(config),g.conta['id']))
        conn.commit()
    return jsonify(imagem=image)


def leitor():
    if not g.conta or not g.conta['leitor_id']:
        raise BadRequest('Esta conta não está vinculada a um cadastro de leitor.')
    return g.conta['leitor_id']


def records(conn,sql,params=()):
    cur=conn.execute(sql,params)
    return [dict(zip([d[0] for d in cur.description],row)) for row in cur.fetchall()]


@bp.get('/perfil')
def page():
    return render_template('perfil.html',ativo='perfil')


@bp.get('/boas-vindas')
def welcome():
    from flask import redirect
    if g.conta['onboarding_concluido_em']:
        return redirect('/app')
    return render_template('perfil.html',ativo='perfil',onboarding=True)


@bp.get('/api/minha-conta')
def profile():
    with db_manager.connection() as conn:
        account=dict(g.conta)
        if account['leitor_id']:
            account.update(records(conn,'SELECT tipo,sala,materia FROM Usuarios WHERE id=?',(leitor(),))[0])
        return jsonify(account)


@bp.post('/api/minha-conta/senha')
def password():
    limitar('senha',str(g.conta['id']))
    payload=request.get_json()
    hashed=senha_validada(payload)
    with db_manager.connection() as conn:
        old=conn.execute('SELECT senha_hash FROM Contas WHERE id=?',(g.conta['id'],)).fetchone()[0]
        if not check_password_hash(old,str(payload.get('senha_atual',''))):
            raise BadRequest('Senha atual inválida.')
        conn.execute('UPDATE Contas SET senha_hash=?,versao_sessao=versao_sessao+1 WHERE id=?',(hashed,g.conta['id']))
        conn.execute('UPDATE Codigos SET consumido=1 WHERE conta_id=? AND finalidade=?',(g.conta['id'],'recuperacao'))
        auditar(conn,'alterar_senha',g.conta['id'])
        conn.commit()
    return jsonify(mensagem='Senha alterada. Entre novamente.')


@bp.get('/api/minha-conta/emprestimos')
def loans():
    with db_manager.connection() as conn:
        return jsonify(records(conn,"""SELECT e.id,l.id AS livro_id,l.nome AS livro,l.capa_url AS capa,e.data_emprestimo,e.data_vencimento,e.data_devolucao,e.status,e.encerramento,
            (SELECT estado FROM PedidosRenovacao p WHERE p.emprestimo_id=e.id ORDER BY p.id DESC LIMIT 1) AS pedido
            FROM Emprestimo e JOIN Livros l ON l.id=e.livros_id WHERE e.usuarios_id=? ORDER BY e.id DESC""",(leitor(),)))


@bp.post('/api/minha-conta/emprestimos/<int:id>/renovacao')
def renewal(id):
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if not conn.execute("SELECT 1 FROM Emprestimo WHERE id=? AND usuarios_id=? AND status IN ('Aprovado','Atrasado') AND encerramento IS NULL",(id,leitor())).fetchone():
            raise NotFound('Empréstimo ativo não encontrado.')
        conn.execute('INSERT INTO PedidosRenovacao(emprestimo_id) VALUES (?)',(id,))
        auditar(conn,'solicitar_renovacao',id)
        conn.commit()
    return jsonify(mensagem='Pedido enviado ao bibliotecário. O prazo atual ainda não mudou.')


@bp.get('/api/minha-conta/quero-ler')
def wishlist():
    with db_manager.connection() as conn:
        return jsonify(records(conn,'SELECT l.id,l.nome,l.autor,l.capa_url,l.quantidade_disponivel AS disponivel,l.arquivado FROM QueroLer q JOIN Livros l ON l.id=q.livro_id WHERE q.leitor_id=? ORDER BY l.nome,l.id',(leitor(),)))


@bp.route('/api/minha-conta/quero-ler/<int:id>',methods=['POST','DELETE'])
def wish(id):
    with db_manager.connection() as conn:
        if request.method=='POST':
            if not conn.execute('SELECT 1 FROM Livros WHERE id=? AND arquivado=0',(id,)).fetchone():
                raise NotFound('Livro não encontrado.')
            conn.execute('INSERT OR IGNORE INTO QueroLer VALUES (?,?)',(leitor(),id))
        else:
            conn.execute('DELETE FROM QueroLer WHERE leitor_id=? AND livro_id=?',(leitor(),id))
        conn.commit()
    return jsonify(status='ok')


@bp.get('/api/minha-conta/reservas')
def reservations():
    with db_manager.connection() as conn:
        return jsonify(records(conn,"""SELECT r.id,r.livro_id,l.nome,l.capa_url,r.estado,r.expira,
            (SELECT COUNT(*) FROM Reservas q WHERE q.livro_id=r.livro_id AND q.estado='fila' AND (q.criada_em<r.criada_em OR (q.criada_em=r.criada_em AND q.id<=r.id))) AS posicao
            FROM Reservas r JOIN Livros l ON l.id=r.livro_id WHERE r.leitor_id=? ORDER BY r.id DESC""",(leitor(),)))


@bp.post('/api/minha-conta/reservas/<int:livro_id>')
def reserve(livro_id):
    return jsonify(reservar(leitor(),livro_id))


@bp.delete('/api/minha-conta/reservas/<int:id>')
def cancel(id):
    return jsonify(cancelar_reserva(id,leitor()))


@bp.get('/api/minha-conta/notificacoes')
def notifications():
    with db_manager.connection() as conn:
        return jsonify(records(conn,'SELECT id,mensagem,lida,criada_em FROM Notificacoes WHERE leitor_id=? ORDER BY id DESC LIMIT 100',(leitor(),)))


@bp.post('/api/minha-conta/notificacoes/<int:id>/ler')
def read_notification(id):
    with db_manager.connection() as conn:
        conn.execute('UPDATE Notificacoes SET lida=1 WHERE id=? AND leitor_id=?',(id,leitor()))
        conn.commit()
    return jsonify(status='ok')


@bp.get('/api/minha-conta/avaliacoes')
def reviews():
    with db_manager.connection() as conn:
        return jsonify(records(conn,'SELECT a.*,l.nome,l.capa_url FROM Avaliacoes a JOIN Livros l ON l.id=a.livro_id WHERE a.leitor_id=? ORDER BY atualizada_em DESC',(leitor(),)))


@bp.get('/api/minha-conta/lidos')
def read_books():
    with db_manager.connection() as conn:
        return jsonify(records(conn,'''SELECT l.id,l.nome,l.autor,l.capa_url,l.arquivado,r.concluida_em
            FROM LeiturasConcluidas r JOIN Livros l ON l.id=r.livro_id
            WHERE r.leitor_id=? ORDER BY r.concluida_em DESC,l.id DESC''',(leitor(),)))


@bp.route('/api/minha-conta/lidos/<int:id>',methods=['POST','DELETE'])
def mark_read(id):
    with db_manager.connection() as conn:
        owner=leitor()
        if request.method=='POST':
            if not conn.execute('SELECT 1 FROM Livros WHERE id=? AND arquivado=0',(id,)).fetchone():
                raise NotFound('Livro não encontrado.')
            conn.execute('INSERT OR IGNORE INTO LeiturasConcluidas(leitor_id,livro_id) VALUES (?,?)',(owner,id))
        else:
            conn.execute('DELETE FROM LeiturasConcluidas WHERE leitor_id=? AND livro_id=?',(owner,id))
        conn.commit()
    return jsonify(status='ok')


@bp.route('/api/minha-conta/avaliacoes/<int:livro_id>',methods=['POST','DELETE','GET'])
def review(livro_id):
    with db_manager.connection() as conn:
        if request.method=='GET':
            # Sem turma, e-mail ou telefone. Identificação pública mínima.
            return jsonify(records(conn,"SELECT estrelas,comentario,atualizada_em FROM Avaliacoes WHERE livro_id=? AND estado='publicado' ORDER BY atualizada_em DESC LIMIT 100",(livro_id,)))
        if request.method=='DELETE':
            conn.execute('DELETE FROM Avaliacoes WHERE livro_id=? AND leitor_id=?',(livro_id,leitor()))
        else:
            limitar('avaliacao',str(g.conta['id']),limite=10,janela=3600)
            data=request.get_json(); stars=data.get('estrelas'); comment=data.get('comentario','')
            if type(stars) is not int or not 1<=stars<=5 or not isinstance(comment,str) or len(comment)>2000:
                raise BadRequest('Informe de 1 a 5 estrelas e até 2000 caracteres.')
            if not conn.execute('SELECT 1 FROM Livros WHERE id=? AND arquivado=0',(livro_id,)).fetchone():
                raise NotFound('Livro não encontrado.')
            # Apoio determinístico, sempre revisável; não é garantia de moderação.
            flagged=any(word in comment.casefold() for word in ('idiota','imbecil','merda','porra','caralho'))
            estado='revisao' if flagged else 'publicado'
            conn.execute('''INSERT INTO Avaliacoes(leitor_id,livro_id,estrelas,comentario,estado,atualizada_em) VALUES (?,?,?,?,?,?)
                ON CONFLICT(leitor_id,livro_id) DO UPDATE SET estrelas=excluded.estrelas,comentario=excluded.comentario,estado=excluded.estado,motivo=NULL,atualizada_em=excluded.atualizada_em''',
                         (leitor(),livro_id,stars,comment,estado,int(time.time())))
        auditar(conn,'avaliacao',livro_id)
        conn.commit()
    return jsonify(status='ok')
