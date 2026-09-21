# Evolução do BIBI — plano verificável

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
