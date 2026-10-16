ALTER TABLE Contas ADD COLUMN onboarding_concluido_em TEXT;
UPDATE Contas SET onboarding_concluido_em=criada_em WHERE avatar IS NOT NULL AND avatar<>'';
CREATE TABLE AceitesTermos (
 id INTEGER PRIMARY KEY, conta_id INTEGER NOT NULL REFERENCES Contas(id),
 versao TEXT NOT NULL, aceito_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE Favoritos (
 conta_id INTEGER NOT NULL REFERENCES Contas(id), livro_id INTEGER NOT NULL REFERENCES Livros(id),
 ordem INTEGER NOT NULL CHECK(ordem BETWEEN 0 AND 3),
 PRIMARY KEY(conta_id,livro_id), UNIQUE(conta_id,ordem)
);
CREATE TABLE Preferencias (
 conta_id INTEGER PRIMARY KEY REFERENCES Contas(id), tema TEXT NOT NULL DEFAULT 'claro' CHECK(tema IN ('claro','escuro'))
);
INSERT OR IGNORE INTO Configuracoes(chave,valor) SELECT 'instalacao_criada_em',MIN(criada_em) FROM Contas HAVING COUNT(*)>0;
INSERT OR IGNORE INTO Configuracoes(chave,valor) SELECT 'instalacao_data_estimada','true' WHERE EXISTS(SELECT 1 FROM Contas);
INSERT OR IGNORE INTO Configuracoes VALUES ('recuperacao_modelo','desktop-dpapi-v1');
