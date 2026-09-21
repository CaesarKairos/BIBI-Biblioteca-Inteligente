CREATE TABLE IF NOT EXISTS Contas (
 id INTEGER PRIMARY KEY, leitor_id INTEGER UNIQUE REFERENCES Usuarios(id),
 nome TEXT NOT NULL, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
 senha_hash TEXT NOT NULL, papel TEXT NOT NULL CHECK(papel IN ('bibliotecario','leitor')),
 ativa INTEGER NOT NULL DEFAULT 1, email_verificado INTEGER NOT NULL DEFAULT 0,
 ativacao TEXT NOT NULL, versao_sessao INTEGER NOT NULL DEFAULT 1,
 recuperacao_hash TEXT, avatar TEXT, criada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS Sessoes (
 hash TEXT PRIMARY KEY, conta_id INTEGER NOT NULL REFERENCES Contas(id),
 versao INTEGER NOT NULL, expira INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS Codigos (
 id INTEGER PRIMARY KEY, leitor_id INTEGER REFERENCES Usuarios(id), conta_id INTEGER REFERENCES Contas(id),
 email TEXT NOT NULL COLLATE NOCASE, finalidade TEXT NOT NULL,
 entrega TEXT NOT NULL CHECK(entrega IN ('presencial','email')), hash TEXT NOT NULL UNIQUE,
 expira INTEGER NOT NULL, consumido INTEGER NOT NULL DEFAULT 0,
 criado_por INTEGER REFERENCES Contas(id), criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS Tentativas (
 chave TEXT PRIMARY KEY, quantidade INTEGER NOT NULL, inicio INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS Auditoria (
 id INTEGER PRIMARY KEY, conta_id INTEGER, quando TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 acao TEXT NOT NULL, recurso TEXT NOT NULL, resultado TEXT NOT NULL, motivo TEXT
);
CREATE INDEX IF NOT EXISTS idx_codigos_destino ON Codigos(email,finalidade,consumido);
CREATE INDEX IF NOT EXISTS idx_emprestimo_leitor ON Emprestimo(usuarios_id,status);
CREATE INDEX IF NOT EXISTS idx_emprestimo_livro ON Emprestimo(livros_id,status);
CREATE INDEX IF NOT EXISTS idx_livros_nome ON Livros(nome,id);
