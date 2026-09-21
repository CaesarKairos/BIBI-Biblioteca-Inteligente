# Evolução do BIBI — inventário e relatório de entrega

## Inventário inicial (checkout em 20/09/2026)

- Implementado: Flask modular, PyWebView, SQLite, acervo/ISBN/páginas, leitores sem contas, circulação e agenda, busca por nome, cinco prateleiras, capas uniformes, temas e painéis redimensionáveis.
- Parcial: e-mail (SMTP Gmail síncrono/threads e flags no banco), migrações aditivas sem versionamento, validação de imagens, isolamento dos testes por substituição do gerenciador global.
- Ausente: contas/sessões, primeiro acesso, convites, perfil/avatar, reservas/lista pessoal, moderação, CSV, backup/restauração pela interface e auditoria.
- Riscos confirmados: localhost concede administração; chave de sessão padrão; SMTP em texto puro; ranking expõe nomes; exclusão física com histórico; empréstimo pode atualizar pessoa por coincidência de e-mail; capas externas permitem destinos internos; importação de app inicializa banco real.
- Contratos: preservar IDs/data-bibi, APIs de catálogo e circulação, `numero_paginas`, quatro categorias/prateleiras + demonstração, PyWebView e diretório de dados. Controles de acesso antigos por IP serão substituídos, não preservados como comportamento válido.

## Etapas e aceitação

1. Migrações versionadas e backup SQLite anterior; fábrica Flask sem janela/workers implícitos.
2. Primeiro bibliotecário local e atômico; sessões, CSRF, autorização central e auditoria; códigos separados por finalidade; convites presenciais e recuperação.
3. Configuração/segredos sem .env; SMTP e fila persistente; contas e perfil.
4. Circulação por ID, políticas, reservas, estoque e arquivamento.
5. Avatar Adventurer Neutral documentado, lista pessoal, avaliações/moderação, notificações.
6. Pesquisa, CSV, exportações, backup/restauração, saúde, rede/instalador.
7. Testes isolados por domínio, integração no navegador, revisão completa do diff.

Cada etapa deve estar utilizável antes de ser marcada concluída. O banco pessoal não será usado em testes. Não haverá push, publicação ou alteração de infraestrutura.

## Decisões conservadoras

- Primeiro acesso somente em loopback, sem confiar em cabeçalho de proxy. Acesso de rede fica desligado até configuração explícita; HTTPS da escola exige configuração externa e não será descrito como resolvido por HTTP.
- Recuperação e convite são códigos diferentes, com hash, validade, uso único e limitação persistente de tentativas. Presencial não verifica e-mail.
- Renovação solicitada por leitor exige aprovação manual. Não exigir empréstimo anterior para avaliação (não é requisito aprovado).
- Recursos de IA continuam futuros: somente acervo existente, preferências/histórico/avaliações, prioridade para autoras com metadados verificados, análise agregada, conversa sobre leitura e nenhuma decisão administrativa automática.

## Fontes técnicas consultadas

- https://werkzeug.palletsprojects.com/en/stable/utils/ (hash adaptativo)
- https://flask.palletsprojects.com/en/stable/web-security/ (cookies/CSRF)
- https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata (segredos Windows)
- https://docs.pylonsproject.org/projects/waitress/en/stable/ (servidor WSGI)

## Implementação entregue

O [guia de operação](GUIA_OPERACAO.md) descreve todos os fluxos para instalação nova/antiga, primeiro bibliotecário, recuperação offline, convites, SMTP, permissões, circulação, perfil, rede e backup.

| Área | Principais arquivos | Resultado |
|---|---|---|
| Inicialização | `app.py`, `desktop.py`, `config.py` | Fábrica sem efeitos de importação; Waitress, PyWebView e worker explícitos |
| Banco | `database/database.py`, `database/migrations/001_contas.sql`, `002_circulacao.sql` | Backup SQLite anterior, versões e migrações aditivas transacionais; integridade referencial |
| Segurança | `utils/auth.py`, `utils/secrets_store.py`, `routes/contas.py`, `services/contas_service.py` | Contas/sessões, CSRF/origem/host, setup local, códigos com hash, rate limit, DPAPI e revogação |
| Circulação | `services/circulacao_service.py`, `emprestimos_service.py`, `leitores_service.py`, `livros_service.py` | ID do leitor, políticas, estoque atômico, reservas, ocorrências e arquivamento |
| Perfil | `routes/perfil.py`, `services/avatar_service.py`, `templates/perfil.html`, `static/js/perfil.js` | Avatar local editável, histórico, lista pessoal, reservas, avaliações, notificações e credenciais |
| Mensagens | `services/mensagens_service.py`, `email_service.py` | SMTP TLS, destinatários verificados, fila persistente e quatro templates existentes |
| Gestão | `routes/gestao.py`, `services/dados_service.py`, `templates/gestao.html`, `static/js/gestao.js` | CSV, relatórios, backup/restauração, políticas, saúde, auditoria, convites e moderação |
| Acervo/interface | `services/catalogo_service.py`, `templates/app.html`, `static/js/{livros,leitores,emprestimos,conta_acervo,ui,app}.js`, `static/css/contas.css` | Busca combinada/progressiva, capas fixas, cinco prateleiras, ações por estado, integração com conta e layout responsivo |
| Acesso e textos | `templates/acesso.html`, `instituicao.html`, `static/js/acesso.js`, `conta_comum.js`, `routes/pages.py` | Primeiro acesso, login/convite/recuperação e textos institucionais públicos escapados |
| Distribuição | `packaging/BIBI.spec`, `setup.iss.example`, `requirements.txt`, `static/vendor/` | Recursos completos no build; Chart.js/Flatpickr locais, sem .env ou dados pessoais |

`numero_paginas` e seus testes anteriores foram preservados. Metadados vêm das fontes existentes: `number_of_pages` da Open Library, `page_count` da BrasilAPI e `pageCount` do Google Books, com validação opcional/fallback. Não existe variação de altura por páginas: as capas das prateleiras permanecem 80 × 110 px. A quinta prateleira continua uma demonstração identificada, preparada para receber IDs; Dashboard e recomendações usam o gatinho SVG. Nenhuma IA foi integrada.

## Decisões e limites

- As novas regras escolares não foram arbitradas: defaults legados são mantidos até configuração explícita. O prazo de retirada precisa ser definido para habilitar reservas. Aprovação de renovação é manual.
- O último bibliotecário ativo é protegido; alteração de acesso revoga sessões. Uma ativação presencial deixa e-mail não verificado e continua funcional sem SMTP.
- Backup portátil não exporta DPAPI e não ressuscita sessões/códigos. Restauração gera novo código offline e remove a credencial SMTP. Há rollback testado após falha.
- Um processo de desktop/worker por biblioteca. Requisições e rotina periódica compartilham o bloqueio de operações durante restauração. Não é uma solução de coordenação entre múltiplos servidores.
- URLs de capas baixadas pelo servidor são restritas às fontes oficiais existentes, HTTPS, IP público e sem redirecionamento. Outras imagens podem ser enviadas pelo upload validado.
- Rede escolar exige proxy HTTPS/certificado configurados pela instituição. Nenhum firewall, certificado, DNS ou infraestrutura foi alterado.
- Build executado não equivale a instalador homologado. Janela nativa e instalação/desinstalação em máquina limpa, rede real e SMTP real permanecem para homologação local.

## Verificações executadas em 21/09/2026

- `python -m unittest discover -s tests -q`: **49 testes aprovados**, incluindo banco antigo/novo, migrações e rollback, autenticação, concorrência de setup/ativação/estoque, CSRF/host/HTTPS, worker lento sem bloquear requisições, limites, PIN, bloqueio/papéis, convites, verificação de e-mail, reservas, políticas, avatar, moderação, CSV, backup/restauração e segredos.
- `python tests/browser_check.py`: **aprovado**, com Flask/Waitress reais, configuração inicial, ativação/login de leitor, privacidade, perfil, avatar salvo/cancelado, pesquisa, cinco prateleiras, indisponibilidade, detalhes/X, painéis e 1366×768, 1920×1080, 800×900 e 390×844, em claro/escuro. Capturas também revisadas em gestão e editor do avatar.
- `python tests/browser_loan_search.py`: **aprovado**, cobrindo nome parcial, acentos, caixa, filtros, ações, atualização, vazio/limpeza e ordem de respostas.
- `python -m compileall -q app.py desktop.py routes services utils database tests`: **aprovado**.
- PyInstaller no Windows, Python 3.11.6, com `packaging/BIBI.spec`: **build concluído** em diretório temporário. Presença de templates/schema/migrações/DiceBear/vendor e ausência de `.env`, banco e segredos conferidas.
- `git diff --check`: sem erros de whitespace. Contratos DOM e alterações cumulativas comparados com a base anterior; exclusões de código de mutação de empréstimos correspondem à centralização no serviço de circulação, não à remoção dessas operações.

Os testes usam dados sintéticos, banco temporário e SMTP simulado; o navegador bloqueia chamadas externas. Erros deliberadamente injetados em testes de rollback e resposta segura podem aparecer no log, com a suíte terminando em OK. O banco real da biblioteca não foi usado. Não houve push, publicação nem alteração de documento acadêmico.

Os testes antigos que tratavam IP local como autenticação foram substituídos por sessões reais e rejeição de acessos não autenticados; não se preservou esse comportamento inseguro como contrato de regressão.
