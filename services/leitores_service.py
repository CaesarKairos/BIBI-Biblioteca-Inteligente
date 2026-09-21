from database.database import db_manager
import uuid
from services.contas_service import auditar,email_normalizado


def api_leitores():
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, nome, tipo, email, sala, periodo, materia, telefone FROM Usuarios WHERE tipo != "bibliotecario" AND arquivado=0 ORDER BY nome,id')
        leitores = []
        for row in cursor.fetchall():
            leitores.append({
                "id": row[0], "nome": row[1], "tipo": row[2], "email": row[3],
                "sala": row[4], "periodo": row[5], "materia": row[6], "telefone": row[7]
            })
        return leitores


def buscar_leitor(query):
    q = query.get('q', '').strip()
    if not q or len(q) < 2:
        return []
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT id, nome, tipo, email, sala, periodo, materia, telefone 
                          FROM Usuarios 
                          WHERE tipo != "bibliotecario" AND arquivado=0 AND nome LIKE ?
                          ORDER BY nome LIMIT 10''', (f'%{q}%',))
        leitores = []
        for row in cursor.fetchall():
            leitores.append({
                "id": row[0], "nome": row[1], "tipo": row[2], "email": row[3],
                "sala": row[4], "periodo": row[5], "materia": row[6], "telefone": row[7]
            })
        return leitores


def criar_leitor(data):
    if not isinstance(data,dict) or data.get('tipo') not in ('estudante','professor') or not str(data.get('nome','')).strip():
        return {'erro':'Informe nome e categoria estudante ou professor.'},400
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        email = data.get('email')
        email = email_normalizado(email) if email else None
        if email and conn.execute('SELECT 1 FROM Usuarios WHERE lower(email)=?',(email,)).fetchone():
            return {'erro':'Este e-mail já está vinculado a um leitor.'},409
        cursor.execute('''
            INSERT INTO Usuarios (nome, tipo, email, sala, periodo, materia, telefone)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data['nome'], data['tipo'], email, data.get('sala'),
              data.get('periodo'), data.get('materia'), data.get('telefone')))
        leitor_id=cursor.lastrowid
        auditar(conn,'criar_leitor',leitor_id)
        conn.commit()
        return {"status": "ok",'id':leitor_id}, 201


def editar_leitor(id, data):
    if not isinstance(data,dict) or data.get('tipo') not in ('estudante','professor') or not str(data.get('nome','')).strip():
        return {'erro':'Informe nome e categoria estudante ou professor.'},400
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        conn.execute('BEGIN IMMEDIATE')
        email = data.get('email')
        email = email_normalizado(email) if email else None
        previous=conn.execute('SELECT email,tipo FROM Usuarios WHERE id=? AND arquivado=0',(id,)).fetchone()
        if not previous:
            return {'erro':'Leitor não encontrado.'},404
        if email and conn.execute('SELECT 1 FROM Usuarios WHERE lower(email)=? AND id!=?',(email,id)).fetchone():
            return {'erro':'Este e-mail já está vinculado a outro leitor.'},409
        account=conn.execute('SELECT id FROM Contas WHERE leitor_id=?',(id,)).fetchone()
        if account and not email:
            return {'erro':'Uma conta ativa precisa de e-mail de acesso.'},400
        if previous[0]!=email:
            conn.execute('UPDATE Codigos SET consumido=1 WHERE leitor_id=?',(id,))
            conn.execute('UPDATE Contas SET email=?,email_verificado=0,versao_sessao=versao_sessao+1 WHERE leitor_id=?',(email,id))
        cursor.execute('''
            UPDATE Usuarios
            SET nome = ?, tipo = ?, email = ?, sala = ?, periodo = ?, materia = ?, telefone = ?
            WHERE id = ?
        ''', (data['nome'], data['tipo'], email, data.get('sala'),
              data.get('periodo'), data.get('materia'), data.get('telefone'), id))
        conn.execute('UPDATE Contas SET nome=? WHERE leitor_id=?',(data['nome'],id))
        auditar(conn,'editar_leitor',id,motivo='categoria alterada' if previous[1]!=data['tipo'] else 'dados administrativos')
        conn.commit()
        return {"status": "ok"}


def excluir_leitor(id):
    from services.circulacao_service import arquivar
    return arquivar('Usuarios',id)
