# BIBI — Biblioteca Inteligente

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT) [![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org) [![HTML5](https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/HTML) [![CSS3](https://img.shields.io/badge/CSS3-1572B6?logo=css3&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/CSS) [![Flask](https://img.shields.io/badge/Flask-2.x-black?logo=flask)](https://flask.palletsprojects.com/) [![Releases](https://img.shields.io/badge/Releases-Download-blue?logo=github)](https://github.com/CaesarKairos/BIBI-Biblioteca-Inteligente/releases)

BIBI é um sistema de gerenciamento de biblioteca desktop, projetado para escolas. Ele roda localmente pelo navegador e oferece controle inteligente de empréstimos, cadastro de leitores, notificações por e-mail e agendamento de salas de aula.

---

## Sumário

- [Funcionalidades](#funcionalidades)
- [Tecnologias](#tecnologias)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Instalação](#instalação)
  - [Para Usuários Finais](#para-usuários-finais)
  - [Para Desenvolvedores](#para-desenvolvedores)
- [Build](#build)
- [Guia de Configuração (Escolas)](#guia-de-configuração-escolas)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Notas de Desenvolvimento](#notas-de-desenvolvimento)
- [Licença](#licença)

---

## Funcionalidades

### Gerenciamento de Acervo
- **Catálogo de livros**: Cadastro manual ou por ISBN com upload de capa, categorias, localização/prateleira e controle de estoque
- **Leitores**: Cadastro de estudantes e professores com sala, período, matéria e telefone
- **Empréstimos**: Assistente rápido, visões de ativos/histórico/devoluções, status (Aprovado, Devolvido, Atrasado, Pendente)
- **Renovação e Devolução**: Renovação e devolução em um clique com atualização automática do estoque
- **Notificações por e-mail**: Confirmações HTML em HTML no empréstimo, renovação e devolução; lembrete automático 3 dias antes e na data de vencimento
- **Dashboard**: Estatísticas, gráficos de gêneros, livros mais emprestados, ranking de leitores (trimestral) e livros adormecidos (sem empréstimos há 6 meses)

### Agendamento de Salas
- **Agenda Semanal**: Grade por período e número de aula/sala
- **Barra Lateral**: Próximas 5 datas agendadas com navegação rápida
- **Sem Conflitos**: Criação e exclusão simples de agendamentos

### Administração e Segurança
- **Rotas Administrativas**: Todas as operações de escrita restritas ao localhost por padrão
- **Proteção por Senha**: PIN de 4 dígitos opcional para empréstimos e agendamentos
- **Configurações do Sistema**: Alternar e-mails, obrigar localização do livro, bloquear exclusão de agendamentos, configurar SMTP, definir quantidade de aulas por dia (1–20)
- **Tema Escuro**: Alternância global de tema, persistida no armazenamento do navegador

### Experiência do Usuário
- **Imagens de Destaque**: Banner aleatório a partir de `static/images/hero/`
- **Capas de Livros**: Upload via arrastar/colar, importação por URL externa ou placeholder
- **Biblioteca de Capas**: Pastas separadas para capas enviadas e externas em `%LOCALAPPDATA%\BIBI\`
- **Atalhos de Teclado**: Ctrl+1 Dashboard, Ctrl+2 Acervo, Ctrl+3 Empréstimos, Ctrl+5 Leitores

---

## Tecnologias

| Categoria | Tecnologia |
|---|---|
| Linguagem | Python 3.8+ |
| Framework Web | Flask |
| Banco de Dados | SQLite |
| Runtime Desktop | pywebview |
| E-mail | smtplib + MIME ( HTML com imagens embutidas) |
| Frontend | HTML5, CSS3, JavaScript (Vanilla) |
| Estilização | CSS Grid, Layout Responsivo, Tema Escuro |
| Gráficos | Chart.js |
| Seletor de Data | Flatpickr |
| Empacotamento | PyInstaller |

---

## Estrutura do Projeto

```
BIBI-Biblioteca-Inteligente/
│
├── app.py                 # Aplicação Flask principal (backend + HTML/CSS/JS embutidos)
├── env.example            # Template de variáveis de ambiente Flask
├── .env                   # Segredos de execução (não versionado)
├── requirements.txt       # Dependências Python
├── setup.iss.example      # Modelo de instalador para Inno Setup
├── .gitignore
│
├── static/
│   └── images/
│       ├── icon.png       # Ícone do aplicativo
│       ├── icon.ico       # Ícone Windows
│       ├── iconphilocode.png
│       ├── philocode.png
│       ├── placeholder.png
│       ├── catwaving.webm # Animação da barra lateral
│       ├── hero/          # Banners de destaque (seleção aleatória)
│       ├── uploadedcovers/ # Capas enviadas pelo usuário (runtime)
│       └── externalcovers/ # Capas importadas por URL (runtime)
│
└── (saída do build na release)
```

Observações:
- Dados de execução são armazenados em `%LOCALAPPDATA%\BIBI\` (ex: `C:\Users\<usuario>\AppData\Local\BIBI\`).
- O banco de dados SQLite (`Biblioteca.db`) fica dentro do diretório de dados.
- Não há pasta `templates/` separada; a interface é renderizada via `render_template_string` dentro de `app.py`.

---

## Instalação

### Para Usuários Finais

Usuários finais não precisam instalar Python nem executar scripts.

1. Acesse a página de [Releases](https://github.com/CaesarKairos/BIBI-Biblioteca-Inteligente/releases)
2. Baixe o instalador (`.exe`) para Windows
3. Execute o instalador e siga as instruções
4. Inicie o BIBI pelo Menu Iniciar / Atalho na área de trabalho

O aplicativo abre em uma janela nativa leve de navegador.

### Para Desenvolvedores

Pré-requisitos:
- Python 3.8+
- Git
- pip

```bash
# 1. Clone o repositório
git clone https://github.com/CaesarKairos/BIBI-Biblioteca-Inteligente.git
cd BIBI-Biblioteca-Inteligente

# 2. Crie e ative um ambiente virtual
python -m venv .venv
.venv\Scripts\Activate.ps1   # PowerShell
# ou
.venv\Scripts\activate.bat   # CMD

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
copy env.example .env
# Edite .env e defina SECRET_KEY, EMAIL_USER/EMAIL_PASSWORD se necessário

# 5. Execute a aplicação
python app.py
```

Abra o navegador em `http://127.0.0.1:5000/app`.

**Importante:** Os recursos administrativos estão disponíveis apenas ao acessar de `localhost` ou `127.0.0.1`.

---

## Build

### PyInstaller

A partir da raiz do projeto:

```bash
pyinstaller --onefile --windowed app.py
```

`--onefile`: gera um único `.exe`.
`--windowed`: suprime a janela do console.

A saída fica em `dist/`.

> **Nota:** Não há `app.spec` versionado no repositório. Use o comando acima diretamente.

### Inno Setup (Instalador Windows)

Este repositório inclui `setup.iss.example` como modelo. Para gerar o instalador:

1. Copie `setup.iss.example` para `setup.iss`
2. Ajuste `AppVersion`, caminhos e configurações conforme necessário
3. Compile com:

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss
```

Isso produz um instalador Windows que registra o app, cria atalhos e coloca o executável em `Arquivos de Programas`.

**Nota:** Revise o arquivo `setup.iss` para configurações específicas do instalador (nome do app, versão, nome do arquivo de saída, ícone e diretório de instalação padrão).

---

## Guia de Configuração (Escolas)

O BIBI foi criado para escolas de ensino básico brasileiras (conforme indicado pelos tipos estudante/professor, matérias, salas/períodos). Esta seção orienta o primeiro acesso para um administrador escolar sem conhecimento técnico.

### 1. Primeira Execução
- Inicie o aplicativo após a instalação.
- O banco de dados e os diretórios de usuário são criados automaticamente em `%LOCALAPPDATA%\BIBI\`.

### 2. Acesso Administrativo
- Abra o app na mesma máquina onde ele foi instalado.
- Recursos administrativos (adicionar/editar/excluir livros, leitores, empréstimos, agendamentos e configurações) estão disponíveis apenas no localhost.
- Na primeira ação administrativa, o sistema pode solicitar a definição de um PIN de 4 dígitos para operações protegidas.

### 3. Configurações do Sistema (Ícone de Engrenagem)
Acesse as configurações pela barra lateral (apenas admin):

- **Bloquear e-mails**: Desabilita/habilita todas as notificações de saída (útil durante testes).
- **Exigir senha para empréstimos**: Solicita o PIN de admin para realizar empréstimos.
- **Obrigar localização do livro**: Torna o campo "Localização (Prateleira)" obrigatório ao adicionar ou editar livros.
- **Exigir senha para agendamentos**: Solicita o PIN de admin para criar ou excluir agendamentos.
- **Bloquear exclusão de agendamentos**: Impede completamente a exclusão de agendamentos.
- **Quantidade de aulas por dia**: Defina de 1 a 20 para corresponder à carga diária da escola.
- **E-mail da organização**: Configure uma conta Gmail e App Password para notificações.

### 4. Notificações por E-mail
Opcional, mas recomendado:
- Use uma conta Gmail com [App Password](https://support.google.com/accounts/answer/185833).
- Configure no painel de configurações. E-mails são enviados para:
  - Confirmação de empréstimo
  - Confirmação de renovação
  - Confirmação de devolução
  - Lembretes de vencimento (3 dias antes e na data de vencimento)

Se os e-mails não estiverem configurados, o sistema registra logs no console.

### 5. Catálogo de Livros
- Acesse **Acervo**.
- **Adicione livros** por ISBN (consulta um serviço de catálogo externo) ou **manualmente** (para obras raras ou locais).
- Campos opcionais: descrição, temas, categoria, localização (prateleira) e capa.
- O estoque é gerenciado por meio dos contadores Total e Disponível.

### 6. Leitores
- Acesse **Leitores**.
- Tipos: **estudante** ou **professor**.
- Estudantes exigem e-mail, sala, período e telefone opcional.
- Professores exigem e-mail opcional e matéria.

### 7. Empréstimos
- **Empréstimo Rápido**: Selecione um livro, abra o **Empréstimo Rápido**, busque ou crie um leitor e confirme.
- Limites: Estudantes podem pegar 1 livro por vez. Professores não têm limite de empréstimos ativos na lógica atual.
- Prazos: Estudantes recebem um prazo configurável (padrão 7 dias); professores devem devolver no mesmo dia (0 dias).
- Atraso automático: Empréstimos pendentes com data vencida são marcados como **Atrasado**.

### 8. Agendamento de Salas
- Acesse **Agenda**.
- Escolha uma data e um período (Manhã / Tarde / Noite).
- Preencha professor, matéria e uso da sala.
- A tabela exibe aulas agendadas por dia e número de sala.

### 9. Dashboard
- Visualize o total de títulos, exemplares, empréstimos ativos, itens atrasados, devoluções do dia, itens na agenda e quantidade de leitores.
- Revise gráficos de gêneros, preferência histórica, principais leitores do trimestre, livros mais emprestados e livros adormecidos.

---

## Variáveis de Ambiente

Definidas em `env.example` e lidas por `app.py` via `python-dotenv`:

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `SECRET_KEY` | Recomendada | `sua-chave-secreta-padrao` | Chave de assinatura de sessão Flask. Deve ser uma string longa e aleatória em produção. |
| `PORT` | Não | `5000` | Porta HTTP para o servidor de desenvolvimento Flask. |
| `FLASK_DEBUG` | Não | `False` | Habilita modo de depuração (`True`) apenas para desenvolvimento. |

Credenciais adicionais são armazenadas diretamente na tabela `Configuracoes` do banco de dados, em vez de `.env`:
- `email_organizacao` (conta SMTP)
- `email_app_password` (senha SMTP)
- `bloquear_email`
- `exigir_senha_emprestimo`
- `exigir_senha_agendamento`
- `obrigar_localizacao_livro`
- `bloquear_excluir_agendamento`
- `quantidade_aulas`
- `senha_hash`

---

## Notas de Desenvolvimento

### Arquitetura
- Aplicação Flask de arquivo único (`app.py`) com templates, estilos e scripts embutidos.
- SQLite por meio de uma classe `DatabaseManager` personalizada com modo WAL ativado.
- Tarefas em segundo plano usando `threading` Python (verificação de notificações a cada 30 minutos).
- Templates HTML de e-mail construídos inline em Python com logo e capa de livro embutidos.
- Frontend responsivo desktop-first com layout de 3 colunas (`260px / 1fr / 320px`).

### Observações de Comportamento
- A verificação de admin depende apenas de endereços loopback IPv4/IPv6: `127.0.0.1`, `::1`, `localhost`. Se o app for implantado em rede, os endpoints administrativos serão negados. Para implantação em intranet, verificações de IP adicionais ou autenticação são necessárias.
- O serviço de e-mail atualmente usa Gmail SMTP fixo (`smtp.gmail.com:587` com STARTTLS). Outros provedores não são suportados sem alterações no código.
- A busca por ISBN depende de uma função externa (`buscar_livro_cascata`). Se esse serviço falhar, o cadastro por ISBN retorna 404; o cadastro manual é a alternativa.
- O fuso horário usa o fixo `-03:00` (Brasília). Regras de DST são ignoradas.

### Performance e Escalabilidade
- SQLite é adequado para uso escolar em máquina única.
- Capas de livros são servidas diretamente do disco.
- Não há autenticação de usuário além das verificações de host administrativo e um PIN opcional.

### Roteiro e Ressalvas
- Frontend e backend são fortemente acoplados; refatoração futura em módulos e pastas separadas é recomendada para manutenibilidade.
- Não há funcionalidade de backup/exportação; o arquivo SQLite pode ser copiado manualmente com o app fechado.
- O app usa `webview` para a experiência desktop, mas o esquema de URL é `http://127.0.0.1:5000/app`, que executa o servidor Flask e abre uma janela nativa.

---

## Licença

Este projeto está licenciado sob a licença MIT. Consulte o arquivo [LICENSE](LICENSE) para obter detalhes.
