# Capas do acervo — 22/10/2026

A instalação acessada por `app.py` possui 76 títulos. A auditoria verificou arquivos, respostas HTTP, decodificação das imagens e carregamento em Chromium. Antes da correção, 54 capas renderizavam; 20 registros não tinham referência e duas URLs retornavam uma imagem de 1×1 pixel com HTTP 200.

## Correções aplicadas

Foram atualizadas 15 referências no banco local, após backup SQLite consistente. Nenhuma capa existente e válida foi substituída. As imagens são exibidas por URLs da Open Library, conforme suas [orientações para uso de capas](https://openlibrary.org/dev/docs/api/covers). Não foram incluídos arquivos de capa no repositório ou nos instaladores.

A pesquisa por ISBN não encontrou vários registros de quadrinhos. Nesses casos, a identificação foi feita pela obra, autoria e volume, com revisão visual. A correspondência com a edição física ainda precisa ser confirmada pela biblioteca; os ISBNs cadastrados não foram alterados. Para os títulos sem ISBN, foram priorizadas capas em português e registradas as edições consultadas.

| Título | Fonte bibliográfica | Referência da imagem |
| --- | --- | --- |
| Watchmen | [Open Library](https://openlibrary.org/works/OL2897798W) | [Capa](https://covers.openlibrary.org/b/id/7774899-L.jpg?default=false) |
| V de Vinganca | [Open Library](https://openlibrary.org/books/OL44707955M) | [Capa](https://covers.openlibrary.org/b/id/13110427-L.jpg?default=false) |
| Batman: Ano Um | [Open Library](https://openlibrary.org/works/OL15016298W) | [Capa](https://covers.openlibrary.org/b/id/6462744-L.jpg?default=false) |
| Sandman Vol. 1 | [Open Library](https://openlibrary.org/works/OL9200964W) | [Capa](https://covers.openlibrary.org/b/id/7508162-L.jpg?default=false) |
| Sandman Vol. 2 | [Open Library](https://openlibrary.org/works/OL15449786W) | [Capa](https://covers.openlibrary.org/b/id/14416396-L.jpg?default=false) |
| Batman: Cavaleiro das Trevas | [Open Library](https://openlibrary.org/works/OL3577222W) | [Capa](https://covers.openlibrary.org/b/id/798170-L.jpg?default=false) |
| Maus Volume 2 | [Open Library](https://openlibrary.org/works/OL2056808W) | [Capa](https://covers.openlibrary.org/b/id/12606590-L.jpg?default=false) |
| A Hora da Estrela | [Open Library](https://openlibrary.org/books/OL62501777M) | [Capa](https://covers.openlibrary.org/b/id/15249744-L.jpg?default=false) |
| O Alienista | [Open Library](https://openlibrary.org/books/OL61352956M) | [Capa](https://covers.openlibrary.org/b/id/15171781-L.jpg?default=false) |
| Capitães da Areia | [Open Library](https://openlibrary.org/books/OL62256210M) | [Capa](https://covers.openlibrary.org/b/id/15236135-L.jpg?default=false) |
| Vidas Secas | [Open Library](https://openlibrary.org/books/OL35663964M) | [Capa](https://covers.openlibrary.org/b/id/12369687-L.jpg?default=false) |
| A Ilha do Tesouro | [Open Library](https://openlibrary.org/books/OL27826858M) | [Capa](https://covers.openlibrary.org/b/id/9221290-L.jpg?default=false) |
| A Volta ao Mundo em Oitenta Dias | [Open Library](https://openlibrary.org/works/OL30822201W) | [Capa](https://covers.openlibrary.org/b/id/13689116-L.jpg?default=false) |
| Quarto de Despejo | [Open Library](https://openlibrary.org/books/OL38221997M) | [Capa](https://covers.openlibrary.org/b/id/12769759-L.jpg?default=false) |
| Marília de Dirceu | [Open Library](https://openlibrary.org/books/OL16737554M) | [Capa](https://covers.openlibrary.org/b/id/7246712-L.jpg?default=false) |

## Pendências

| Título | Motivo |
| --- | --- |
| The Age of Alexander (Penguin Classics) | Open Library retorna 1×1 pixel; edição encontrada na Penguin, mas sem autorização específica confirmada para este uso. |
| The Dhammapada | Open Library retorna 1×1 pixel; edição encontrada na Penguin, mas sem autorização específica confirmada para este uso. |
| Maus | ISBN não localizado; título genérico não esclarece se o exemplar é o volume I ou a edição integral. |
| Uma Breve História do Tempo | Sem ISBN/edição; não foi encontrada capa em português identificada com segurança na fonte consultada. |
| O Mundo Assombrado pelos Demônios | Sem ISBN/edição; encontrada obra original em inglês, sem edição em português confirmada. |
| Eu | Resultados encontrados para Eu e outras poesias; composição/edição do exemplar não confirmada. |
| Laços | Sem ISBN/edição; não foi localizada uma correspondência bibliográfica segura nas fontes consultadas. |

Google Books respondeu HTTP 429 durante a busca por ISBN. Resultados com título semelhante, autoria diferente ou outro volume foram descartados. Fontes editoriais encontradas: [The Age of Alexander](https://www.penguin.com.au/books/the-age-of-alexander-9780140449358) e [The Dhammapada](https://www.penguinrandomhouse.com/books/673323/the-dhammapada-by-anonymous-translated-with-an-introduction-and-notes-by-valerie-roebuck/).

## Persistência e validação

As referências foram gravadas no SQLite da instalação, com comparação do valor anterior para preservar alterações concorrentes. O backup anterior permanece na pasta local `backups`; o nome está no [relatório estruturado](validacao/capas-corrigidas.json). Uma nova aplicação com cópia apenas dos campos bibliográficos e arquivos de capa foi aberta em Chromium após a gravação: **69 imagens renderizadas e sete pendências**. Isso verifica a leitura persistida por uma nova instância sem reiniciar nem interromper a BIBI aberta pelo usuário.

O tratamento visual do acervo e dos detalhes agora mantém o placeholder quando a imagem não carrega ou tem dimensões de placeholder remoto. As URLs externas continuam dependendo de internet e da disponibilidade da fonte. Nenhum banco, leitor ou segredo da instalação foi publicado.
