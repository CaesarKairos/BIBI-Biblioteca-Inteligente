# Finalização e acervo — 19/10/2026

## Importação executada na instalação local

O ZIP fornecido foi aberto como arquivo de dados, sem executar seu código. O SQLite de origem passou por `integrity_check` e `foreign_key_check`. Foram encontrados 32 livros, 32 capas referenciadas e existentes, 6 leitores, 6 empréstimos e 1 agendamento. Outras seis imagens sem referência não foram importadas.

Foram adicionados **32 livros e 32 capas** em `%LOCALAPPDATA%\BIBI`, com banco `Biblioteca.db` e imagens em `uploadedcovers` / `externalcovers`. As URLs antigas `/static/images/...` passaram a usar `/uploadedcovers/...` e `/externalcovers/...`. Os arquivos mantiveram seus nomes; colisões com conteúdo diferente recebem sufixo SHA-256. As imagens são verificadas pelo mesmo validador usado nos uploads.

A importação foi somente bibliográfica. Os seis leitores, seis empréstimos e o agendamento permaneceram no ZIP original, sem criação de contas ou senhas. Como os empréstimos antigos não foram transportados, a disponibilidade dos títulos importados foi reconciliada com o estoque total: **562 exemplares disponíveis de 562**. Não se inferiu gênero ou nacionalidade da autoria.

Antes da gravação foi criado o backup consistente:

`%LOCALAPPDATA%\BIBI\backups\antes-acervo-1792454408292893500.zip`

O relatório local é `backups\importacao-acervo-1792454408408814400.json`. Depois da importação, o banco passou novamente nas verificações de integridade e as 32 imagens foram encontradas nos destinos. As linhas preexistentes de Contas e Configuracoes foram comparadas antes/depois e permaneceram iguais; os hashes dos arquivos preexistentes de configuração/segredos também permaneceram iguais. Havia uma conta bibliotecária e nenhum livro, leitor ou empréstimo na instalação de destino.

O backup anterior à importação é uma cópia técnica local do SQLite e das imagens, para recuperação com o programa fechado; não é o arquivo portátil com manifesto produzido pelo botão de backup do aplicativo. Os segredos permanecem no arquivo original da instalação e não foram incluídos nesse ZIP.

Essa verificação da instalação real foi feita no banco e nos arquivos. Os fluxos de navegador usam uma instalação descartável com o mesmo catálogo e contas sintéticas, sem assumir acesso à conta real do bibliotecário.

## Procedimento reproduzível

Feche a BIBI pelo ícone da bandeja. No ambiente Python 3.11 com as dependências instaladas:

```powershell
# Examina a origem sem gravar na instalação
python tools/importar_acervo.py --zip "C:\caminho\acervo.zip"
# Cria backup e adiciona o catálogo na instalação local
python tools/importar_acervo.py --zip "C:\caminho\acervo.zip" --aplicar
# Para testar, informe uma pasta descartável explicitamente
python tools/importar_acervo.py --zip "C:\caminho\acervo.zip" --destino "$env:TEMP\bibi-acervo-teste" --aplicar
```

O importador não substitui o banco, contas, configurações ou credenciais. A prévia mostra a origem; a aplicação verifica duplicatas no destino por registro de importação e ISBN. Conflitos bibliográficos são relatados sem sobrescrever a obra existente. Sem ISBN, títulos/autores coincidentes exigem revisão. Falhas de transação desfazem os novos registros e removem somente as novas imagens daquela tentativa. A repetição do mesmo arquivo não duplica as obras. O backup anterior é local e contém dados da instalação: não deve ser publicado.

## Recursos preservados e ajustes

Contas, convites, avatar local, favoritos, Quero ler, circulação, reservas, renovação administrativa, comentários, moderação, notificações, SMTP institucional, Dashboard, backup e servidor HTTPS já existiam e foram reutilizados. O roteamento de IA não foi modificado.

Foi acrescentado o registro voluntário **Livros lidos**, separado do histórico de empréstimos. Marcar/desmarcar uma obra não devolve exemplares, não altera estoque nem publica essa informação para outras contas. O perfil passa a apresentar capas nos empréstimos, histórico, listas, reservas e avaliações. As avaliações usam estrelas acessíveis por teclado e cartões de opiniões sem identificação pessoal. A edição conserva o fluxo de moderação já existente. O cancelamento de reserva agora gera notificação interna uma única vez, mesmo sem SMTP.

O ensaio de renovação identificou um bloqueio no fechamento das Configurações: a atualização removia o botão da lista antes da conclusão do contador de operações. `settings_modal.js` agora acompanha operações iniciadas mesmo quando seu elemento é removido; o fechamento continua bloqueado durante a execução, mas é liberado ao concluir. Os controles secundários das avaliações também receberam o estilo compartilhado da biblioteca.

O teste de cancelamento também encontrou que `accountApi` declarava JSON mesmo nas ações sem corpo. O backend rejeitava corretamente o JSON vazio, impedindo operações pessoais de remoção. O helper agora envia esse cabeçalho somente quando há dados. A validação mantém as regras de sessão e CSRF do servidor.

As migrações são aditivas: `006_leituras_importacao.sql` cria os registros pessoais e o mapeamento da importação sem substituir tabelas existentes. O catálogo legado não ganha metadados de autoria presumidos. A seleção determinística e a preferência por autoras brasileiras continuam dependendo dos metadados confiáveis cadastrados pela escola.

## Validação

`python -m unittest discover -s tests -p 'test_*.py' -v`: **116 testes aprovados em 462,165 s**. A execução inclui contratos de provedores simulados, roteamento, prioridade bibliográfica, contas, configurações, circulação, segurança, HTTPS local, importação e registros pessoais. Falhas e erros TLS simulados aparecem no log dos respectivos testes negativos; o resultado final foi `OK`. Nenhum teste usa créditos de IA ou envia e-mail real.

`python -m unittest tests.test_importacao_acervo tests.test_leituras -v` também foi usado durante o desenvolvimento. Os cinco testes do importador verificam duplicatas, conflito de ISBN, colisão de imagens, rollback e rejeição de caminho inseguro. Os quatro de leitura/notificações verificam isolamento, idempotência, estoque, persistência após reinício/backup, cancelamento e avisos sem SMTP. Os arquivos JavaScript alterados passaram por `node --check` e o diff por `git diff --check`.

O ZIP original também foi importado duas vezes em um destino temporário: a primeira operação adicionou 32 livros e a segunda reconheceu os 32 existentes sem duplicá-los. A comparação da instalação real com a origem confirmou os campos bibliográficos e SHA-256 das 32 imagens; banco íntegro, sem violações de chave estrangeira.

### Navegador real

`python tests/browser_pre_apresentacao.py --zip "C:\caminho\acervo.zip"`: **aprovado**, com Waitress e Chromium, banco descartável, duas contas de estudantes e uma bibliotecária sintéticas, rede externa bloqueada e SMTP simulado. A configuração das regras de circulação e a preparação do título indisponível usaram API; as ações de cadastro de leitor, convite, ativação, avatar, favorito, leitura, avaliação, empréstimo, pedido/aprovação de renovação, devolução, reserva/cancelamento, moderação, backup, cadastro/edição de livro e logout/login foram executadas na interface. O estado final foi conferido por UI e APIs.

O teste confirmou quatro prateleiras sem IA, os 32 livros importados e suas 32 capas com HTTP 200, busca por título/autor/ISBN, detalhes e desmarcação, isolamento da lista de lidos, comentário publicado visível por outra conta sem identificação, edição sinalizada e revisão, exclusão própria preservando a opinião alheia, estoque/histórico após devolução, fila e separação da reserva, aviso de cancelamento e leitura de notificação. A renovação permanece sujeita à aprovação administrativa.

Foram salvas **60 capturas PNG** em [`validacao/final-pre-apresentacao/`](validacao/final-pre-apresentacao/), com resultados estruturados em [`resultados.json`](validacao/final-pre-apresentacao/resultados.json) e [`testes-servicos.json`](validacao/final-pre-apresentacao/testes-servicos.json). A matriz cobre acervo, perfil, detalhes/avaliações, Dashboard e Configurações em **1366×768, 1920×1080, 800×900 e 390×844**, claro e escuro. Foram inspecionadas capturas de estrelas, leitura, moderação, Dashboard, Configurações e perfil/detalhes móveis. Não houve erro JavaScript nem transbordamento horizontal na rodada final. As listas e painéis mantêm rolagem própria; as imagens de tela inteira no celular são mais altas que a área visível.

As primeiras tentativas revelaram seletores ambíguos do roteiro, espera de rede excedida e os dois defeitos compartilhados descritos acima. Não foram consideradas aprovações. A rodada final passou integralmente após as correções. As capturas de Dashboard podem mostrar 34 títulos: 32 da origem mais dois títulos sintéticos criados para testar cadastro e reservas; esses dois não foram adicionados à instalação real.

### Limites e preparação manual

- Não houve conexão real com provedores de IA, consumo de créditos ou envio SMTP real. A arquitetura de IA permaneceu inalterada; testes de contrato/roteamento são simulados.
- A suíte verificou HTTPS no próprio servidor; não foi feito novo ensaio em outro dispositivo físico, nem certificação de firewall/rede escolar.
- O instalador e a experiência completa de bandeja/janela em computador limpo ainda precisam de homologação. O teste do executável comprovou servidor, cadastro, catálogo e capas em diretório isolado.
- A instalação real conserva sua conta anterior. A validação por navegador usou contas temporárias, sem alterar sua senha ou criar estudantes nela. Para a apresentação, crie convites e contas de demonstração explicitamente e guarde os códigos fora de material público.
- As seis pessoas, os seis empréstimos e o agendamento do banco legado não foram migrados; permanecem na fonte preservada. Não há pendência para exibir o catálogo importado, mas esses históricos não estarão na aplicação atual.
- A revisão das condições do provedor e a configuração de SMTP continuam sob responsabilidade da escola. Sem esses serviços, o catálogo e os recursos convencionais continuam funcionando.

## Empacotamento

O build Windows foi executado com `python -m PyInstaller --noconfirm --distpath "$env:TEMP\bibi-final-dist" --workpath "$env:TEMP\bibi-final-build" packaging/BIBI.spec`. A primeira tentativa no `dist/BIBI` anterior encontrou arquivos bloqueados, portanto foi preservada e o build usou um destino novo.

A distribuição testada está disponível em **`dist/BIBI-pre-apresentacao/BIBI.exe`**, com `_internal`. O spec existente já recolhe a pasta de migrações, incluindo a 006, e os templates/assets alterados; não precisou de dependências novas. Não há banco, arquivo original do acervo ou segredo na distribuição. O `base_library.zip` presente é a biblioteca Python do PyInstaller.

O comando `python tests/smoke_executavel.py --exe "$env:TEMP\bibi-final-dist\BIBI\BIBI.exe" --zip "C:\caminho\acervo.zip"` passou: processo real, servidor HTTP de loopback, primeiro cadastro, 32 livros e 32 capas HTTP 200, usando LOCALAPPDATA temporário. O processo foi encerrado ao terminar; os dados reais não foram abertos por esse teste. A primeira execução desse roteiro omitia a versão dos termos no cadastro e foi corrigida para ler a versão servida pela própria tela.

Os últimos ajustes de CSS e dos helpers JavaScript foram sincronizados com a distribuição em `dist/BIBI-pre-apresentacao/_internal`, comparados por hash e o mesmo teste foi repetido com `--exe dist\BIBI-pre-apresentacao\BIBI.exe`, novamente aprovado. A distribuição inteira precisa acompanhar o executável.

O instalador Inno Setup não foi construído. O comportamento completo da janela nativa/bandeja em computador limpo e o acesso por outro dispositivo não foram homologados nesta execução. Os testes automatizados do servidor local não equivalem a esses ensaios físicos.

## Arquivos alterados

| Arquivos | Finalidade |
|---|---|
| `services/importacao_acervo.py`, `tools/importar_acervo.py` | Inspeção, backup, importação aditiva e ajuste de capas |
| `database/migrations/006_leituras_importacao.sql` | Registro voluntário de leitura e mapeamento de IDs importados |
| `routes/perfil.py`, `templates/perfil.html`, `static/js/perfil.js` | Lista privada de lidos e cartões com capas no perfil |
| `static/js/conta_acervo.js`, `static/css/contas.css` | Marcação de leitura, estrelas e cartões de opiniões |
| `static/js/conta_comum.js`, `static/js/settings_modal.js` | Requisições sem corpo e conclusão das operações no modal |
| `services/circulacao_service.py` | Aviso interno de cancelamento de reserva, com deduplicação existente |
| `tests/test_importacao_acervo.py`, `tests/test_leituras.py` | Integridade, conflitos, rollback, privacidade, notificações e persistência |
| `tests/browser_pre_apresentacao.py`, `tests/smoke_executavel.py` | Navegador real e teste isolado do executável |
| `.gitignore`, `README.md`, este relatório e `docs/validacao/final-pre-apresentacao/` | Proteção dos arquivos locais, instruções e evidências |

Nenhum arquivo em `services/ai/` foi alterado.

## Roteiro de sete minutos

1. **0:00–1:00 — Acervo:** abrir a BIBI, mostrar as capas importadas, buscar título/autor/ISBN e abrir/fechar detalhes.
2. **1:00–2:00 — Bibliotecário:** mostrar um cadastro de leitor sintético, gerar convite e registrar empréstimo.
3. **2:00–3:00 — Estudante:** entrar na conta de demonstração, personalizar avatar e adicionar um favorito/Quero ler.
4. **3:00–4:00 — Leitura:** marcar um livro como lido e mostrar a diferença entre essa lista e o histórico físico.
5. **4:00–5:00 — Opiniões:** escolher estrelas, publicar comentário, mostrar a opinião em outra conta e a revisão administrativa.
6. **5:00–6:00 — Circulação:** solicitar renovação, aprovar na biblioteca, devolver e conferir histórico/disponibilidade. Mostrar fila de reserva e notificação.
7. **6:00–7:00 — Gestão:** apresentar indicadores reais, Configurações, backup e endereço HTTPS. IA somente se houver serviço previamente validado e autorizado; nesta etapa não houve teste real de nuvem.
