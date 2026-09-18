from database.database import db_manager
import uuid


def api_leitores():
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, nome, tipo, email, sala, periodo, materia, telefone FROM Usuarios WHERE tipo != "bibliotecario"')
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
                          WHERE tipo != "bibliotecario" AND nome LIKE ? 
                          ORDER BY nome LIMIT 10''', (f'%{q}%',))
        leitores = []
        for row in cursor.fetchall():
            leitores.append({
                "id": row[0], "nome": row[1], "tipo": row[2], "email": row[3],
                "sala": row[4], "periodo": row[5], "materia": row[6], "telefone": row[7]
            })
        return leitores


def criar_leitor(data):
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        email = data.get('email')
        if data['tipo'] == 'professor' and not email:
            email = f"professor_{uuid.uuid4().hex[:8]}@bibi.local"
        cursor.execute('''
            INSERT INTO Usuarios (nome, tipo, email, sala, periodo, materia, telefone)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data['nome'], data['tipo'], email, data.get('sala'),
              data.get('periodo'), data.get('materia'), data.get('telefone')))
        conn.commit()
        return {"status": "ok"}, 201


def editar_leitor(id, data):
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        email = data.get('email')
        if data['tipo'] == 'professor' and not email:
            email = f"professor_{uuid.uuid4().hex[:8]}@bibi.local"
        cursor.execute('''
            UPDATE Usuarios
            SET nome = ?, tipo = ?, email = ?, sala = ?, periodo = ?, materia = ?, telefone = ?
            WHERE id = ?
        ''', (data['nome'], data['tipo'], email, data.get('sala'),
              data.get('periodo'), data.get('materia'), data.get('telefone'), id))
        conn.commit()
        return {"status": "ok"}


def excluir_leitor(id):
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM Usuarios WHERE id = ?', (id,))
        conn.commit()
        return {"status": "ok"}
