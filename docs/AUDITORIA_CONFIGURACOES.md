# Auditoria das configurações e da agenda

Auditoria realizada em 19/10/2026 na branch `integracao-bibi`. Os testes usam banco descartável, contas sintéticas e Chromium. Nenhum banco da instalação foi substituído; não houve envio real de e-mail nem consumo de IA.

## Problemas corrigidos

- **Telefone:** o switch agora controla o cadastro e a edição de estudantes, além do empréstimo rápido. Quando desligado, os dois formulários ocultam o campo e não exigem preenchimento. Telefones existentes são preservados ao editar um cadastro com o campo oculto. Quando ligado, o backend valida o telefone também em empréstimos de leitores existentes e salva o contato informado.
- **Localização:** a exigência passa a valer também na edição de livros. Desligá-la deixa a localização disponível como campo opcional, em vez de impedir seu preenchimento.
- **Importação CSV:** prévia e confirmação respeitam as exigências de telefone e localização. A confirmação refaz a validação; não basta enviar diretamente uma importação sem os campos exigidos.
- **Prazo:** o empréstimo rápido usa o prazo estudantil configurado, inclusive valores fora de 7/14/21/28 dias. O prazo pode ser ajustado explicitamente pelo bibliotecário. O texto para professores acompanha a regra efetiva, em vez de sempre anunciar devolução no mesmo dia.
- **Atualização da tela:** ao fechar as configurações, a aplicação consulta novamente os campos salvos e atualiza formulários, agenda e botão de exclusão do livro já selecionado. A quantidade de aulas é carregada antes da primeira renderização da agenda.
- **Persistência concorrente:** alterar um switch envia apenas aquela opção. O backend mescla a alteração em transação, preservando as demais opções, inclusive alterações feitas por outra sessão.
- **Cache antigo:** as opções globais e seus padrões vêm do servidor. Um cache de outra configuração no navegador não prevalece quando uma chave ainda não existe no banco, por exemplo após restaurar uma instalação antiga.
- **E-mail bloqueado:** o bloqueio alcança o transporte comum usado por convites, verificação, recuperação e fila. O teste de remetente explica o bloqueio, em vez de sugerir uma senha incorreta.
- **Agenda:** divisão vertical entre Aula e Agendamento nos dois temas; a coluna Aula ocupa 25% quando presente. O backend rejeita horários fora da quantidade configurada. Reduzir a quantidade não pode ocultar compromissos futuros; horários históricos continuam visíveis ao consultar a data.
- **Informações institucionais:** salvar termos e privacidade atualiza também os textos da seção institucional já aberta, sem exigir recarga.
- **Carregamento das configurações:** o conteúdo fica `inert` e marcado como ocupado até todos os formulários estarem inicializados. Isso evita submissões HTML antes de os handlers com CSRF estarem prontos. Uma falha de carregamento limpa o conteúdo parcial, permitindo tentar novamente.

O ajuste anterior do resumo do Dashboard foi preservado: classe própria, sem herdar largura e espaços das mensagens do chat.

## Mapa das opções revisadas

| Opção | Efeito e verificação |
| --- | --- |
| Descrição, temas, ano, categoria | Exibição no cadastro/edição. Chromium verifica campos ocultos no cadastro e visíveis na edição após reativar. Não apagam metadados existentes. |
| Telefone de estudantes | Visibilidade no cadastro e empréstimo, validação no backend e CSV, preservação do contato oculto. Chromium e unittest. |
| Ocultar exclusão de livros | Atualiza o botão do livro selecionado. Chromium. É uma opção de exibição, conforme seu rótulo; não cria uma nova regra de autorização. |
| Exigir localização | Obrigatoriedade no cadastro, edição e CSV; campo opcional continua disponível. Chromium e unittest. |
| Mostrar coluna Aula | Remove/restaura a coluna sem mudar os horários. Chromium. |
| Quantidade de aulas | Quantidade renderizada, persistência e validação dos horários; proteção de compromissos futuros. Chromium e unittest. |
| Bloquear exclusão de agendamento | Backend impede a exclusão; o painel consulta a configuração para ocultar o botão. Ativação/desativação exercitadas por unittest. |
| Confirmar senha ao agendar | Mudança exige identidade; criação exige senha real somente quando habilitada. Unittest. |
| Confirmar senha ao emprestar | Conferência da senha no backend preservada; regressão automatizada existente. |
| Máximo de exemplares | Limite efetivo por categoria; unittest registra empréstimos e testa rejeição ao exceder. |
| Prazo por categoria | Vencimento real e padrão do formulário; unittest e Chromium. Não reescreve vencimentos existentes. |
| Limite de renovações | Backend aceita até o limite e rejeita a próxima; unittest. |
| Bloquear por atraso | Backend bloqueia novo empréstimo e permite após desabilitar a regra; unittest. |
| Retirada de reservas | Regra de reservas e expiração preservada; testes existentes na suíte geral. |
| Bloquear e-mail | Transporte comum não inicia SMTP; unittest. |
| SMTP, conta, tema, IA, backups | Fluxos e proteções existentes revisados e cobertos pelas regressões pertinentes. Não foi feito teste real de SMTP ou provedor de IA nesta auditoria. |
| Termos e privacidade | Atualização imediata da seção e persistência da página pública; cenário Chromium separado. |

## Comandos e resultados

Resultado final: **92 testes aprovados em 299,995 s; processo Python e comando com saída 0**. [Log completo](validacao/configuracoes/unittest-final.txt). Os erros simulados de gravação/restauração e a rejeição de certificado não confiável no log pertencem aos testes de falha previstos; não são falhas da suíte.

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m unittest tests.test_settings_effects -v
python tests/browser_settings.py
python tests/browser_settings.py --institution-only
python tests/browser_settings.py --cache-only
node --check static/js/configuracoes.js
node --check static/js/app.js
node --check static/js/emprestimos.js
node --check static/js/leitores.js
node --check static/js/livros.js
node --check static/js/preferencias.js
node --check static/js/gestao.js
node --check static/js/agenda.js
node --check static/js/ui.js
node --check static/js/settings_modal.js
git diff --check
```

- Primeira execução geral: **89 testes, OK**, 399,450 s. A execução foi iniciada antes dos três cenários adicionais da auditoria; o wrapper PowerShell retornou 1 apesar do resumo OK. A execução final captura o código diretamente do subprocesso Python para não depender do tratamento de stderr pelo shell.
- Suíte específica final: **9 testes, OK**, 28,138 s. Não somar execuções repetidas como testes distintos.
- Chromium principal: **PASS**, saída 0. Telefone, campos de livros, localização, ocultação da exclusão, regras salvas pelo painel, prazos, quantidade persistida, coluna Aula e divisória em 1366/800/390 px, nos temas claro e escuro. Sem erros de JavaScript.
- Chromium institucional: **PASS**, saída 0. Conteúdo bloqueado para interação durante a resposta preparatória retida; após o carregamento, salvamento dos textos, atualização imediata e persistência na página pública. Sem erros de JavaScript.
- Chromium de cache antigo: **PASS**, saída 0. Valores antigos conflitantes no `localStorage` não substituem os padrões do servidor; telefone oculto e coluna Aula presente, com os mesmos estados no painel de configurações.
- Checagens de sintaxe JavaScript, compilação Python dos arquivos alterados e `git diff --check`: aprovadas. O Git apenas informa conversão futura de LF para CRLF em um arquivo já existente.
- Execuções exploratórias: o primeiro teste de switches usou clique forçado no input visualmente oculto; foi substituído por teclado no controle real. Uma execução posterior aguardou resposta sem a mudança esperada. A execução aprovada confirma também o estado final do controle. O cenário institucional revelou a submissão prematura com erro de CSRF; o carregamento foi corrigido e ganhou verificação própria com resposta preparatória retida.

Capturas preservadas: [agenda clara](validacao/configuracoes/agenda-claro.png) e [agenda escura em celular](validacao/configuracoes/agenda-escuro-mobile.png). As seis capturas originais ficam em `%TEMP%/bibi-settings-audit/`. A validação usa o servidor HTTP de teste local; não comprova acesso HTTPS por outro dispositivo, SMTP real, integração real em nuvem ou novo empacotamento.

As mudanças de exibição são aplicadas ao fechar Configurações nesta página e ao carregar novamente a aplicação. Não foi criado um serviço de sincronização instantânea entre dispositivos. As regras de backend são verificadas nas operações, independentemente da tela aberta.
