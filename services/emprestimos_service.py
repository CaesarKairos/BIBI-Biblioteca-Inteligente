from database.database import db_manager
from datetime import datetime
from datetime import timedelta
from services.configuracoes_service import is_email_blocked
from services.configuracoes_service import is_exigir_senha_emprestimo
from services.email_service import enviar_email_confirmacao
from services.email_service import enviar_email_devolucao
from services.email_service import enviar_email_renovacao
from services.email_service import verificar_e_enviar_notificacoes
from utils.auth import verificar_senha_admin
from utils.datetime import get_brasilia_today
import threading
import uuid


def realizar_emprestimo(data):
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()

        tipo = data.get('tipo')
        nome = data.get('nome')
        email = data.get('email')
        sala = data.get('sala')
        periodo = data.get('periodo')
        materia = data.get('materia')
        prazo_str = data.get('prazo', '7')
        livros = data.get('livros', [])
        telefone = data.get('telefone')
        senha_fornecida = data.get('senha', None)

        if not tipo or not nome:
            return {"erro": "Nome e tipo são obrigatórios."}, 400
        if tipo not in ('estudante', 'professor'):
            return {"erro": "Tipo de leitor inválido."}, 400

        if tipo == 'professor' and not email:
            email = f"professor_{uuid.uuid4().hex[:8]}@bibi.local"
        elif not email:
            return {"erro": "E-mail é obrigatório para estudantes."}, 400

        if is_exigir_senha_emprestimo():
            if not senha_fornecida or not verificar_senha_admin(senha_fornecida):
                return {"erro": "Senha de administrador necessária para realizar empréstimos."}, 403

        try:
            prazo = int(prazo_str) if tipo == 'estudante' else 0
        except:
            prazo = 7 if tipo == 'estudante' else 0

        if tipo == 'estudante':
            if len(livros) > 1:
                return {"erro": "Estudante pode emprestar apenas um livro por vez."}, 400
            cursor.execute('''
                SELECT COUNT(*) FROM Emprestimo e
                JOIN Usuarios u ON e.usuarios_id = u.id
                WHERE u.email = ? AND e.status IN ('Aprovado', 'Atrasado')
            ''', (email,))
            if cursor.fetchone()[0] > 0:
                return {"erro": "Este e-mail já possui um livro emprestado."}, 400

        cursor.execute('SELECT id, nome, sala, periodo, materia, telefone FROM Usuarios WHERE email = ? AND tipo = ?', (email, tipo))
        user = cursor.fetchone()
        user_id = None
        if user:
            user_id = user[0]
            updates = []
            params = []
            if user[1] != nome:
                updates.append("nome = ?")
                params.append(nome)
            if tipo == 'estudante':
                if sala is not None and user[2] != sala:
                    updates.append("sala = ?")
                    params.append(sala)
                if periodo is not None and user[3] != periodo:
                    updates.append("periodo = ?")
                    params.append(periodo)
                if telefone is not None and user[5] != telefone:
                    updates.append("telefone = ?")
                    params.append(telefone)
            else:
                if materia is not None and user[4] != materia:
                    updates.append("materia = ?")
                    params.append(materia)
                if telefone is not None and user[5] != telefone:
                    updates.append("telefone = ?")
                    params.append(telefone)

            if updates:
                query = f"UPDATE Usuarios SET {', '.join(updates)} WHERE id = ?"
                params.append(user_id)
                cursor.execute(query, params)
        else:
            cursor.execute('''
                INSERT INTO Usuarios (nome, tipo, email, sala, periodo, materia, telefone)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (nome, tipo, email, sala, periodo, materia, telefone))
            user_id = cursor.lastrowid

        hoje = get_brasilia_today()
        vencimento = hoje + timedelta(days=prazo)

        for item in livros:
            livro_id = item.get('id')
            qtd = item.get('quantidade', 1)
            if not livro_id:
                return {"erro": "ID do livro não informado."}, 400
            cursor.execute('SELECT quantidade_disponivel FROM Livros WHERE id = ?', (livro_id,))
            disp = cursor.fetchone()
            if not disp or disp[0] < qtd:
                conn.rollback()
                conn.close()
                return {"erro": f"Quantidade insuficiente para o livro ID {livro_id}."}, 400

        for item in livros:
            livro_id = item['id']
            qtd = item.get('quantidade', 1)
            cursor.execute('''
                INSERT INTO Emprestimo (usuarios_id, livros_id, data_emprestimo, data_vencimento, quantidade, status, notificacao_3dias, notificacao_hoje)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, livro_id, hoje.isoformat(), vencimento.isoformat(), qtd, 'Aprovado', 0, 0))
            cursor.execute('UPDATE Livros SET quantidade_disponivel = quantidade_disponivel - ? WHERE id = ?', (qtd, livro_id))

        conn.commit()

        cursor.execute('SELECT nome, capa_url FROM Livros WHERE id = ?', (livros[0]['id'],))
        livro_info = cursor.fetchone()
        titulo = livro_info[0]
        capa_url = livro_info[1]
        conn.close()

        if email and '@' in email and not is_email_blocked():
            threading.Thread(target=enviar_email_confirmacao, args=(email, nome, titulo, vencimento.strftime("%d/%m/%Y"), capa_url)).start()

        return {"status": "sucesso", "email_enviado": True}

    except Exception as e:
        print(f"Erro detalhado no empréstimo: {e}")
        return {"erro": f"Falha no servidor: {str(e)}"}, 500


def contar_emprestimos_ativos():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Emprestimo WHERE status IN ('Aprovado', 'Atrasado')")
    count = cursor.fetchone()[0]
    conn.close()
    return {"count": count}


def listar_emprestimos_ativos():
    threading.Thread(target=verificar_e_enviar_notificacoes).start()
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.id, u.nome as leitor, u.sala as serie, u.telefone, l.nome as livro, l.capa_url, e.data_emprestimo, e.data_vencimento, e.quantidade, e.status
        FROM Emprestimo e
        JOIN Usuarios u ON e.usuarios_id = u.id
        JOIN Livros l ON e.livros_id = l.id
        WHERE e.status IN ('Aprovado', 'Atrasado')
        ORDER BY e.data_vencimento
    ''')
    emprestimos = []
    for row in cursor.fetchall():
        emprestimos.append({
            "id": row[0], "leitor": row[1], "serie": row[2] or '', "telefone": row[3] or '',
            "livro": row[4], "capa": row[5], "data_emprestimo": row[6],
            "data_vencimento": row[7], "quantidade": row[8], "status": row[9]
        })
    conn.close()
    return emprestimos


def listar_todos_emprestimos():
    threading.Thread(target=verificar_e_enviar_notificacoes).start()
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.id, u.nome as leitor, u.sala as serie, u.telefone, l.nome as livro, l.capa_url, e.data_emprestimo, e.data_vencimento, e.quantidade, e.status
        FROM Emprestimo e
        JOIN Usuarios u ON e.usuarios_id = u.id
        JOIN Livros l ON e.livros_id = l.id
        ORDER BY e.data_vencimento DESC
    ''')
    emprestimos = []
    for row in cursor.fetchall():
        emprestimos.append({
            "id": row[0], "leitor": row[1], "serie": row[2] or '', "telefone": row[3] or '',
            "livro": row[4], "capa": row[5], "data_emprestimo": row[6],
            "data_vencimento": row[7], "quantidade": row[8], "status": row[9]
        })
    conn.close()
    return emprestimos


def listar_emprestimos_devolvidos():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.id, u.nome as leitor, u.sala as serie, u.telefone, l.nome as livro, l.capa_url, e.data_emprestimo, e.data_vencimento, e.data_devolucao, e.quantidade, e.status
        FROM Emprestimo e
        JOIN Usuarios u ON e.usuarios_id = u.id
        JOIN Livros l ON e.livros_id = l.id
        WHERE e.status = 'Devolvido'
        ORDER BY e.data_devolucao DESC
    ''')
    emprestimos = []
    for row in cursor.fetchall():
        emprestimos.append({
            "id": row[0], "leitor": row[1], "serie": row[2] or '', "telefone": row[3] or '',
            "livro": row[4], "capa": row[5], "data_emprestimo": row[6],
            "data_vencimento": row[7], "data_devolucao": row[8], "quantidade": row[9], "status": row[10]
        })
    conn.close()
    return emprestimos


def listar_devolucoes_hoje():
    hoje = get_brasilia_today().isoformat()
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.id, u.nome as leitor, u.sala as serie, u.telefone, l.nome as livro, l.capa_url, e.data_vencimento
        FROM Emprestimo e
        JOIN Usuarios u ON e.usuarios_id = u.id
        JOIN Livros l ON e.livros_id = l.id
        WHERE e.status IN ('Aprovado', 'Atrasado') AND e.data_vencimento = ?
    ''', (hoje,))
    devolucoes = []
    for row in cursor.fetchall():
        devolucoes.append({
            "id": row[0], "leitor": row[1], "serie": row[2] or '', "telefone": row[3] or '',
            "livro": row[4], "capa": row[5], "vencimento": row[6]
        })
    conn.close()
    return devolucoes


def listar_atrasos():
    threading.Thread(target=verificar_e_enviar_notificacoes).start()
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.id, u.nome as leitor, u.sala as serie, u.telefone, l.nome as livro, l.capa_url, e.data_vencimento
        FROM Emprestimo e
        JOIN Usuarios u ON e.usuarios_id = u.id
        JOIN Livros l ON e.livros_id = l.id
        WHERE e.status = 'Atrasado'
    ''')
    atrasos = []
    for row in cursor.fetchall():
        atrasos.append({
            "id": row[0], "leitor": row[1], "serie": row[2] or '', "telefone": row[3] or '',
            "livro": row[4], "capa": row[5], "vencimento": row[6]
        })
    conn.close()
    return atrasos


def devolver_emprestimo(id):
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT livros_id, usuarios_id, quantidade FROM Emprestimo WHERE id = ?', (id,))
    emp = cursor.fetchone()
    if not emp:
        conn.close()
        return {"erro": "Empréstimo não encontrado"}, 404
    livro_id, user_id, qtd = emp
    hoje = get_brasilia_today().isoformat()
    cursor.execute('''
        UPDATE Emprestimo
        SET status = 'Devolvido', data_devolucao = ?
        WHERE id = ?
    ''', (hoje, id))
    cursor.execute('UPDATE Livros SET quantidade_disponivel = quantidade_disponivel + ? WHERE id = ?', (qtd, livro_id))
    conn.commit()

    cursor.execute('SELECT nome, email FROM Usuarios WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    cursor.execute('SELECT nome, capa_url FROM Livros WHERE id = ?', (livro_id,))
    livro_info = cursor.fetchone()
    livro_nome = livro_info[0]
    capa_url = livro_info[1]
    conn.close()

    if user and user[1] and '@' in user[1] and not is_email_blocked():
        threading.Thread(target=enviar_email_devolucao, args=(user[1], user[0], livro_nome, hoje, capa_url)).start()

    return {"status": "ok"}


def renovar_emprestimo(id):
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.data_vencimento, u.tipo, u.email, u.nome, l.nome as livro_titulo, l.capa_url
        FROM Emprestimo e
        JOIN Usuarios u ON e.usuarios_id = u.id
        JOIN Livros l ON e.livros_id = l.id
        WHERE e.id = ? AND e.status IN ('Aprovado', 'Atrasado')
    ''', (id,))
    emp = cursor.fetchone()
    if not emp:
        conn.close()
        return {"erro": "Empréstimo não encontrado ou já devolvido."}, 404

    data_venc_str, tipo, email, nome, titulo, capa_url = emp
    data_venc = datetime.strptime(data_venc_str, "%Y-%m-%d").date()
    hoje = get_brasilia_today()
    if data_venc < hoje:
        data_venc = hoje
    dias_extras = 7 if tipo == 'estudante' else 1
    nova_data = data_venc + timedelta(days=dias_extras)

    cursor.execute('''
        UPDATE Emprestimo
        SET data_vencimento = ?, status = 'Aprovado', notificacao_3dias = 0, notificacao_hoje = 0
        WHERE id = ?
    ''', (nova_data.isoformat(), id))
    conn.commit()
    conn.close()

    if email and '@' in email and not is_email_blocked():
        threading.Thread(target=enviar_email_renovacao, args=(email, nome, titulo, nova_data.strftime("%d/%m/%Y"), capa_url)).start()

    return {"status": "ok", "nova_data": nova_data.isoformat()}


def listar_mais_emprestados():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT l.id, l.nome, l.autor, l.capa_url, COUNT(e.id) as total_emprestimos
        FROM Emprestimo e
        JOIN Livros l ON e.livros_id = l.id
        GROUP BY l.id
        ORDER BY total_emprestimos DESC
        LIMIT 5
    ''')
    destaques = []
    for row in cursor.fetchall():
        destaques.append({
            "id": row[0],
            "titulo": row[1],
            "autor": row[2],
            "capa": row[3],
            "total_emprestimos": row[4]
        })
    conn.close()
    return destaques


def listar_ativos_por_genero():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT l.categoria, COUNT(*) as total
        FROM Emprestimo e
        JOIN Livros l ON e.livros_id = l.id
        WHERE e.status IN ('Aprovado', 'Atrasado')
        GROUP BY l.categoria
        ORDER BY total DESC
    ''')
    generos = []
    for row in cursor.fetchall():
        generos.append({
            "categoria": row[0],
            "total": row[1]
        })
    conn.close()
    return generos


def listar_historico_por_genero():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT l.categoria, COUNT(*) as total
        FROM Emprestimo e
        JOIN Livros l ON e.livros_id = l.id
        GROUP BY l.categoria
        ORDER BY total DESC
    ''')
    generos = []
    for row in cursor.fetchall():
        generos.append({
            "categoria": row[0],
            "total": row[1]
        })
    conn.close()
    return generos


def listar_ranking_leitores():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    tres_meses_atras = (get_brasilia_today() - timedelta(days=90)).isoformat()
    cursor.execute('''
        SELECT u.nome, u.sala, u.tipo, COUNT(e.id) as total
        FROM Emprestimo e
        JOIN Usuarios u ON e.usuarios_id = u.id
        WHERE e.data_emprestimo >= ?
        GROUP BY u.id
        ORDER BY total DESC
    ''', (tres_meses_atras,))
    ranking = []
    for row in cursor.fetchall():
        ranking.append({
            "nome": row[0],
            "sala": row[1] or '',
            "tipo": row[2],
            "total": row[3]
        })
    conn.close()
    return ranking


def listar_livros_adormecidos():
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT l.id, l.nome, l.autor, l.capa_url
        FROM Livros l
        WHERE l.data_cadastro <= date('now', '-6 months')
        AND l.id NOT IN (
            SELECT DISTINCT e.livros_id 
            FROM Emprestimo e 
            WHERE e.data_emprestimo >= date('now', '-6 months')
        )
    ''')
    adormecidos = []
    for row in cursor.fetchall():
        adormecidos.append({
            "id": row[0],
            "titulo": row[1],
            "autor": row[2],
            "capa": row[3]
        })
    conn.close()
    return adormecidos
