ALTER TABLE Livros ADD COLUMN arquivado INTEGER NOT NULL DEFAULT 0;
ALTER TABLE Usuarios ADD COLUMN arquivado INTEGER NOT NULL DEFAULT 0;
ALTER TABLE Emprestimo ADD COLUMN renovacoes INTEGER NOT NULL DEFAULT 0;
ALTER TABLE Emprestimo ADD COLUMN encerramento TEXT;
CREATE TABLE IF NOT EXISTS Reservas (
 id INTEGER PRIMARY KEY, leitor_id INTEGER NOT NULL REFERENCES Usuarios(id), livro_id INTEGER NOT NULL REFERENCES Livros(id),
 estado TEXT NOT NULL CHECK(estado IN ('fila','retirada','concluida','cancelada','expirada')),
 criada_em INTEGER NOT NULL, expira INTEGER, emprestimo_id INTEGER REFERENCES Emprestimo(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS reserva_unica ON Reservas(leitor_id,livro_id) WHERE estado IN ('fila','retirada');
CREATE INDEX IF NOT EXISTS reserva_fila ON Reservas(livro_id,estado,criada_em,id);
CREATE TABLE IF NOT EXISTS QueroLer (
 leitor_id INTEGER NOT NULL REFERENCES Usuarios(id),livro_id INTEGER NOT NULL REFERENCES Livros(id),
 PRIMARY KEY(leitor_id,livro_id)
);
CREATE TABLE IF NOT EXISTS PedidosRenovacao (
 id INTEGER PRIMARY KEY, emprestimo_id INTEGER NOT NULL REFERENCES Emprestimo(id),
 estado TEXT NOT NULL DEFAULT 'pendente', criada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, motivo TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS pedido_unico ON PedidosRenovacao(emprestimo_id) WHERE estado='pendente';
CREATE TABLE IF NOT EXISTS Ocorrencias (
 id INTEGER PRIMARY KEY, livro_id INTEGER NOT NULL REFERENCES Livros(id), emprestimo_id INTEGER REFERENCES Emprestimo(id),
 tipo TEXT NOT NULL CHECK(tipo IN ('observacao','reparo','baixa','perda','retorno_reparo')),
 quantidade INTEGER NOT NULL CHECK(quantidade>0), observacao TEXT NOT NULL, conta_id INTEGER REFERENCES Contas(id),
 criada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS Notificacoes (
 id INTEGER PRIMARY KEY, leitor_id INTEGER NOT NULL REFERENCES Usuarios(id), evento TEXT NOT NULL UNIQUE,
 mensagem TEXT NOT NULL, lida INTEGER NOT NULL DEFAULT 0, criada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS Avaliacoes (
 id INTEGER PRIMARY KEY, leitor_id INTEGER NOT NULL REFERENCES Usuarios(id), livro_id INTEGER NOT NULL REFERENCES Livros(id),
 estrelas INTEGER NOT NULL CHECK(estrelas BETWEEN 1 AND 5), comentario TEXT NOT NULL,
 estado TEXT NOT NULL CHECK(estado IN ('publicado','revisao','oculto')), motivo TEXT,
 atualizada_em INTEGER NOT NULL, UNIQUE(leitor_id,livro_id)
);
CREATE TABLE IF NOT EXISTS FilaEmail (
 id INTEGER PRIMARY KEY, evento TEXT NOT NULL UNIQUE, destinatario TEXT NOT NULL,
 assunto TEXT NOT NULL, corpo TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'pendente', tentativas INTEGER NOT NULL DEFAULT 0,
 proxima INTEGER NOT NULL DEFAULT 0, atualizada_em INTEGER NOT NULL DEFAULT 0
);
