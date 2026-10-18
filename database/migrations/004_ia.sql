ALTER TABLE Livros ADD COLUMN autoria_genero TEXT CHECK(autoria_genero IN ('feminina','masculina','mista') OR autoria_genero IS NULL);
ALTER TABLE Livros ADD COLUMN autoria_pais TEXT;
ALTER TABLE Livros ADD COLUMN autoria_fonte TEXT;
CREATE TABLE IAUtilizacao (id INTEGER PRIMARY KEY, conta_id INTEGER REFERENCES Contas(id), instante INTEGER NOT NULL, operacao TEXT NOT NULL, provedor TEXT NOT NULL, modelo TEXT NOT NULL, tokens INTEGER, estado TEXT NOT NULL DEFAULT 'iniciada');
CREATE INDEX ia_uso_instante ON IAUtilizacao(instante);
