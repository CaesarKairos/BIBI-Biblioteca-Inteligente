
            CREATE TABLE IF NOT EXISTS Livros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                isbn TEXT UNIQUE,
                nome TEXT NOT NULL,
                autor TEXT NOT NULL,
                ano_publicacao INTEGER,
                numero_paginas INTEGER CHECK (numero_paginas IS NULL OR (typeof(numero_paginas) = 'integer' AND numero_paginas > 0)),
                capa_url TEXT,
                descricao TEXT,
                temas TEXT,
                categoria TEXT DEFAULT 'Ficção',
                estoque INTEGER NOT NULL,
                quantidade_disponivel INTEGER NOT NULL,
                data_cadastro TEXT NOT NULL DEFAULT (date('now')),
                localizacao TEXT
            );

            CREATE TABLE IF NOT EXISTS Usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                tipo TEXT CHECK(tipo IN ('estudante', 'professor', 'bibliotecario')) NOT NULL,
                email TEXT UNIQUE,
                sala TEXT,
                periodo TEXT,
                materia TEXT,
                telefone TEXT
            );

            CREATE TABLE IF NOT EXISTS Emprestimo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuarios_id INTEGER NOT NULL,
                livros_id INTEGER NOT NULL,
                data_emprestimo TEXT NOT NULL,
                data_vencimento TEXT NOT NULL,
                data_devolucao TEXT,
                quantidade INTEGER NOT NULL DEFAULT 1,
                status TEXT CHECK(status IN ('Pendente', 'Aprovado', 'Devolvido', 'Atrasado')) DEFAULT 'Aprovado',
                notificacao_3dias INTEGER DEFAULT 0,
                notificacao_hoje INTEGER DEFAULT 0,
                FOREIGN KEY (usuarios_id) REFERENCES Usuarios(id),
                FOREIGN KEY (livros_id) REFERENCES Livros(id)
            );

            CREATE TABLE IF NOT EXISTS Agendamento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                periodo TEXT CHECK(periodo IN('Manhã', 'Tarde', 'Noite')) NOT NULL,
                dia_semana INTEGER NOT NULL,
                aula INTEGER NOT NULL,
                professor TEXT NOT NULL,
                materia TEXT NOT NULL,
                uso TEXT NOT NULL,
                turma TEXT
            );

            CREATE TABLE IF NOT EXISTS Configuracoes (
                chave TEXT PRIMARY KEY,
                valor TEXT
            );
