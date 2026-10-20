"""Acrescenta leitores fictícios e atividade ao banco de apresentação, com backup."""
import json
import sqlite3
import time
from datetime import date, datetime, timedelta
from pathlib import Path


def main():
    path = Path.home() / 'AppData/Local/BIBI/Biblioteca.db'
    if not path.is_file():
        raise RuntimeError('Banco não encontrado.')
    conn = sqlite3.connect(path, timeout=30)
    conn.execute('PRAGMA foreign_keys=ON')
    backup = path.parent / 'backups' / f'Biblioteca-antes-comunidade-{datetime.now():%Y%m%d-%H%M%S}.db'
    with sqlite3.connect(backup) as target:
        conn.backup(target)
    today = date(2026, 10, 20)
    names = ['Mariana Oliveira','Lucas Ferreira','Beatriz Almeida','Pedro Henrique Costa','Camila Rodrigues','Gabriel Souza','Larissa Martins','Rafael Pereira','Isabela Rocha','Matheus Lima','Sofia Carvalho','André Mendes']
    comments = {
        'Ficção': ['Gostei de acompanhar as escolhas dos personagens. Algumas atitudes renderam uma boa conversa depois da leitura.', 'Demorei um pouco para entrar no ritmo, mas terminei querendo discutir a história com alguém.', 'Foi uma boa indicação da biblioteca. A escrita me chamou atenção e pretendo conhecer mais obras dessa autoria.', 'Li aos poucos durante a semana e gostei da experiência. É uma história que eu levaria para uma roda de leitura.', 'Gostei da leitura, embora algumas partes tenham exigido mais atenção. O que ficou foi a vontade de trocar impressões com a turma.'],
        'Não-ficção': ['Anotei várias ideias para pesquisar depois. Gostei de ter encontrado este livro no acervo da escola.', 'A leitura me ajudou a olhar o assunto por outro ângulo. Recomendo separar um tempo para refletir entre os capítulos.', 'Usei a leitura como ponto de partida para uma atividade e acabei me interessando mais pelo tema.', 'Algumas partes pedem uma leitura mais devagar, mas gostei das questões que o livro levanta.', 'Foi uma indicação que valeu a pena. Quero conversar sobre algumas passagens na próxima visita à biblioteca.'],
        'Poesia': ['Gostei de ler sem pressa e voltar aos trechos que mais me chamaram atenção. A experiência muda bastante na releitura.', 'Levei para casa e li um pouco a cada dia. Alguns versos ficaram comigo mesmo depois da devolução.', 'Nem todos os poemas me tocaram do mesmo jeito, mas encontrei passagens que gostaria de ler em voz alta.', 'Foi bom sair um pouco dos romances e experimentar poesia. Recomendo ler aos poucos.', 'A leitura rendeu boas interpretações na turma. Gostei de perceber como cada pessoa se aproxima dos poemas.'],
        'Quadrinhos': ['Gostei de prestar atenção na relação entre as imagens e os diálogos. Quero explorar mais essa parte do acervo.', 'Li no fim de semana e depois voltei a algumas páginas para observar melhor os desenhos.', 'Uma boa escolha para variar as leituras. Gostaria de conversar sobre a narrativa no clube do livro.', 'Gostei do ritmo e da forma de contar a história. Já coloquei outros quadrinhos na minha lista.', 'Os detalhes visuais fizeram diferença para mim. Vale olhar as páginas com calma além de acompanhar o texto.'],
    }
    endings = [' Peguei por indicação de um colega.', ' Escolhi depois de olhar a prateleira.', ' Foi minha leitura do mês.', ' Quero recomendar para uma amiga.', ' Vou levar essa impressão para o clube de leitura.', ' Pretendo reler mais adiante.', ' A conversa em sala ajudou na leitura.', ' Foi bom descobrir algo fora das minhas escolhas habituais.']
    now = int(time.time())
    inserted = returned = active = wishes = 0
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        readers = []
        for i, name in enumerate(names):
            email = f'leitor{i+1}@example.test'
            row = conn.execute('SELECT id FROM Usuarios WHERE email=?', (email,)).fetchone()
            readers.append(row[0] if row else conn.execute("INSERT INTO Usuarios(nome,tipo,email,sala,periodo) VALUES (?,'estudante',?,?,?)", (name,email,f'{i%3+1}º {chr(65+i%3)}','Manhã' if i%2==0 else 'Tarde')).lastrowid)
        books = conn.execute('SELECT id,nome,categoria FROM Livros WHERE arquivado=0 ORDER BY id').fetchall()
        for index, (bid, title, category) in enumerate(books):
            pool = comments.get(category, comments['Ficção'])
            for j in range(3 + index%2):
                uid = readers[(index*5+j*3)%len(readers)]
                if conn.execute('SELECT 1 FROM Avaliacoes WHERE leitor_id=? AND livro_id=?', (uid,bid)).fetchone():
                    continue
                end = today-timedelta(days=3+(index*7+j*11)%80)
                start = end-timedelta(days=3+(index+j)%5)
                comment = f'“{title.strip()}” — ' + pool[(index+j)%len(pool)] + endings[(index*3+j)%len(endings)]
                stars = [4,5,4,3,5,4,5][(index+j*2)%7]
                conn.execute("INSERT INTO Avaliacoes(leitor_id,livro_id,estrelas,comentario,estado,atualizada_em) VALUES (?,?,?,?,'publicado',?)", (uid,bid,stars,comment,now-(today-end).days*86400))
                conn.execute('INSERT OR IGNORE INTO LeiturasConcluidas(leitor_id,livro_id,concluida_em) VALUES (?,?,?)', (uid,bid,end.isoformat()))
                conn.execute("INSERT INTO Emprestimo(usuarios_id,livros_id,data_emprestimo,data_vencimento,data_devolucao,status) VALUES (?,?,?,?,?,'Devolvido')", (uid,bid,start.isoformat(),(start+timedelta(days=7)).isoformat(),end.isoformat()))
                inserted += 1
                returned += 1
        for i, uid in enumerate(readers):
            if not conn.execute("SELECT 1 FROM Emprestimo WHERE usuarios_id=? AND status IN ('Aprovado','Atrasado')", (uid,)).fetchone():
                bid = books[(i*7+2)%len(books)][0]
                if conn.execute('SELECT quantidade_disponivel FROM Livros WHERE id=?', (bid,)).fetchone()[0] > 0:
                    days = 10 if i in (3,8) else 1+i%5
                    start = today-timedelta(days=days)
                    due = start+timedelta(days=7)
                    status = 'Atrasado' if due<today else 'Aprovado'
                    conn.execute('INSERT INTO Emprestimo(usuarios_id,livros_id,data_emprestimo,data_vencimento,status) VALUES (?,?,?,?,?)', (uid,bid,start.isoformat(),due.isoformat(),status))
                    conn.execute('UPDATE Livros SET quantidade_disponivel=quantidade_disponivel-1 WHERE id=?', (bid,))
                    active += 1
            for j in range(3):
                bid = books[(i*5+j*11)%len(books)][0]
                wishes += conn.execute('INSERT OR IGNORE INTO QueroLer VALUES (?,?)', (uid,bid)).rowcount
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()
        assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not conn.execute('SELECT 1 FROM Livros WHERE quantidade_disponivel<0 OR quantidade_disponivel>estoque').fetchone()
        missing = conn.execute("SELECT COUNT(*) FROM Livros l WHERE arquivado=0 AND NOT EXISTS(SELECT 1 FROM Avaliacoes a WHERE a.livro_id=l.id AND a.estado='publicado')").fetchone()[0]
        assert missing == 0
        conn.execute("INSERT INTO Auditoria(acao,recurso,resultado,motivo) VALUES ('preenchimento_comunidade','acervo','ok','Leitores fictícios e movimentações para apresentação local')")
    print(json.dumps(dict(backup=str(backup),livros_com_opinioes=len(books),comentarios_adicionados=inserted,emprestimos_devolvidos=returned,emprestimos_ativos_adicionados=active,interesses_adicionados=wishes,integridade='ok'), ensure_ascii=False))
    conn.close()


if __name__ == '__main__':
    main()
