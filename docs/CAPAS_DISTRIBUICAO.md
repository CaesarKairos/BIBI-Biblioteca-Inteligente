# Capas do acervo — 23/10/2026

A instalação utilizada por `app.py` possui 76 obras. A auditoria verificou arquivos, respostas HTTP, dimensões, decodificação e renderização em Chromium. Inicialmente, 54 capas funcionavam: 20 registros não tinham referência e duas URLs devolviam uma imagem de 1×1 pixel, apesar do HTTP 200.

## Correções aplicadas

As 22 referências foram corrigidas no banco local após backups SQLite consistentes. Nenhuma capa válida foi substituída. As imagens são exibidas remotamente: Open Library, conforme suas [orientações de uso](https://openlibrary.org/dev/docs/api/covers), e o [serviço oficial de imagens por ISBN da Penguin Random House](https://developer.penguinrandomhouse.com/docs/read/enhanced_prh_api/concepts/Images). Os arquivos originais das capas não acompanham o repositório ou os instaladores.

| Título | Fonte bibliográfica | Imagem |
| --- | --- | --- |
| Watchmen | [Registro](https://openlibrary.org/works/OL2897798W) | [Capa](https://covers.openlibrary.org/b/id/7774899-L.jpg?default=false) |
| V de Vinganca | [Registro](https://openlibrary.org/books/OL44707955M) | [Capa](https://covers.openlibrary.org/b/id/13110427-L.jpg?default=false) |
| Batman: Ano Um | [Registro](https://openlibrary.org/works/OL15016298W) | [Capa](https://covers.openlibrary.org/b/id/6462744-L.jpg?default=false) |
| Sandman Vol. 1 | [Registro](https://openlibrary.org/works/OL9200964W) | [Capa](https://covers.openlibrary.org/b/id/7508162-L.jpg?default=false) |
| Sandman Vol. 2 | [Registro](https://openlibrary.org/works/OL15449786W) | [Capa](https://covers.openlibrary.org/b/id/14416396-L.jpg?default=false) |
| Batman: Cavaleiro das Trevas | [Registro](https://openlibrary.org/works/OL3577222W) | [Capa](https://covers.openlibrary.org/b/id/798170-L.jpg?default=false) |
| Maus Volume 2 | [Registro](https://openlibrary.org/works/OL2056808W) | [Capa](https://covers.openlibrary.org/b/id/12606590-L.jpg?default=false) |
| A Hora da Estrela | [Registro](https://openlibrary.org/books/OL62501777M) | [Capa](https://covers.openlibrary.org/b/id/15249744-L.jpg?default=false) |
| O Alienista | [Registro](https://openlibrary.org/books/OL61352956M) | [Capa](https://covers.openlibrary.org/b/id/15171781-L.jpg?default=false) |
| Capitães da Areia | [Registro](https://openlibrary.org/books/OL62256210M) | [Capa](https://covers.openlibrary.org/b/id/15236135-L.jpg?default=false) |
| Vidas Secas | [Registro](https://openlibrary.org/books/OL35663964M) | [Capa](https://covers.openlibrary.org/b/id/12369687-L.jpg?default=false) |
| A Ilha do Tesouro | [Registro](https://openlibrary.org/books/OL27826858M) | [Capa](https://covers.openlibrary.org/b/id/9221290-L.jpg?default=false) |
| A Volta ao Mundo em Oitenta Dias | [Registro](https://openlibrary.org/works/OL30822201W) | [Capa](https://covers.openlibrary.org/b/id/13689116-L.jpg?default=false) |
| Quarto de Despejo | [Registro](https://openlibrary.org/books/OL38221997M) | [Capa](https://covers.openlibrary.org/b/id/12769759-L.jpg?default=false) |
| Marília de Dirceu | [Registro](https://openlibrary.org/books/OL16737554M) | [Capa](https://covers.openlibrary.org/b/id/7246712-L.jpg?default=false) |
| The Age of Alexander (Penguin Classics) | [Registro](https://www.penguin.com.au/books/the-age-of-alexander-9780140449358) | [Capa](https://images.penguinrandomhouse.com/cover/9780140449358) |
| The Dhammapada | [Registro](https://www.penguinrandomhouse.com/books/673323/the-dhammapada-by-anonymous-translated-with-an-introduction-and-notes-by-valerie-roebuck/) | [Capa](https://images.penguinrandomhouse.com/cover/9780140449419) |
| Maus | [Registro](https://openlibrary.org/books/OL9158739M) | [Capa](https://covers.openlibrary.org/b/id/9248756-L.jpg?default=false) |
| Uma Breve História do Tempo | [Registro](https://openlibrary.org/books/OL60470590M) | [Capa](https://covers.openlibrary.org/b/id/15131920-L.jpg?default=false) |
| O Mundo Assombrado pelos Demônios | [Registro](https://openlibrary.org/books/OL30698416M) | [Capa](https://covers.openlibrary.org/b/id/10492588-L.jpg?default=false) |
| Eu | [Registro](https://openlibrary.org/works/OL34307295W) | [Capa](https://covers.openlibrary.org/b/id/13158150-L.jpg?default=false) |
| Laços | [Registro](https://openlibrary.org/books/OL32179904M) | [Capa](https://covers.openlibrary.org/b/id/10836214-L.jpg?default=false) |

## Edições e pendências

Nenhuma das 76 obras permanece sem uma capa renderizável. A identidade da obra e a autoria foram conferidas; isso não comprova a edição física quando o cadastro não informa ISBN ou o ISBN não foi localizado. Esses casos permanecem sinalizados no [relatório por título](validacao/capas-corrigidas.json), sem alterar ISBNs nem mesclar livros.

As duas capas Penguin correspondem exatamente aos ISBNs cadastrados. Para Maus foi identificada a história completa em português; o ISBN local não foi encontrado e a edição física precisa ser conferida. Uma Breve História do Tempo e O Mundo Assombrado pelos Demônios usam referências de edições em português das editoras Intrínseca e Companhia das Letras. Eu usa a edição Eu e outras poesias (L&PM), título também documentado na biblioteca digital da UFSC. Laços corresponde à obra de Vitor e Lu Cafaggi, edição Panini.

Google Books respondeu HTTP 429 durante a pesquisa. Resultados de outra autoria ou volume foram descartados. A bibliografia complementar está no relatório estruturado.

## Persistência e validação

As referências foram persistidas no SQLite, preservando os valores anteriores em backups locais cujos nomes constam no relatório. Uma nova instância isolada leu os campos bibliográficos e os arquivos de capa após a gravação: **76 de 76 capas renderizadas**, sem placeholders. O teste verificou também os detalhes dos livros e as dimensões no navegador; [resultado](validacao/capas-navegador.json).

A BIBI aberta pelo usuário não foi interrompida. As capturas foram refeitas a partir deste catálogo em uma instalação temporária com contas demonstrativas, sem copiar leitores ou configurações particulares. Imagens externas dependem da internet e da disponibilidade da fonte. Não foram publicados bancos privados, dados pessoais ou arquivos originais de capas.
