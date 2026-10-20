CREATE TABLE LeiturasConcluidas (leitor_id INTEGER NOT NULL REFERENCES Usuarios(id), livro_id INTEGER NOT NULL REFERENCES Livros(id), concluida_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(leitor_id,livro_id));
CREATE TABLE ImportacoesAcervo (origem TEXT NOT NULL, origem_id INTEGER NOT NULL, livro_id INTEGER NOT NULL REFERENCES Livros(id), PRIMARY KEY(origem,origem_id));
