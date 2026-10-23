# Imagens da BIBI

Capturas de 23/10/2026, feitas com Playwright/Chromium, em 1920×1080 e 390×844. O catálogo é o da instalação utilizada por `app.py`: 76 títulos. As contas, os leitores, a agenda e a circulação das capturas foram preparados em uma instalação temporária, sem importar contas, senhas, configurações privadas ou históricos da escola.

As imagens mostram o sistema em funcionamento. Os arquivos originais de capas não são distribuídos no repositório ou nos pacotes; aparecem apenas como parte das telas. A IA está ativada com uma integração real do OpenRouter e somente modelos gratuitos autorizados. A conversa foi gerada pelo serviço externo, sem simulação. A chave permanece fora do repositório, dos relatórios e dos pacotes.

A apresentação principal utiliza `acervo.png`, `dashboard.png`, `perfil-leitor.png`, `detalhes-livro.png`, `acervo-escuro.png`, `perfil-mobile-escuro.png` e `ia-conversa.png`.

| Mais recursos | Visualização |
| --- | --- |
| Empréstimos e circulação | [Abrir captura](emprestimos.png) |
| Agenda com atividades | [Abrir captura](agenda.png) |
| Histórico de leitura | [Abrir captura](historico-leitura.png) |
| Listas pessoais | [Abrir captura](listas-pessoais.png) |
| Avaliações e comentários | [Abrir captura](avaliacoes.png) |
| Configurações da biblioteca | [Abrir captura](configuracoes.png) |
| Configuração de IA, ativada e verificada | [Abrir captura](ia-opcional.png) |
| Conversa literária com IA real | [Abrir captura](ia-conversa.png) |
| Acervo em tema escuro | [Abrir captura](acervo-escuro.png) |

[Relatório das capas e pendências](../CAPAS_DISTRIBUICAO.md) · [Validação e distribuição](../DISTRIBUICAO.md) · [Voltar à apresentação](../../README.md)

Para reproduzir as capturas, a equipe de desenvolvimento pode executar `tests/browser_distribuicao.py --catalogo-local CAMINHO_DOS_DADOS`. A origem é aberta somente para leitura dos campos bibliográficos e cópia temporária das capas. SMTP não é utilizado. A integração real exige fornecer temporariamente `BIBI_SCREENSHOT_OPENROUTER_KEY` no ambiente; isso faz chamadas externas e não deve ser usado em testes comuns. Sem a variável, a IA permanece desligada; sem o argumento do catálogo, são usados livros fictícios.
