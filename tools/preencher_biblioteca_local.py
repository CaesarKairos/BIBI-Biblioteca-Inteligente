"""Preenche a instalação local com acervo e histórico; cria backup antes de gravar."""
import argparse
import getpass
import json
import sqlite3
import time
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', required=True)
    parser.add_argument('--email', required=True)
    parser.add_argument('--senha')
    args = parser.parse_args()
    password = args.senha or getpass.getpass('Senha do aluno: ')
    path = Path(args.db)
    if not path.is_file():
        raise RuntimeError('Banco não encontrado.')
    conn = sqlite3.connect(path, timeout=30)
    conn.execute('PRAGMA foreign_keys=ON')
    backup = path.parent / 'backups' / ('Biblioteca-antes-preenchimento-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.db')
    backup.parent.mkdir(exist_ok=True)
    with sqlite3.connect(backup) as target:
        conn.backup(target)
    today = date(2026, 10, 20)
    now = int(time.time())
    counts = {}
    def norm(s):
        return ''.join(c for c in unicodedata.normalize('NFD', s.casefold().strip()) if not unicodedata.combining(c))
    books = [
        ('A Hora da Estrela', 'Clarice Lispector', 'Ficção', 'Uma jovem nordestina busca seu lugar no Rio de Janeiro.', 'identidade, literatura brasileira'),
        ('O Alienista', 'Machado de Assis', 'Ficção', 'Um médico transforma a vida de uma cidade ao investigar os limites da razão.', 'ciência, sociedade, sátira'),
        ('Capitães da Areia', 'Jorge Amado', 'Ficção', 'A vida e os vínculos de um grupo de meninos nas ruas de Salvador.', 'juventude, desigualdade, amizade'),
        ('Vidas Secas', 'Graciliano Ramos', 'Ficção', 'Uma família enfrenta a seca e a dureza da vida no sertão.', 'sertão, família, desigualdade'),
        ('A Ilha do Tesouro', 'Robert Louis Stevenson', 'Ficção', 'Um mapa leva um jovem a uma aventura entre piratas e tesouros.', 'aventura, coragem, piratas'),
        ('A Volta ao Mundo em Oitenta Dias', 'Júlio Verne', 'Ficção', 'Uma aposta inicia uma viagem extraordinária ao redor do mundo.', 'viagem, aventura, geografia'),
        ('Quarto de Despejo', 'Carolina Maria de Jesus', 'Não-ficção', 'Registros do cotidiano e da luta pela sobrevivência na favela do Canindé.', 'memória, sociedade, Brasil'),
        ('Uma Breve História do Tempo', 'Stephen Hawking', 'Não-ficção', 'Uma introdução às grandes perguntas sobre o tempo e o universo.', 'ciência, física, universo'),
        ('O Mundo Assombrado pelos Demônios', 'Carl Sagan', 'Não-ficção', 'Reflexões sobre ciência, curiosidade e pensamento crítico.', 'ciência, pensamento crítico'),
        ('Marília de Dirceu', 'Tomás Antônio Gonzaga', 'Poesia', 'Liras que exploram o amor e os ideais do Arcadismo brasileiro.', 'amor, arcadismo'),
        ('Eu', 'Augusto dos Anjos', 'Poesia', 'Poemas sobre a existência, a matéria e a condição humana.', 'existência, literatura brasileira'),
        ('Laços', 'Vitor Cafaggi e Lu Cafaggi', 'Quadrinhos', 'Uma aventura da Turma da Mônica sobre amizade e companheirismo.', 'amizade, aventura, infância'),
    ]
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        email = args.email.strip().casefold()
        if conn.execute('SELECT 1 FROM Contas WHERE email=?', (email,)).fetchone():
            raise RuntimeError('A conta já existe; nenhuma alteração foi gravada.')
        reader = conn.execute('SELECT id FROM Usuarios WHERE lower(email)=?', (email,)).fetchone()
        uid = reader[0] if reader else conn.execute("INSERT INTO Usuarios(nome,tipo,email,sala,periodo) VALUES (?,'estudante',?,'3º A','Manhã')", ('César Batista Santos', email)).lastrowid
        cid = conn.execute("INSERT INTO Contas(leitor_id,nome,email,senha_hash,papel,ativacao,onboarding_concluido_em) VALUES (?,?,?,?,'leitor','presencial',CURRENT_TIMESTAMP)", (uid, 'César Batista Santos', email, generate_password_hash(password, method='scrypt'))).lastrowid
        existing = {norm(name): bid for bid, name in conn.execute('SELECT id,nome FROM Livros WHERE arquivado=0')}
        added = 0
        for title, author, category, description, themes in books:
            if norm(title) in existing:
                continue
            bid = conn.execute('INSERT INTO Livros(nome,autor,descricao,temas,categoria,estoque,quantidade_disponivel,data_cadastro,localizacao) VALUES (?,?,?,?,?,4,4,?,?)', (title, author, description, themes, category, today.isoformat(), 'Estante ' + {'Ficção':'A','Não-ficção':'B','Poesia':'C','Quadrinhos':'D'}[category])).lastrowid
            existing[norm(title)] = bid
            added += 1
        reviews = [
            ('Dom Casmurro', 4, 'Gostei de como a narrativa faz a gente questionar o ponto de vista do narrador. O final rendeu uma boa discussão na turma.'),
            ('A Bolsa Amarela', 5, 'Uma leitura criativa e sensível sobre crescer e encontrar a própria voz. A bolsa e suas vontades deixam a história muito especial.'),
            ('Eu, Robô', 5, 'Os dilemas dos robôs foram a melhor parte. Cada história traz uma pergunta diferente sobre responsabilidade e tecnologia.'),
            ('O diário de Anne Frank', 5, 'Uma leitura marcante. O cotidiano e os sonhos da Anne tornam a história muito próxima e ajudam a refletir sobre respeito e memória.'),
            ('O Alienista', 4, 'O humor e a crítica social me surpreenderam. É curto, mas deixa bastante coisa para pensar sobre quem define o que é normal.'),
        ]
        for i, (title, stars, comment) in enumerate(reviews):
            bid = existing[norm(title)]
            start = today - timedelta(days=70-i*12)
            end = start + timedelta(days=6)
            conn.execute("INSERT INTO Emprestimo(usuarios_id,livros_id,data_emprestimo,data_vencimento,data_devolucao,status) VALUES (?,?,?,?,?,'Devolvido')", (uid,bid,start.isoformat(),(start+timedelta(days=7)).isoformat(),end.isoformat()))
            conn.execute('INSERT INTO LeiturasConcluidas(leitor_id,livro_id,concluida_em) VALUES (?,?,?)', (uid,bid,end.isoformat()))
            conn.execute("INSERT INTO Avaliacoes(leitor_id,livro_id,estrelas,comentario,estado,atualizada_em) VALUES (?,?,?,?,'publicado',?)", (uid,bid,stars,comment,now-(today-end).days*86400))
        active = existing[norm('A Hora da Estrela')]
        assert conn.execute('SELECT quantidade_disponivel FROM Livros WHERE id=?', (active,)).fetchone()[0] > 0
        loan = conn.execute("INSERT INTO Emprestimo(usuarios_id,livros_id,data_emprestimo,data_vencimento,status) VALUES (?,?,?,?,'Aprovado')", (uid,active,(today-timedelta(days=1)).isoformat(),(today+timedelta(days=6)).isoformat())).lastrowid
        conn.execute('UPDATE Livros SET quantidade_disponivel=quantidade_disponivel-1 WHERE id=?', (active,))
        for title in ['Vidas Secas','Capitães da Areia','Uma Breve História do Tempo','Laços','A Ilha do Tesouro','Quarto de Despejo']:
            conn.execute('INSERT OR IGNORE INTO QueroLer VALUES (?,?)', (uid,existing[norm(title)]))
        conn.execute('INSERT INTO Notificacoes(leitor_id,evento,mensagem) VALUES (?,?,?)', (uid,f'emprestimo-criado:{loan}','Você está com A Hora da Estrela. A devolução está prevista para 26/10/2026.'))
        staff = [('Ana Paula Ribeiro','Língua Portuguesa','Roda de leitura e debate literário','3º A'),('Marcos Oliveira','História','Pesquisa sobre memória e cidadania','2º B'),('Juliana Costa','Ciências','Pesquisa orientada sobre ciência e universo','1º A'),('Fernanda Almeida','Arte','Oficina de poesia e ilustração','2º A')]
        scheduled = 0
        for offset in range(-5, 15):
            day = today + timedelta(days=offset)
            if day.weekday() >= 5:
                continue
            for k, period in enumerate(['Manhã','Tarde']):
                teacher, subject, use, group = staff[(offset+k)%len(staff)]
                lesson = (offset+k)%6+1
                if conn.execute('SELECT 1 FROM Agendamento WHERE data=? AND periodo=? AND aula=?', (day.isoformat(),period,lesson)).fetchone():
                    continue
                conn.execute('INSERT INTO Agendamento(data,periodo,dia_semana,aula,professor,materia,uso,turma) VALUES (?,?,?,?,?,?,?,?)', (day.isoformat(),period,(day.weekday()+1)%7,lesson,teacher,subject,use,group))
                scheduled += 1
        conn.execute("INSERT INTO Auditoria(conta_id,acao,recurso,resultado,motivo) VALUES (?,'preenchimento_acervo',?,'ok','Cadastro de aluno, histórico de leitura, acervo e agenda')", (cid,str(uid)))
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()
        assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert check_password_hash(conn.execute('SELECT senha_hash FROM Contas WHERE id=?', (cid,)).fetchone()[0], password)
        assert not conn.execute('SELECT 1 FROM Livros WHERE quantidade_disponivel<0 OR quantidade_disponivel>estoque').fetchone()
        counts = {'livros_adicionados':added,'agendamentos_adicionados':scheduled,'leituras_concluidas':len(reviews),'avaliacoes':len(reviews),'quero_ler':6,'emprestimos_ativos':1}
    print(json.dumps({'backup':str(backup),'aluno_id':uid,'conta_id':cid,**counts,'integridade':'ok','senha_validada':True},ensure_ascii=False))
    conn.close()


if __name__ == '__main__':
    main()
