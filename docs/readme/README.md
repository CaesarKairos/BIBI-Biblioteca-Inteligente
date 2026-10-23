# Imagens da BIBI

Capturas de 22/10/2026, feitas com Playwright/Chromium, em 1920×1080 e 390×844. O catálogo é o da instalação utilizada por `app.py`: 76 títulos. As contas, os leitores, a agenda e a circulação das capturas foram preparados em uma instalação temporária, sem importar contas, senhas, configurações privadas ou históricos da escola.

As imagens mostram o sistema em funcionamento. Os arquivos originais de capas não são distribuídos no repositório ou nos pacotes; aparecem apenas como parte das telas. A interface de IA é real e está desativada, sem conversas ou respostas simuladas.

A apresentação principal utiliza `acervo.png`, `dashboard.png`, `perfil-leitor.png`, `detalhes-livro.png`, `acervo-escuro.png` e `perfil-mobile-escuro.png`.

| Mais recursos | Visualização |
| --- | --- |
| Empréstimos e circulação | [Abrir captura](emprestimos.png) |
| Agenda com atividades | [Abrir captura](agenda.png) |
| Histórico de leitura | [Abrir captura](historico-leitura.png) |
| Listas pessoais | [Abrir captura](listas-pessoais.png) |
| Avaliações e comentários | [Abrir captura](avaliacoes.png) |
| Configurações da biblioteca | [Abrir captura](configuracoes.png) |
| Configuração opcional de IA, desativada | [Abrir captura](ia-opcional.png) |
| Acervo em tema escuro | [Abrir captura](acervo-escuro.png) |

[Relatório das capas e pendências](../CAPAS_DISTRIBUICAO.md) · [Validação e distribuição](../DISTRIBUICAO.md) · [Voltar à apresentação](../../README.md)

Para reproduzir as capturas, a equipe de desenvolvimento pode executar `tests/browser_distribuicao.py --catalogo-local CAMINHO_DOS_DADOS`. A origem é aberta somente para leitura dos campos bibliográficos e cópia temporária das capas. SMTP e provedores de IA não são utilizados. Sem esse argumento, o roteiro utiliza um catálogo inteiramente fictício para testes.
