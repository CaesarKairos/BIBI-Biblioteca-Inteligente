"""Transições físicas executadas na mesma transação IMMEDIATE do estoque."""
import json
import time
from datetime import timedelta,date
from flask import g
from werkzeug.exceptions import BadRequest,NotFound
from database.database import db_manager
from services.contas_service import auditar,email_normalizado
from utils.datetime import get_brasilia_today

# Compatibilidade até a biblioteca definir suas regras: não impor limites escolares novos.
# Professor tinha prazo no mesmo dia e renovação de um dia; renovações não tinham limite.
DEFAULT_RULES = {'estudante':{'maximo':1,'prazo':7,'renovacoes':None,'bloquear_atraso':False},
                 'professor':{'maximo':None,'prazo':0,'renovacoes':None,'bloquear_atraso':False},'retirada_horas':None}


def regras(conn):
    row=conn.execute("SELECT valor FROM Configuracoes WHERE chave='circulacao'").fetchone()
    return json.loads(row[0]) if row else DEFAULT_RULES


def notificar(conn,leitor,evento,mensagem):
    conn.execute('INSERT OR IGNORE INTO Notificacoes(leitor_id,evento,mensagem) VALUES (?,?,?)',(leitor,evento,mensagem))


def distribuir(conn,livro_id):
    """Disponível exclui exemplares separados. Uma fila atende um exemplar por reserva."""
    now=int(time.time())
    for rid,leitor in conn.execute("SELECT id,leitor_id FROM Reservas WHERE livro_id=? AND estado='retirada' AND expira<=?",(livro_id,now)).fetchall():
        conn.execute("UPDATE Reservas SET estado='expirada' WHERE id=?",(rid,))
        conn.execute('UPDATE Livros SET quantidade_disponivel=quantidade_disponivel+1 WHERE id=?',(livro_id,))
        notificar(conn,leitor,f'reserva-expirada:{rid}','O prazo para retirar sua reserva terminou.')
    while True:
        book=conn.execute('SELECT quantidade_disponivel,arquivado,nome FROM Livros WHERE id=?',(livro_id,)).fetchone()
        if not book or book[1] or book[0]<=0:
            break
        candidates=conn.execute("""SELECT r.id,r.leitor_id,u.tipo FROM Reservas r JOIN Usuarios u ON u.id=r.leitor_id
            JOIN Contas c ON c.leitor_id=u.id WHERE r.livro_id=? AND r.estado='fila' AND u.arquivado=0 AND c.ativa=1
            ORDER BY r.criada_em,r.id""",(livro_id,)).fetchall()
        row=None
        policies=regras(conn)
        if policies['retirada_horas'] is None:
            break
        for candidate in candidates:
            policy=policies.get(candidate[2])
            if not policy:
                continue
            active=conn.execute("SELECT COALESCE(SUM(quantidade),0) FROM Emprestimo WHERE usuarios_id=? AND status IN ('Aprovado','Atrasado') AND encerramento IS NULL",(candidate[1],)).fetchone()[0]
            held=conn.execute("SELECT COUNT(*) FROM Reservas WHERE leitor_id=? AND estado='retirada'",(candidate[1],)).fetchone()[0]
            if policy['maximo'] is not None and active+held>=policy['maximo']:
                continue
            if policy['bloquear_atraso'] and conn.execute("SELECT 1 FROM Emprestimo WHERE usuarios_id=? AND status IN ('Aprovado','Atrasado') AND encerramento IS NULL AND data_vencimento<?",(candidate[1],get_brasilia_today().isoformat())).fetchone():
                continue
            row=candidate
            break
        if not row:
            break
        conn.execute("UPDATE Reservas SET estado='retirada',expira=? WHERE id=?",(now+regras(conn)['retirada_horas']*3600,row[0]))
        conn.execute('UPDATE Livros SET quantidade_disponivel=quantidade_disponivel-1 WHERE id=?',(livro_id,))
        notificar(conn,row[1],f'reserva-disponivel:{row[0]}',f'Sua reserva de {book[2]} está disponível para retirada na biblioteca.')


def processar_expiracoes():
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        for (livro,) in conn.execute("SELECT DISTINCT livro_id FROM Reservas WHERE estado IN ('fila','retirada')").fetchall():
            distribuir(conn,livro)
        conn.commit()


def reservar(leitor,livro):
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if regras(conn)['retirada_horas'] is None:
            raise BadRequest('A biblioteca precisa configurar o prazo de retirada antes de receber reservas.')
        distribuir(conn,livro)
        book=conn.execute('SELECT quantidade_disponivel,arquivado FROM Livros WHERE id=?',(livro,)).fetchone()
        if not book or book[1]:
            raise NotFound('Livro indisponível no acervo.')
        if book[0]>0:
            raise BadRequest('Há exemplar disponível. Procure a biblioteca para emprestar.')
        if conn.execute("SELECT 1 FROM Emprestimo WHERE usuarios_id=? AND livros_id=? AND status IN ('Aprovado','Atrasado') AND encerramento IS NULL",(leitor,livro)).fetchone():
            raise BadRequest('Você já possui um empréstimo ativo deste título.')
        cur=conn.execute("INSERT INTO Reservas(leitor_id,livro_id,estado,criada_em) VALUES (?,?,'fila',?)",(leitor,livro,int(time.time())))
        auditar(conn,'reservar',cur.lastrowid)
        conn.commit()
    return {'status':'ok'}


def cancelar_reserva(reserva,leitor=None):
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT leitor_id,livro_id,estado FROM Reservas WHERE id=?',(reserva,)).fetchone()
        if not row or (leitor is not None and row[0]!=leitor):
            raise NotFound('Reserva não encontrada.')
        if row[2] in ('fila','retirada'):
            conn.execute("UPDATE Reservas SET estado='cancelada' WHERE id=?",(reserva,))
            if row[2]=='retirada':
                conn.execute('UPDATE Livros SET quantidade_disponivel=quantidade_disponivel+1 WHERE id=?',(row[1],))
            distribuir(conn,row[1])
            auditar(conn,'cancelar_reserva',reserva)
        conn.commit()
    return {'status':'ok'}


def emprestar(data):
    if not isinstance(data,dict) or not isinstance(data.get('livros'),list) or not data['livros']:
        raise BadRequest('Informe os livros.')
    livros=data['livros']; seen=set()
    for item in livros:
        if not isinstance(item,dict) or type(item.get('id')) is not int or type(item.get('quantidade',1)) is not int or item.get('quantidade',1)<=0 or item['id'] in seen:
            raise BadRequest('Livro ou quantidade inválida.')
        seen.add(item['id'])
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        leitor=data.get('leitor_id')
        confirmation=conn.execute("SELECT valor FROM Configuracoes WHERE chave='exigir_senha_emprestimo'").fetchone()
        if confirmation and confirmation[0] in ('true','1'):
            from utils.auth import verificar_senha_admin
            if not verificar_senha_admin(data.get('senha')):
                raise BadRequest('Confirme a senha atual da sua conta para registrar o empréstimo.')
        if leitor is not None:
            row=conn.execute('SELECT nome,tipo,email FROM Usuarios WHERE id=? AND arquivado=0',(leitor,)).fetchone()
            if not row:
                raise BadRequest('Selecione um leitor ativo.')
            nome,tipo,email=row
        else:
            nome=str(data.get('nome','')).strip(); tipo=data.get('tipo'); email=str(data.get('email') or '').strip().casefold() or None
            if not nome or tipo not in ('estudante','professor'):
                raise BadRequest('Informe nome e categoria do novo leitor.')
            email=email_normalizado(email) if email else None
            if email and conn.execute('SELECT 1 FROM Usuarios WHERE lower(email)=?',(email,)).fetchone():
                raise BadRequest('Este e-mail já está cadastrado. Selecione o leitor na pesquisa.')
            cur=conn.execute('INSERT INTO Usuarios(nome,tipo,email,sala,periodo,materia,telefone) VALUES (?,?,?,?,?,?,?)',(nome,tipo,email,data.get('sala'),data.get('periodo'),data.get('materia'),data.get('telefone')))
            leitor=cur.lastrowid
            auditar(conn,'criar_leitor',leitor)
        policy=regras(conn)[tipo]
        active=conn.execute("SELECT COALESCE(SUM(quantidade),0) FROM Emprestimo WHERE usuarios_id=? AND status IN ('Aprovado','Atrasado') AND encerramento IS NULL",(leitor,)).fetchone()[0]
        if policy['maximo'] is not None and active+sum(i.get('quantidade',1) for i in livros)>policy['maximo']:
            raise BadRequest('Limite de empréstimos desta categoria atingido.')
        hoje=get_brasilia_today()
        if policy['bloquear_atraso'] and conn.execute("SELECT 1 FROM Emprestimo WHERE usuarios_id=? AND status IN ('Aprovado','Atrasado') AND encerramento IS NULL AND data_vencimento<?",(leitor,hoje.isoformat())).fetchone():
            raise BadRequest('Regularize os empréstimos atrasados antes de um novo empréstimo.')
        prazo=data.get('prazo',policy['prazo'])
        try:
            prazo=int(prazo)
        except (ValueError,TypeError):
            raise BadRequest('Prazo inválido.')
        if prazo==0 and tipo=='professor':
            prazo=policy['prazo']
        if not (0 if tipo=='professor' else 1)<=prazo<=365:
            raise BadRequest('Prazo deve ser de 1 a 365 dias.')
        ids=[]
        for item in livros:
            livro=item['id']; qtd=item.get('quantidade',1)
            distribuir(conn,livro)
            book=conn.execute('SELECT quantidade_disponivel,arquivado,nome FROM Livros WHERE id=?',(livro,)).fetchone()
            reserva=conn.execute("SELECT id FROM Reservas WHERE livro_id=? AND leitor_id=? AND estado='retirada'",(livro,leitor)).fetchone()
            livre=qtd-(1 if reserva else 0)
            if not book or book[1] or book[0]<livre:
                raise BadRequest('Não há exemplares livres suficientes. Exemplares reservados não podem ser emprestados a outra pessoa.')
            cur=conn.execute("INSERT INTO Emprestimo(usuarios_id,livros_id,data_emprestimo,data_vencimento,quantidade,status) VALUES (?,?,?,?,?,'Aprovado')",(leitor,livro,hoje.isoformat(),(hoje+timedelta(days=prazo)).isoformat(),qtd))
            ids.append(cur.lastrowid)
            conn.execute('UPDATE Livros SET quantidade_disponivel=quantidade_disponivel-? WHERE id=?',(livre,livro))
            if reserva:
                conn.execute("UPDATE Reservas SET estado='concluida',emprestimo_id=? WHERE id=?",(cur.lastrowid,reserva[0]))
            notificar(conn,leitor,f'emprestimo:{cur.lastrowid}',f'Empréstimo registrado: {book[2]}. Devolução até {(hoje+timedelta(days=prazo)).isoformat()}.')
            auditar(conn,'emprestar',cur.lastrowid)
        conn.commit()
    return {'status':'sucesso','email_enviado':False,'leitor_id':leitor,'emprestimos':ids}


def devolver(id):
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT livros_id,usuarios_id,quantidade,status,encerramento FROM Emprestimo WHERE id=?',(id,)).fetchone()
        if not row:
            raise NotFound('Empréstimo não encontrado.')
        if row[3]=='Devolvido':
            return {'status':'ok'}
        if row[4]:
            raise BadRequest('Este empréstimo foi encerrado por ocorrência. Não repõe estoque por devolução.')
        conn.execute("UPDATE Emprestimo SET status='Devolvido',data_devolucao=? WHERE id=?",(get_brasilia_today().isoformat(),id))
        conn.execute('UPDATE Livros SET quantidade_disponivel=quantidade_disponivel+? WHERE id=?',(row[2],row[0]))
        conn.execute("UPDATE PedidosRenovacao SET estado='cancelado',motivo='Livro devolvido' WHERE emprestimo_id=? AND estado='pendente'",(id,))
        distribuir(conn,row[0])
        notificar(conn,row[1],f'devolucao:{id}','A devolução do seu empréstimo foi registrada.')
        auditar(conn,'devolver',id)
        conn.commit()
    return {'status':'ok'}


def renovar(id):
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute("SELECT e.livros_id,e.usuarios_id,e.data_vencimento,e.renovacoes,u.tipo FROM Emprestimo e JOIN Usuarios u ON u.id=e.usuarios_id WHERE e.id=? AND e.status IN ('Aprovado','Atrasado') AND e.encerramento IS NULL",(id,)).fetchone()
        if not row:
            raise NotFound('Empréstimo ativo não encontrado.')
        policy=regras(conn)[row[4]]
        if policy['renovacoes'] is not None and row[3]>=policy['renovacoes']:
            raise BadRequest('Limite de renovações atingido.')
        if conn.execute("SELECT 1 FROM Reservas WHERE livro_id=? AND estado IN ('fila','retirada')",(row[0],)).fetchone():
            raise BadRequest('Há reservas para este título. A renovação não está disponível.')
        if policy['bloquear_atraso'] and row[2]<get_brasilia_today().isoformat():
            raise BadRequest('Regularize o empréstimo atrasado na biblioteca.')
        nova=max(date.fromisoformat(row[2]),get_brasilia_today())+timedelta(days=max(1,policy['prazo']))
        conn.execute("UPDATE Emprestimo SET data_vencimento=?,status='Aprovado',renovacoes=renovacoes+1,notificacao_3dias=0,notificacao_hoje=0 WHERE id=?",(nova.isoformat(),id))
        conn.execute("UPDATE PedidosRenovacao SET estado='aprovado' WHERE emprestimo_id=? AND estado='pendente'",(id,))
        notificar(conn,row[1],f'renovacao:{id}:{row[3]+1}',f'Renovação aprovada. Novo prazo: {nova.isoformat()}.')
        auditar(conn,'renovar',id)
        conn.commit()
    return {'status':'ok','nova_data':nova.isoformat()}


def arquivar(tabela,id):
    if tabela not in ('Livros','Usuarios'):
        raise BadRequest()
    coluna='livros_id' if tabela=='Livros' else 'usuarios_id'
    reserva_col='livro_id' if tabela=='Livros' else 'leitor_id'
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute(f"SELECT 1 FROM Emprestimo WHERE {coluna}=? AND status IN ('Aprovado','Atrasado') AND encerramento IS NULL",(id,)).fetchone() or conn.execute(f"SELECT 1 FROM Reservas WHERE {reserva_col}=? AND estado IN ('fila','retirada')",(id,)).fetchone():
            raise BadRequest('Resolva os empréstimos e reservas pendentes antes de arquivar.')
        if tabela=='Usuarios':
            account=conn.execute('SELECT id,papel,ativa FROM Contas WHERE leitor_id=?',(id,)).fetchone()
            if account and account[1]=='bibliotecario' and account[2] and conn.execute("SELECT COUNT(*) FROM Contas WHERE papel='bibliotecario' AND ativa=1").fetchone()[0]<=1:
                raise BadRequest('Não é possível arquivar o último bibliotecário ativo.')
            conn.execute('UPDATE Contas SET ativa=0,versao_sessao=versao_sessao+1 WHERE leitor_id=?',(id,))
            conn.execute('UPDATE Codigos SET consumido=1 WHERE leitor_id=?',(id,))
        conn.execute(f'UPDATE {tabela} SET arquivado=1 WHERE id=?',(id,))
        auditar(conn,'arquivar',f'{tabela}:{id}')
        conn.commit()
    return {'status':'ok'}
