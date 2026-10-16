# Refinamento da interface

Base: branch `integracao-bibi`, commit `9048eeb`. Referência visual: `d262282`, incluindo o template do modal, `configuracoes.js` e os estilos dos painéis e switches. O código de autenticação antigo não faz parte da implementação.

## Inventário e destino dos recursos

| Origem | Seção do modal | Operações preservadas |
| --- | --- | --- |
| Perfil | Minha conta | Senha real, envio e confirmação da verificação/alteração de e-mail |
| Preferências | Aparência | Tema pessoal, salvo imediatamente |
| Configurações | Biblioteca | Identidade, endereço HTTPS, termos e privacidade |
| Configurações e modal antigo da Agenda | Acervo e agenda | Campos do cadastro, bloqueios, confirmação por senha e quantidade de aulas |
| Configurações e `/emprestimos/circulacao` | Circulação | Regras, renovações, reservas e ocorrências |
| `/leitores/contas` | Contas e acesso | Convites, código presencial, recuperação assistida, revogação, papéis e bloqueios |
| Configurações | E-mail | Remetente único, credencial protegida, remoção, bloqueio de envio e teste SMTP |
| Importações e Configurações | Dados | CSV de livros/leitores, mapeamento, prévia, confirmação, exportação, backup e restauração |
| Configurações | Moderação | Publicação/ocultação com motivo |
| Configurações | Sistema e segurança | Banco, worker, fila de e-mail, espaço, migrações, backup e auditoria |
| Instituição e Configurações | Informações institucionais e Sobre | Textos permitidos, projeto, versão e informações da instalação |

Os templates separados de importação, contas e circulação foram incorporados ao fragmento único `templates/configuracoes.html`. As URLs anteriores continuam protegidas e encaminham à seção correspondente, preservando o leitor e o tipo de importação. Em links internos, o modal abre sobre a página atual.

Leitores recebem somente Minha conta, Aparência, Informações institucionais e Sobre. As APIs continuam usando a autorização de sessão existente; o fragmento também é renderizado conforme o papel da conta.

## Salvamento

Cada formulário possui sua própria ação. Não há “Salvar tudo”. Tema e switches são imediatos; campos de texto e regras exigem a ação de salvar da respectiva seção. Importar, revogar códigos, alterar acesso e restaurar têm ações próprias. O fechamento oferece continuar editando ou descartar os rascunhos; alterações imediatas continuam persistidas. O modal aguarda operações em andamento antes de fechar.

O editor de avatar é o mesmo no primeiro acesso e no Perfil. Suas alterações são rascunhos até Salvar; Cancelar preserva o avatar persistido. Miniaturas usam uma configuração de comparação estável, cache em memória e no máximo quatro solicitações locais simultâneas. Nenhum serviço externo gera os avatares.

A prévia mostra o avatar atual enquanto atualiza; sua solicitação tem prioridade sobre miniaturas ainda na fila. A fonte Nunito também é distribuída localmente, com a licença em `static/vendor/nunito/OFL.txt`, preservando a tipografia sem depender do Google Fonts. O tema persistido é carregado por conta; o armazenamento do navegador funciona como cache.

Após uma restauração concluída, a interface volta ao login, acompanhando a invalidação das sessões feita pelo servidor.

## Arquivos principais

- `templates/configuracoes.html`: fragmento único, formulários e seções por papel.
- `templates/shell.html` e `static/js/settings_modal.js`: diálogo nativo, abertura compartilhada, foco, descarte e reutilização do conteúdo carregado.
- `static/js/gestao.js`, `preferencias.js` e `conta_comum.js`: operações existentes, estado dos formulários, tema e tratamento de falhas.
- `templates/perfil.html` e `static/js/perfil.js`: editor visual reutilizado nos dois fluxos.
- `templates/acesso.html` e `static/js/acesso.js`: login, ativação e recuperação em etapas.
- `static/css/contas.css`: modal, editor, controles compactos e adaptações de tamanho.
- `routes/pages.py` e `routes/gestao.py`: fragmento autenticado e compatibilidade das URLs antigas.

## Verificação reproduzível

```powershell
python -m unittest discover -s tests
python tests/interface_check.py
```

`interface_check.py` executa Flask/Waitress e Chromium com banco temporário, dados sintéticos, bloqueio de recursos externos e SMTP substituído por uma implementação que impede envio. As capturas ficam em `docs/capturas-interface/`. A referência histórica é servida apenas pelo aplicativo temporário de teste, com seu script limitado a solicitações de leitura.

A suíte de serviços e segurança passou com **59 testes**. O teste separado `browser_loan_search.py` também passou: busca por nomes parciais, acentos, filtros, ações, atualização e ordem das respostas.

Também passaram `browser_check.py` e `interface_check.py`. A revisão executada cobriu:

- Bibliotecário e leitor; primeiro acesso e edição posterior do avatar, incluindo salvar e cancelar.
- Login, ativação, solicitação de recuperação sem nova senha, código presencial e capacidade de recuperação desktop por HTTP.
- Modal no Acervo, Perfil, Dashboard, Empréstimos, Agenda e Leitores; salvar, descartar, reabrir e preservar filtros, rolagem e livro selecionado.
- Ausência de nova busca do fragmento ao reabrir; bloqueio de fechamento durante uma preferência ainda em salvamento, incluindo seu select customizado.
- Importação efetiva de livros e leitores, ocorrência de circulação, emissão de código, backup, validação e restauração efetiva, todos sintéticos.
- Logout real e falha simulada sem redirecionamento falso; APIs administrativas negadas ao leitor.
- Claro e escuro, 1366×768, 1920×1080 e 390×844 para ambos os papéis; a regressão geral também cobre tamanhos intermediários e redimensionamento.
- Foco com Tab/Shift+Tab, Escape, retorno de foco, rolagem interna e ausência de IDs duplicados e erros inesperados no console. Respostas 401/403 deliberadas e a falha 503 simulada fazem parte dos testes negativos.

### Capturas

| Tela | Arquivo |
| --- | --- |
| Referência histórica | [d262282](capturas-interface/referencia-d262282.png) |
| Modal no desktop | [1366, claro](capturas-interface/configuracoes-1366-claro.png) · [1920, escuro](capturas-interface/configuracoes-1920-escuro.png) |
| Modal no celular | [Claro](capturas-interface/configuracoes-390-claro.png) · [Escuro](capturas-interface/configuracoes-390-escuro.png) |
| Leitor | [Minha conta no celular](capturas-interface/leitor-configuracoes-mobile.png) · [Aparência no desktop](capturas-interface/leitor-configuracoes-desktop-escuro.png) |
| Avatar | [Primeiro acesso](capturas-interface/avatar-primeiro-acesso.png) · [Edição no celular](capturas-interface/avatar-mobile.png) |
| Acesso | [Login](capturas-interface/login-mobile.png) · [Recuperação](capturas-interface/recuperacao-mobile.png) |
| Saúde da instalação | [Resumo legível](capturas-interface/saude-instalacao.png) |

Esta verificação de navegador não representa homologação de instalador ou da janela Windows/PyWebView.
