from database.database import db_manager
from datetime import datetime
from datetime import timedelta
from services.configuracoes_service import is_email_blocked
from services.configuracoes_service import is_exigir_senha_emprestimo
from services.email_service import enviar_email_confirmacao
from services.email_service import enviar_email_devolucao
from services.email_service import enviar_email_renovacao
from services.email_service import atualizar_atrasos
from utils.auth import verificar_senha_admin
from utils.datetime import get_brasilia_today
import threading
import logging

logger = logging.getLogger(__name__)
import uuid


def realizar_emprestimo(data):
    from services.circulacao_service import emprestar
    return emprestar(data)


def contar_emprestimos_ativos():
    atualizar_atrasos()
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Emprestimo WHERE encerramento IS NULL AND status IN ('Aprovado', 'Atrasado')")
        count = cursor.fetchone()[0]
        return {"count": count}


def listar_emprestimos_ativos():
    atualizar_atrasos()
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.id, u.nome as leitor, u.sala as serie, u.telefone, l.nome as livro, l.capa_url, e.data_emprestimo, e.data_vencimento, e.quantidade, COALESCE(e.encerramento,e.status)
            FROM Emprestimo e
            JOIN Usuarios u ON e.usuarios_id = u.id
            JOIN Livros l ON e.livros_id = l.id
            WHERE e.encerramento IS NULL AND e.status IN ('Aprovado', 'Atrasado')
            ORDER BY e.data_vencimento
        ''')
        emprestimos = []
        for row in cursor.fetchall():
            emprestimos.append({
                "id": row[0], "leitor": row[1], "serie": row[2] or '', "telefone": row[3] or '',
                "livro": row[4], "capa": row[5], "data_emprestimo": row[6],
                "data_vencimento": row[7], "quantidade": row[8], "status": row[9]
            })
        return emprestimos


def listar_todos_emprestimos():
    atualizar_atrasos()
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.id, u.nome as leitor, u.sala as serie, u.telefone, l.nome as livro, l.capa_url, e.data_emprestimo, e.data_vencimento, e.quantidade, COALESCE(e.encerramento,e.status)
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
        return emprestimos


def listar_emprestimos_devolvidos():
    with db_manager.connection() as conn:
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
        return emprestimos


def listar_devolucoes_hoje():
    atualizar_atrasos()
    hoje = get_brasilia_today().isoformat()
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.id, u.nome as leitor, u.sala as serie, u.telefone, l.nome as livro, l.capa_url, e.data_vencimento
            FROM Emprestimo e
            JOIN Usuarios u ON e.usuarios_id = u.id
            JOIN Livros l ON e.livros_id = l.id
            WHERE e.encerramento IS NULL AND e.status IN ('Aprovado', 'Atrasado') AND e.data_vencimento = ?
        ''', (hoje,))
        devolucoes = []
        for row in cursor.fetchall():
            devolucoes.append({
                "id": row[0], "leitor": row[1], "serie": row[2] or '', "telefone": row[3] or '',
                "livro": row[4], "capa": row[5], "vencimento": row[6]
            })
        return devolucoes


def listar_atrasos():
    atualizar_atrasos()
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.id, u.nome as leitor, u.sala as serie, u.telefone, l.nome as livro, l.capa_url, e.data_vencimento
            FROM Emprestimo e
            JOIN Usuarios u ON e.usuarios_id = u.id
            JOIN Livros l ON e.livros_id = l.id
            WHERE e.encerramento IS NULL AND e.status = 'Atrasado'
        ''')
        atrasos = []
        for row in cursor.fetchall():
            atrasos.append({
                "id": row[0], "leitor": row[1], "serie": row[2] or '', "telefone": row[3] or '',
                "livro": row[4], "capa": row[5], "vencimento": row[6]
            })
        return atrasos


def devolver_emprestimo(id):
    from services.circulacao_service import devolver
    return devolver(id)


def renovar_emprestimo(id):
    from services.circulacao_service import renovar
    return renovar(id)


def listar_mais_emprestados():
    with db_manager.connection() as conn:
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
        return destaques


def listar_ativos_por_genero():
    with db_manager.connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT l.categoria, COUNT(*) as total
            FROM Emprestimo e
            JOIN Livros l ON e.livros_id = l.id
            WHERE e.encerramento IS NULL AND e.status IN ('Aprovado', 'Atrasado')
            GROUP BY l.categoria
            ORDER BY total DESC
        ''')
        generos = []
        for row in cursor.fetchall():
            generos.append({
                "categoria": row[0],
                "total": row[1]
            })
        return generos


def listar_historico_por_genero():
    with db_manager.connection() as conn:
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
        return generos


def listar_ranking_leitores():
    with db_manager.connection() as conn:
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
        return ranking


def listar_livros_adormecidos():
    with db_manager.connection() as conn:
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
        return adormecidos
