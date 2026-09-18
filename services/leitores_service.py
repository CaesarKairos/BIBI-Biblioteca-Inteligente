from database.database import db_manager
import uuid


def api_leitores():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome, tipo, email, sala, periodo, materia, telefone FROM Usuarios WHERE tipo != "bibliotecario"')
    leitores = []
    for row in cursor.fetchall():
        leitores.append({
            "id": row[0], "nome": row[1], "tipo": row[2], "email": row[3],
            "sala": row[4], "periodo": row[5], "materia": row[6], "telefone": row[7]
        })
    conn.close()
    return leitores


def buscar_leitor(query):
    q = query.get('q', '').strip()
    if not q or len(q) < 2:
        return []
    conn = db_manager.get_connection()
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
    conn.close()
    return leitores


def criar_leitor(data):
    conn = db_manager.get_connection()
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
    conn.close()
    return {"status": "ok"}, 201


def editar_leitor(id, data):
    conn = db_manager.get_connection()
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
    conn.close()
    return {"status": "ok"}


def excluir_leitor(id):
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Usuarios WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}
