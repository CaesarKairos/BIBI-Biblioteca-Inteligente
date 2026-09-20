# Modernização visual do BIBI

A aplicação continua em Flask, SQLite, HTML, CSS e JavaScript nativo. O acervo, a agenda, os empréstimos, os leitores, as configurações, as permissões por endereço e os atalhos foram preservados. Nenhuma integração ou dependência de IA foi adicionada.

## Interface

- Shell ocupa a janela, sem limite global de largura, moldura arredondada ou margem externa. Desktop mantém sidebar, conteúdo e painel direito, cada um com seu scroll quando necessário. As laterais começam em 212/292 px em 1366 px e 232/320 px em 1920 px; o centro recebe o restante, descontando duas divisórias de 8 px.
- Divisórias permitem arrastar as laterais: navegação de 180–320 px (mínimo de 148 px em telas compactas), detalhes de 220–420 px. Limites efetivos reservam 320 px ao centro sempre que a janela comporta; em 701 px o centro tem 317 px. Setas ajustam 16 px, Home/End usam os limites e dois cliques restauram o padrão. Preferências ficam em `bibiPanelWidths` no armazenamento local e são limitadas novamente ao redimensionar a janela. Em até 700 px as divisórias são ocultadas e as áreas ficam empilhadas.
- Tokens de superfícies, texto, verde terroso, bordas, sombras, estados, prateleiras, raios e transições atendem aos dois temas. Nunito, logo, gato e capas continuam presentes.
- Em até 700 px, as áreas ficam em sequência no documento, sem drawer. Selecionar uma capa leva aos detalhes. Entre 701 e 900 px as três colunas são compactadas.
- Painel direito permanece vazio sem seleção. O botão × limpa a seleção e devolve o foco ao livro; a capa de detalhes permanece em 140×200 px, com `background-size: contain`. Descrição e metadados têm alinhamento à esquerda e a descrição completa pode ser lida.
- Livros são botões acessíveis com título/autor e disponibilidade no nome acessível e tooltip. Sem exemplares: opacidade 0,64 e saturação discreta, sem bloquear seleção.
- Microinterações de aproximadamente 200 ms, foco visível, labels de formulários, modais com foco contido/restaurado e Escape, seletores com setas, gráficos com descrição textual e estados vazios. `prefers-reduced-motion` desativa transições, animações de gráficos e movimento do gato.

## Banco e páginas

`Livros.numero_paginas` é `INTEGER`, opcional (`NULL`) e positivo. O schema e a migração incluem uma restrição `CHECK` de tipo inteiro e valor positivo.

Na inicialização, o mecanismo existente consulta `PRAGMA table_info(Livros)` dentro de `BEGIN IMMEDIATE`. Executa `ALTER TABLE ... ADD COLUMN` apenas quando a coluna não existe. Registros antigos recebem `NULL`; não há reconstrução, remoção de tabelas ou alteração do estoque. Inicializações seguintes preservam a coluna e os valores já salvos.

Cadastro manual e edição aceitam páginas no formulário e na API. O backend rejeita zero, negativos, frações, booleanos, objetos e textos inválidos com HTTP 400, antes de gravar. O limite superior é o maior inteiro seguro do JavaScript para preservar o valor no percurso JSON/frontend. Campo omitido no PUT preserva páginas existentes; `null` ou texto vazio limpa o valor. GET e POST de `/api/livros` incluem `numero_paginas`; as rotas existentes delegam ao serviço sem precisar de novas URLs.

A busca em cascata complementa páginas na mesma ordem das fontes já usadas:

| Fonte | Campo real |
|---|---|
| [Open Library, Books API](https://openlibrary.org/dev/docs/api/books) | `number_of_pages` |
| [BrasilAPI, schema ISBN](https://github.com/BrasilAPI/BrasilAPI/blob/main/pages/docs/doc/isbn.json) | `page_count` |
| [Google Books, Volume](https://developers.google.com/books/docs/v1/reference/volumes) | `volumeInfo.pageCount` |

Valores ausentes ou inválidos são tratados como `None`, sem impedir cadastro. Uma fonte posterior pode complementar a anterior. O fallback por título já existente continua disponível; metadados de edições diferentes podem divergir e podem ser corrigidos manualmente. Livros já cadastrados não disparam buscas externas automaticamente.

As capas das prateleiras usam o tamanho original fixo de **80×110 px**, independentemente do número de páginas. A variação por páginas foi removida; o campo continua disponível como informação bibliográfica. A imagem usa `cover`, preservando a proporção e recortando o excesso para preencher a capa sem faixas laterais geradas pelo dimensionamento; detalhes e thumbnails administrativos mantêm seus tamanhos próprios.

O modo noturno combina fundos em carvão quente, superfícies com leve tom oliva e destaques em verde sálvia. Botões têm cores próprias, separadas das cores de texto, com verde e vermelho mais discretos e rótulos claros. Calendário, seletores, bordas e estados de disponibilidade acompanham a mesma paleta.

Scrollbars usam tokens próprios para trilho, indicador e hover nos dois temas. Na tabela de empréstimos, as ações são um grupo flex **dentro** de um `td`, preservando o alinhamento e a altura de todas as células da linha. “Todos” usa um tom neutro terroso, distinto do verde de “Ativos”. A tabela tem largura mínima legível e rolagem horizontal interna quando o centro fica estreito.

Na página inicial, Hero e Sobre Nós compartilham um container de altura limitada à janela (máximo de 760 px). Conteúdo longo rola dentro dessa área sem aumentar a moldura. O tema segue `bibiConfig.darkMode`, com fallback para a preferência antiga.

## Preparação para a BIBI inteligente

As quatro prateleiras por categoria continuam com sua lógica original. A quinta, acima delas, chama-se **Recomendações da BIBI** e usa o ícone fornecido `static/images/cat-svgrepo-com.svg` como máscara CSS, cuja cor acompanha o tema. Mostra até oito livros em ordem de ID, respeitando a busca, identificados como amostra do acervo e “Em preparação”. Não representa recomendação de IA.

`definirRecomendacoesBibi(ids)` recebe uma lista ordenada de IDs, remove duplicatas e ignora IDs ausentes; uma lista vazia mantém a prateleira vazia. `null` restaura o fallback de demonstração. Esse é o ponto de entrada estrutural futuro, sem endpoint ou serviço de IA nesta versão.

No Dashboard, **BIBI** apresenta cumprimento por horário e resumo determinístico de títulos/devoluções do dia. O Dashboard e as recomendações usam o mesmo ícone `cat-svgrepo-com.svg`, pela classe compartilhada `bibi-cat-icon`, que acompanha a cor do tema. Esse é o ícone padrão para os espaços destinados à IA da BIBI. `atualizarMensagemBibi({saudacao, texto})` atualiza o texto com `textContent`. A futura integração poderá alimentar esses campos automaticamente. Não existem botões de geração, prompts ou chatbot. O painel direito vazio não recebeu insights fictícios.

## Arquivos

- Persistência: `database/schema.sql`, `database/database.py`, `services/livros_service.py`.
- Interface: `templates/app.html`, `static/css/{app,landing}.css`, `static/js/{template,app,ui,livros,dashboard,agenda,leitores,emprestimos,landing,layout}.js`; uso do SVG de gato fornecido.
- Verificação: `tests/test_pages.py`, `tests/test_regression.py`, `tests/test_improvements.py`, `tests/browser_check.py`.
- Documentação: `README.md`, este relatório.

## Verificação

```powershell
python -m unittest discover -s tests -v
$env:BIBI_SCREENSHOTS = Join-Path $env:TEMP 'bibi-modernizacao-review'
python tests/browser_check.py
git diff --check
```

Os testes usam somente bancos temporários. A suíte de backend tem 35 testes, incluindo criação com/sem páginas, edição/limpeza/preservação, API pública, bloqueio de escrita não administrativa, formatos das fontes, fallback e migração repetida com preservação de livros, empréstimos e configurações.

O teste Playwright preserva os fluxos de erro, repetição de envio e proteção de texto já existentes. Ambas as páginas têm verificações de comportamento e geometria próprias, pois a igualdade com o layout antigo não seria um critério válido para o redesign. Cobre os dois perfis, temas, 1366×768, 1920×1080, 800×900 e 390×844, cinco prateleiras, seleção/fechamento/nova seleção, teclado, páginas nos formulários, disponibilidade e ausência de overflow global. Também verifica arraste, persistência e limites das laterais, alinhamento das células de empréstimos, cores distintas dos filtros, ícone de gato e altura constante do Hero/Sobre Nós. Capturas incluem acervo, dashboard, agenda, empréstimos, formulários e página inicial; capas sintéticas são fixtures exclusivas do teste.

Resultados em 20/09/2026: **35 testes de backend aprovados**; **Playwright aprovado** para os dois perfis e quatro resoluções, sem erros JavaScript na aplicação atual. Após a revisão visual, uma checagem adicional confirmou fundos dos modais nos dois temas em três resoluções, gráficos vazios ocultos, movimento reduzido e seleção animada. O diff completo foi revisado e `git diff --check` passou. Os testes não abriram o banco de uso real; sua migração ocorrerá na próxima inicialização normal do aplicativo.

Limitações: a execução browser depende das CDNs já usadas e de Edge/Chrome com Playwright; fontes externas usam fallback determinístico nas capturas. Os testes não homologam o instalador ou a janela pywebview empacotada. A classificação original por quatro categorias foi mantida; títulos com categorias externas diferentes continuam seguindo a regra anterior e podem aparecer na amostra da quinta prateleira.
