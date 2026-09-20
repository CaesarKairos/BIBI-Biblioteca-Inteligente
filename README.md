# BIBI — Biblioteca Inteligente

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org) [![Flask](https://img.shields.io/badge/Flask-2.3.3-black?logo=flask)](https://flask.palletsprojects.com/) [![Releases](https://img.shields.io/badge/Releases-Download-blue?logo=github)](https://github.com/CaesarKairos/BIBI-Biblioteca-Inteligente/releases)

BIBI é um sistema de gerenciamento de biblioteca escolar, com execução desktop no Windows. O Flask fornece as páginas e a API HTTP, o SQLite armazena os dados localmente e o pywebview apresenta a interface em uma janela nativa. A interface também pode ser acessada pelo navegador enquanto o aplicativo estiver em execução.

O sistema tem **arquitetura modular em camadas**, com rotas HTTP, serviços, persistência e interface organizados separadamente. O backend e a interface são distribuídos na mesma aplicação; a implementação monolítica anterior está preservada apenas como referência em `legacy/`.

## Sumário

- [Funcionalidades](#funcionalidades)
- [Arquitetura e estrutura](#arquitetura-e-estrutura)
- [Tecnologias](#tecnologias)
- [Instalação e execução](#instalação-e-execução)
- [Configuração e regras de uso](#configuração-e-regras-de-uso)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Dados e backup](#dados-e-backup)
- [Build e instalador](#build-e-instalador)
- [Verificação](#verificação)
- [Limitações atuais](#limitações-atuais)
- [Licença](#licença)

## Funcionalidades

- **Acervo:** cadastro manual ou por ISBN, edição, categorias, descrição, localização/prateleira e controle de exemplares disponíveis.
- **Interface:** ocupa toda a janela, com prateleiras, painel de detalhes fechável, temas claro/escuro e navegação por teclado. Capas nas prateleiras têm tamanho uniforme. Número de páginas opcional, preenchido manualmente ou pelas fontes de ISBN.
- **Capas:** upload, arrastar/colar imagens, obtenção por URL e imagem substituta quando não há capa.
- **Leitores:** cadastro de estudantes e professores, com campos de sala, período, matéria, e-mail e telefone conforme o tipo.
- **Empréstimos:** fluxo rápido, consulta de ativos e histórico, devolução, renovação e atualização de estoque.
- **E-mails:** confirmações de empréstimo, renovação e devolução; lembretes três dias antes e no dia do vencimento.
- **Dashboard:** indicadores do acervo e dos empréstimos, gráficos por gênero, livros mais emprestados, ranking de leitores dos últimos 90 dias e livros adormecidos.
- **Agenda:** consulta por data, período e número da aula, cadastro de professor, matéria, uso e turma, próximas cinco datas agendadas e últimos cinco agendamentos passados.
- **Preferências:** tema escuro, configurações da agenda, exigência de senha em operações específicas e controle do envio de e-mails.

Atalhos administrativos: `Ctrl+1` Dashboard, `Ctrl+2` Acervo, `Ctrl+3` Empréstimos, `Ctrl+4` Agenda e `Ctrl+5` Leitores. No acesso não administrativo, `Ctrl+1` abre o Acervo e `Ctrl+2` abre a Agenda.

## Arquitetura e estrutura

| Componente | Responsabilidade |
|---|---|
| `app.py` | Inicializa diretórios, banco e Flask, registra Blueprints e tratamento de erros; na execução direta, inicia notificações, servidor e janela desktop. |
| `config.py` | Carrega o ambiente e define caminhos para código-fonte, distribuição empacotada e dados do usuário. |
| `routes/` | Adapta requisições HTTP para chamadas aos serviços, aplica restrições administrativas e produz respostas JSON ou HTML. |
| `services/` | Implementa regras de livros, leitores, empréstimos, agendamentos e configurações, além das integrações de imagens e e-mail. |
| `database/` | Mantém o schema SQL, a inicialização, as migrações de compatibilidade e o gerenciamento de conexões SQLite. |
| `utils/` | Compartilha verificações de acesso e funções de data/hora. |
| `templates/` | Contém as páginas Jinja e os quatro templates de e-mail. |
| `static/css/` e `static/js/` | Contêm estilos e scripts separados por responsabilidade: interface, acervo, leitores, empréstimos, dashboard, agenda e configurações. |
| `tests/` | Reúne testes de regressão, correções e comparação no navegador. |
| `docs/` | Preserva inventários e o relatório histórico da refatoração. |
| `legacy/` | Preserva o monólito usado como referência pelos testes; não é o ponto de entrada atual. |

As páginas `/` e `/app` são renderizadas pelo Flask. O JavaScript consome endpoints `/api/...` e recebe dados iniciais do template, como o perfil administrativo e a quantidade de aulas. Os scripts são separados em arquivos por funcionalidade e compartilham funções e estado no navegador.

Os serviços recebem dados das rotas e executam as regras e consultas SQL por meio do `DatabaseManager`. A persistência usa SQLite em modo WAL. Essa organização permite manter cada responsabilidade em seu módulo, embora frontend e backend continuem compartilhando os contratos da API e o mesmo processo de distribuição.

O [relatório da modernização visual](docs/MODERNIZACAO_UI.md) descreve a interface, a migração idempotente de `numero_paginas` e os testes. As áreas **✦ BIBI** são preparação visual: a quinta prateleira mostra uma amostra identificada do acervo e o Dashboard usa um resumo local, sem integração de IA.

O [relatório da refatoração](docs/REFATORACAO.md) e o [inventário original](docs/inventario_original.json) documentam a migração inicial. São registros históricos: informações sobre o estado do workspace e resultados daquela etapa não substituem a implementação atual.

## Tecnologias

As versões fixadas estão em [requirements.txt](requirements.txt).

| Categoria | Tecnologia |
|---|---|
| Linguagem e plataforma | Python 3.8+; caminhos de dados voltados ao Windows |
| Servidor web | Flask 2.3.3 e Werkzeug 2.3.7 |
| Persistência | SQLite, pela biblioteca padrão do Python |
| Janela desktop | pywebview 4.4.1 |
| Integrações HTTP | requests 2.31.0 |
| Ambiente | python-dotenv 1.0.0 |
| Imagens | Pillow 10.1.0 |
| E-mail | smtplib, MIME e templates Jinja |
| Interface | HTML, CSS e JavaScript sem framework de frontend |
| Gráficos e calendário | Chart.js e Flatpickr, carregados por CDN |
| Empacotamento | PyInstaller 6.3.0; modelo de instalador Inno Setup |

## Instalação e execução

### Usuários finais

Consulte os arquivos publicados na página de [Releases](https://github.com/CaesarKairos/BIBI-Biblioteca-Inteligente/releases). Para uma distribuição com instalador Windows, execute o instalador e abra o BIBI pelo atalho criado. O pacote executável dispensa a instalação separada do Python.

### Desenvolvimento no Windows

Com Python, pip e Git instalados, execute no PowerShell:

```powershell
git clone https://github.com/CaesarKairos/BIBI-Biblioteca-Inteligente.git
cd BIBI-Biblioteca-Inteligente
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item env.example .env
# Edite .env e defina uma SECRET_KEY própria.
python app.py
```

No CMD, a ativação do ambiente é `.venv\Scripts\activate.bat`.

O comando `python app.py` inicializa o banco, inicia o servidor e a verificação periódica de notificações e abre a janela em `http://127.0.0.1:5000/`. A página principal do sistema está em `http://127.0.0.1:5000/app`. Se `PORT` for alterada, use a porta configurada nessas URLs.

O servidor escuta em `0.0.0.0`, permitindo acesso pela rede quando a configuração de rede e o firewall permitirem. O perfil administrativo depende do endereço de origem da conexão: `127.0.0.1`, `::1` ou `localhost`. Conexões por outros endereços têm acesso à interface de consulta de acervo e agenda; as rotas de leitores e de gerenciamento de empréstimos são restritas ao administrador.

Importar `app` também inicializa os diretórios e o banco, mas não inicia a janela nem a rotina de notificações. Por isso, executar somente o Flask por outro mecanismo não reproduz todo o comportamento de `python app.py`.

## Configuração e regras de uso

### Primeiro acesso e preferências

Na primeira execução, o banco e os diretórios de dados são criados automaticamente. Acesse o aplicativo localmente e abra as configurações pela engrenagem. A interface permite definir uma senha de **quatro caracteres**, que não precisa ser exclusivamente numérica.

| Configuração | Padrão em um banco novo | Efeito |
|---|---|---|
| Bloquear e-mails | Desativado | Suspende o envio de notificações quando ativado. |
| Exigir senha para empréstimos | Desativado | Exige a senha na criação de empréstimos. |
| Obrigar localização do livro | Desativado | Exige localização ao cadastrar ou editar livros. |
| Exigir senha para agendamentos | Desativado | Exige a senha na criação de agendamentos. |
| Bloquear exclusão de agendamentos | Ativado | Impede a exclusão enquanto estiver ativo. |
| Quantidade de aulas | 6 | Aceita de 1 a 20 aulas por dia. |
| E-mail da organização e senha de aplicativo | Vazios | Configuram as credenciais de envio. |

A senha solicitada pela interface não constitui um sistema de contas e sessões de usuário. A restrição administrativa das rotas usa o endereço de origem; as opções de senha de empréstimo e agendamento são verificadas também pelos respectivos serviços de criação. A exclusão de agendamentos depende do acesso administrativo e da opção de bloqueio, sem uma verificação adicional dessa senha no endpoint.

### Acervo e leitores

O cadastro por ISBN consulta, em sequência, Open Library, BrasilAPI e Google Books, complementando os campos ausentes. Há uma tentativa adicional por título no Google Books quando um título foi encontrado. A busca é considerada bem-sucedida quando há título e autor; se isso não ocorrer, o cadastro por ISBN retorna erro e o cadastro manual continua disponível.

O formulário de leitores solicita nome, sala e período para estudantes, e nome e matéria para professores. O e-mail é obrigatório no fluxo de empréstimo de estudantes. Professores podem ser cadastrados sem e-mail; nesse caso, o backend gera um identificador no domínio `bibi.local`.

### Empréstimos e devoluções

- Estudantes podem solicitar um título por operação e não podem abrir outro empréstimo enquanto houver um ativo associado ao mesmo e-mail. O prazo é informado na operação, com padrão de sete dias na API.
- Professores podem solicitar múltiplos livros e quantidades, respeitando o estoque disponível. O vencimento inicial é no mesmo dia.
- A renovação acrescenta sete dias para estudantes e um dia para professores, contados a partir do vencimento anterior.
- A devolução registra a data e repõe o estoque; repetir a devolução de um registro já devolvido não repõe exemplares novamente.
- Novos empréstimos entram como `Aprovado`. Registros aprovados, vencidos e ainda não devolvidos passam a `Atrasado` nas consultas que atualizam atrasos e na rotina periódica. `Pendente` existe no schema, mas não é o estado inicial do fluxo atual.
- O registro do empréstimo é confirmado antes do envio de e-mail. Uma falha de envio não desfaz o empréstimo.

O painel de devoluções do dia mostra empréstimos ainda ativos com **vencimento hoje**. O ranking considera os últimos 90 dias. Livros adormecidos são os cadastrados há pelo menos seis meses e sem empréstimos nos últimos seis meses.

### Agenda

Selecione uma data e um período (Manhã, Tarde ou Noite) e use a linha correspondente ao número da aula. A grade atual é organizada por aulas da data selecionada, sem cadastro separado de salas físicas. Não é permitido criar agendamentos em datas passadas.

A interface exibe os detalhes das aulas ocupadas. O backend não possui uma restrição de unicidade para data, período e aula; portanto, não há garantia de impedir duplicidades em requisições simultâneas ou feitas diretamente à API.

### Notificações por e-mail

Configure o e-mail da organização e a senha de aplicativo no painel. O código utiliza `smtp.gmail.com:587` com STARTTLS; o servidor SMTP não é configurável pela interface.

Os lembretes são verificados ao iniciar a rotina e, depois, a cada 30 minutos, enquanto o aplicativo estiver aberto. São enviados quando faltam exatamente três dias ou quando o vencimento é hoje; o banco registra o envio bem-sucedido para evitar repetição. Não há envio retroativo de lembretes de dias em que o aplicativo ficou fechado.

## Variáveis de ambiente

[config.py](config.py) carrega as variáveis com `python-dotenv`. Na execução pelo código-fonte, utiliza `load_dotenv()`; no executável, procura `.env` em `_internal/`, dentro da pasta da aplicação. Variáveis já definidas no processo prevalecem sobre o arquivo.

| Variável | Padrão | Uso |
|---|---|---|
| `SECRET_KEY` | `sua-chave-secreta-padrao` | Chave do Flask; defina um valor próprio no ambiente da instalação. |
| `PORT` | `5000` | Porta do servidor iniciado por `app.py`. |
| `FLASK_DEBUG` | `False` | Ativa depuração com `true`, `1` ou `t`, sem diferenciar maiúsculas; o recarregamento automático permanece desligado. |
| `EMAIL_USER` | Vazio | E-mail alternativo quando o banco não contém um par completo de credenciais. |
| `EMAIL_PASSWORD` | Vazio | Senha correspondente ao e-mail alternativo. |
| `LOCALAPPDATA` | Fornecida pelo Windows | Diretório-base para a pasta de dados `BIBI`; é necessário para os caminhos atuais. |

O [env.example](env.example) inclui `SECRET_KEY`, `PORT` e `FLASK_DEBUG`. As variáveis de e-mail continuam sendo lidas por compatibilidade, embora não constem no exemplo. Quando e-mail e senha estão preenchidos na tabela `Configuracoes`, esse par tem preferência sobre as variáveis de ambiente.

As preferências do painel, as credenciais SMTP e o hash da senha administrativa ficam no banco. Tema e algumas preferências visuais ficam no armazenamento local do navegador.

## Dados e backup

```text
%LOCALAPPDATA%\BIBI\
    Biblioteca.db
    uploadedcovers\
    externalcovers\
```

O banco contém acervo, leitores, empréstimos, agenda e configurações. As capas são arquivos separados, armazenados nas duas subpastas. Os arquivos SQLite auxiliares de WAL podem existir durante o uso.

Não há backup ou exportação integrados. Para uma cópia manual, encerre todas as instâncias do BIBI e copie a pasta de dados inteira, preservando o banco e as capas. A pasta de dados é independente da pasta de instalação.

## Build e instalador

### PyInstaller

Com as dependências instaladas, execute na raiz do projeto:

```powershell
python -m PyInstaller --onedir --windowed --name BIBI --icon "static/images/icon.ico" --add-data "static;static" --add-data "templates;templates" --add-data "database/schema.sql;database" app.py
```

A saída fica em `dist/BIBI/`. Distribua a pasta inteira, incluindo `_internal/`: os caminhos atuais esperam esse formato. Templates HTML, templates de e-mail, arquivos estáticos e `database/schema.sql` precisam acompanhar o executável. Se a instalação usar um arquivo `.env`, coloque a configuração própria dessa instalação em `dist/BIBI/_internal/.env`.

Arquivos `*.spec` e `version_info.txt` são ignorados pelo Git. Um `app.spec` pode existir localmente, mas não integra os arquivos versionados. Antes de reutilizar um spec antigo, confira a inclusão de `templates/` e `database/schema.sql`, além dos arquivos estáticos, e as referências a arquivos locais de versão e ambiente. O comando acima gera `BIBI.spec` com os recursos informados.

### Inno Setup

O [setup.iss.example](setup.iss.example) é um modelo que precisa de ajustes para o build atual. Copie-o para `setup.iss`, configure os metadados e substitua a seção `[Files]` para incluir toda a distribuição `onedir`:

```ini
[Files]
Source: "dist\BIBI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
```

O modelo original procura `dist\BIBI.exe` e copia recursos de forma avulsa; isso não corresponde à saída do comando acima. Revise também `AppId`, versão, diretório de saída e opções de atalhos antes de compilar.

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss
```

O executável e o instalador precisam ser validados no Windows de destino; os testes automatizados do código não homologam a distribuição empacotada.

## Verificação

Execute a suíte de testes a partir da raiz:

```powershell
python -m unittest discover -s tests -v
```

`test_regression.py` compara contratos e comportamentos com a implementação preservada em `legacy/`. `test_improvements.py` cobre correções como validação e concorrência de empréstimos, devoluções, notificações e processamento de imagens. Os testes usam bancos temporários e simulam SMTP e chamadas às APIs de livros.

A verificação opcional de layout e interações no navegador requer Playwright e Edge ou Chrome instalado nos caminhos procurados por `tests/browser_check.py`:

```powershell
python -m pip install playwright
python tests/browser_check.py
```

Essa verificação também usa bancos temporários, mas baixa recursos de CDN e requer internet. Resultados registrados em `docs/REFATORACAO.md` correspondem à etapa histórica ali descrita.

## Limitações atuais

- A aplicação foi estruturada para uso desktop no Windows e depende de `LOCALAPPDATA` para resolver o diretório de dados.
- O servidor iniciado por `app.py` é o servidor de desenvolvimento do Flask. Não há configuração de implantação de produção nem autenticação por contas de usuário.
- As APIs de catálogo, o envio de e-mails e as capas externas dependem de rede. Chart.js, Flatpickr e fontes também são carregados de serviços externos; a interface não é totalmente autossuficiente para uso offline.
- O backend usa UTC−3 fixo nas funções de data de Brasília. Algumas consultas SQL usam `date('now')`, e a interface também possui cálculos de data próprios.
- O JavaScript está separado por funcionalidade, mas ainda compartilha funções e variáveis globais. A modularização não implica serviços independentes ou um frontend distribuído separadamente.

## Licença

A documentação anterior declarava licença MIT, mas não há arquivo `LICENSE` versionado nesta revisão. O texto da licença precisa ser incluído para acompanhar formalmente essa declaração.
