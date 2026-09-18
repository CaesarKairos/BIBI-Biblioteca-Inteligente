from database.database import db_manager
from datetime import datetime
from services.configuracoes_service import is_bloquear_excluir_agendamento
from services.configuracoes_service import is_exigir_senha_agendamento
from utils.auth import verificar_senha_admin
from utils.datetime import get_brasilia_today


def api_agendamentos(query):
    periodo = query.get('periodo')
    data = query.get('data')
    conn = db_manager.get_connection()
    cursor = conn.cursor()

    if data:
        if periodo:
            cursor.execute('''
                SELECT id, data, periodo, dia_semana, aula, professor, materia, uso, turma
                FROM Agendamento WHERE data = ? AND periodo = ?
            ''', (data, periodo))
        else:
            cursor.execute('''
                SELECT id, data, periodo, dia_semana, aula, professor, materia, uso, turma
                FROM Agendamento WHERE data = ?
            ''', (data,))
    else:
        cursor.execute('''
            SELECT id, data, periodo, dia_semana, aula, professor, materia, uso, turma
            FROM Agendamento WHERE periodo = ?
        ''', (periodo or 'Manhã',))

    agendamentos = []
    for row in cursor.fetchall():
        agendamentos.append({
            "id": row[0],
            "data": row[1],
            "periodo": row[2],
            "dia": row[3],
            "aula": row[4],
            "professor": row[5],
            "materia": row[6],
            "uso": row[7],
            "turma": row[8]
        })
    conn.close()
    return agendamentos


def datas_com_agendamentos():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    hoje = get_brasilia_today().isoformat()
    # Retorna um agendamento representativo (o de menor id) para cada uma das próximas
    # 5 datas com agendamento, incluindo periodo/aula, para permitir que a interface
    # navegue diretamente até o período e destaque a célula correspondente.
    cursor.execute('''
        SELECT a.id, a.data, a.periodo, a.aula, a.professor, a.materia
        FROM Agendamento a
        INNER JOIN (
            SELECT data, MIN(id) as min_id
            FROM Agendamento
            WHERE date(data) >= date(?)
            GROUP BY data
            ORDER BY data
            LIMIT 5
        ) sub ON a.id = sub.min_id
        ORDER BY a.data
    ''', (hoje,))
    proximos = []
    for row in cursor.fetchall():
        proximos.append({
            "id": row[0],
            "data": row[1],
            "periodo": row[2],
            "aula": row[3],
            "professor": row[4],
            "materia": row[5]
        })
    conn.close()
    return proximos


def agendamentos_passados():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    hoje = get_brasilia_today().isoformat()
    cursor.execute('''
        SELECT id, data, periodo, dia_semana, aula, professor, materia, uso, turma
        FROM Agendamento 
        WHERE date(data) < date(?)
        ORDER BY data DESC
        LIMIT 5
    ''', (hoje,))
    passados = []
    for row in cursor.fetchall():
        passados.append({
            "id": row[0],
            "data": row[1],
            "periodo": row[2],
            "dia": row[3],
            "aula": row[4],
            "professor": row[5],
            "materia": row[6],
            "uso": row[7],
            "turma": row[8]
        })
    conn.close()
    return passados


def criar_agendamento(data):
    data_ag = data.get('data')
    if data_ag:
        data_date = datetime.strptime(data_ag, "%Y-%m-%d").date()
        hoje = get_brasilia_today()
        if data_date < hoje:
            return {"erro": "Não é possível criar agendamentos em datas passadas."}, 400

    senha_fornecida = data.get('senha', None)
    if is_exigir_senha_agendamento():
        if not senha_fornecida or not verificar_senha_admin(senha_fornecida):
            return {"erro": "Senha de administrador necessária para criar agendamentos."}, 403

    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Agendamento (data, periodo, dia_semana, aula, professor, materia, uso, turma)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('data'),
        data['periodo'],
        data['dia'],
        data['aula'],
        data['professor'],
        data['materia'],
        data['uso'],
        data.get('turma', '')
    ))
    conn.commit()
    novo_id = cursor.lastrowid
    conn.close()
    return {"id": novo_id, "status": "ok"}, 201


def excluir_agendamento(id):
    if is_bloquear_excluir_agendamento():
        return {"erro": "Exclusão de agendamentos está bloqueada nas configurações."}, 403
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Agendamento WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}
