# Refinamento da experiência de IA

Branch: `integracao-bibi`. Data: 18/10/2026. Esta etapa refina a integração anterior; não adiciona provedores, modelos locais ou outro aplicativo.

## Experiência final

O chat usa Nunito, as cores e superfícies do tema da biblioteca, o gatinho existente, cartões de convite e mensagens com identificação visual de estudante/BIBI. A composição mantém o campo de escrita junto de Enviar e Parar resposta; Nova conversa fica no cabeçalho e é desabilitada durante uma resposta. Enter envia, Shift+Enter cria uma linha. Há carregamento discreto, respeito a movimento reduzido, histórico com rolagem e texto progressivo sem raciocínio interno. Cancelamentos sem texto não deixam um balão vazio.

Quando um livro é selecionado, seus detalhes continuam antes do chat e os convites passam a tratar daquela obra. Fechar o livro, redimensionar as colunas, navegar e usar claro/escuro mantêm os comportamentos do aplicativo.

Sem IA pronta e ativa, o HTML do chat começa oculto e a quinta prateleira nem é criada. O Dashboard não monta um painel de IA indisponível. Os indicadores normais, quatro prateleiras, avaliações e detalhes do livro continuam disponíveis. Os endpoints também exigem disponibilidade: ocultar a interface não substitui autorização no servidor.

## Preparar, testar e ativar

Na seção Inteligência Artificial, as cinco etapas ficam na mesma página:

1. Escolher OpenAI, Anthropic/Claude, Gemini, xAI/Grok, GroqCloud ou OpenRouter.
2. Inserir a chave e usar **Salvar chave**. Confirmar a senha uma vez, com validade de dez minutos nesta sessão para operações sensíveis.
3. Usar **Consultar modelos** e escolher uma opção. A seleção é salva na preparação sem disponibilizar a IA aos estudantes.
4. Usar **Testar conexão**, com aviso de que a mensagem técnica pode consumir créditos. Não há teste pago implícito ao preencher campos.
5. Confirmar a revisão da escola sobre as condições de uso e privacidade, ligar o switch e **Confirmar configuração**.

Limites e métricas ficam em **Uso e opções avançadas**. A área principal informa estado, provedor, modelo e existência da chave, sem exibi-la. Erros são apresentados junto da operação e a seção não mostra JSON ou cabeçalhos internos.

A configuração em preparação é armazenada separadamente da integração em uso. Consultar, trocar modelo ou testar outra chave não substitui o serviço dos estudantes. Só a confirmação final aplica uma preparação validada. **Descartar alterações em preparação** volta à seleção em uso. Desligar o switch é imediato e não pede senha novamente.

## Disponibilidade e segurança

O backend mantém estados de integração não configurada, desativada, verificando, pronta e indisponível. A disponibilidade depende de ativação e de uma prova persistida de geração bem-sucedida vinculada ao provedor, modelo e credencial exatos. Uma chave salva sozinha não comprova conexão. Falhas conhecidas invalidam a prova correspondente; o responsável precisa testar novamente.

Instalações da versão anterior que estavam ativadas sem prova persistente passam a exigir teste e ativação explícitos. Chaves e acervo são preservados. Não há nova migração de schema: preparação e provas ficam em Configuracoes, e credenciais continuam no armazenamento DPAPI. Restaurar backup limpa preparação, provas e credenciais de IA.

Listar modelos e testar são operações preparatórias permitidas **apenas ao bibliotecário**, mesmo com a IA globalmente desligada. Continuam protegidas por sessão, CSRF, limites e concorrência. Geração estudantil, recomendações expostas pelo recurso e insights exigem disponibilidade efetiva. Não há chamadas gratuitas presumidas nem fallback pago automático.

A confirmação institucional é registrada na auditoria, com ator e provedor. Trocar o provedor exige nova confirmação das condições institucionais. Ela não equivale a certificação jurídica. A prova de conexão representa o último resultado conhecido: não garante saldo, disponibilidade futura ou condições de privacidade do plano.

A tela que altera a configuração atualiza os recursos ao concluir a operação. Outras sessões abertas consultam o estado local em intervalos de até cinco segundos e ao receber foco. As consultas não chamam provedores e não se acumulam durante uma consulta pendente. O bloqueio de novas gerações no backend é imediato; uma chamada já recebida pelo serviço externo pode continuar sendo processada.

## Metadados no lugar certo

Autoria, país e fonte consultada foram movidos para **Sobre a autoria · opcional**, no cadastro manual e na edição das obras. Não aparecem mais na configuração de IA. A validação é compartilhada entre o cadastro e a API administrativa existente, e os campos são salvos na mesma transação do livro. Clientes que não enviam os campos preservam os valores existentes.

A classificação continua opcional e não é deduzida pelo nome. Informar país ou gênero requer uma fonte. O algoritmo de recomendações, o cache e a prioridade a autoras brasileiras permanecem, com testes de desempate e preferências.

## Arquivos principais

- `app.py`: transição segura de configurações antigas sem prova de conexão.
- `services/ai/settings.py`, `services/ai/runtime.py`, `routes/ia.py`: preparação, confirmação recente, validação e disponibilidade compartilhada.
- `services/autoria_service.py`, `services/livros_service.py`, `services/dados_service.py`: autoria e preservação na restauração.
- `templates/ia_chat.html`, `templates/ia_settings.html`, `templates/autoria_fields.html`: componentes na interface existente.
- `static/js/ia.js`, `static/js/ia_config.js`, `static/js/livros.js`, `static/css/ia.css`: composição visual, interação e atualização sem reiniciar.
- `tests/test_ia.py`, `tests/test_regression.py`, `tests/browser_check.py`, `tests/browser_ia.py`, `tests/browser_ia_refino.py`: cenários atualizados e ampliados.
- `README.md`, `docs/INTEGRACAO_IA.md`, `docs/ROTEIRO_DEMONSTRACAO.md`: instruções alinhadas ao novo fluxo.

## Validação

```powershell
python -m unittest discover -s tests -p "test_*.py"
python tests/browser_check.py
python tests/browser_ia.py
python tests/browser_ia.py --loading-only
```

| Verificação executada | Resultado |
|---|---|
| Suíte unittest completa | **83 aprovados**, sem falhas, 283,059 s |
| Regressão geral Chromium | **Aprovada**: instalação, convite, perfis, acervo com quatro prateleiras sem IA, temas, detalhes e redimensionamento |
| Fluxo Chromium de IA | **Aprovado**: preparação desativada, modelos, teste, ativação, conversa, cancelamento, troca preservada, falha, reteste, desligamento e edição de autoria |
| Chromium com resposta de estado retida | **Aprovado**: nenhum flash de chat, quinta prateleira ou insights antes da disponibilidade |
| Preparação/ativação após ajuste de revisão por provedor | **2 testes focados aprovados**, 17,186 s |

A validação usa bancos temporários, contas sintéticas e provedores simulados, sem consumo de créditos. O teste de carregamento retém a resposta do endpoint de estado para comprovar que o chat e a quinta prateleira não aparecem antes de conhecer a disponibilidade. O teste visual verifica ausência de sobreposição entre Enviar, Parar e Nova conversa, nos temas claro/escuro e larguras 1366, 800 e 390 px. A regressão ampla ainda cobre 1920 px e redimensionamento das colunas.

Logs, resumo verificável e capturas estão em [validacao/refino-ia](validacao/refino-ia/resultados.json). Capturas: [conversa contextual](validacao/refino-ia/conversa-contextual.png), [tema escuro no celular](validacao/refino-ia/chat-390-True.png) e [configuração antes de ativar](validacao/refino-ia/configurada-desativada.png). Os livros e respostas mostrados são dados de teste, sem validar nuvem real.

A primeira suíte ampliada teve 82 testes, com uma falha na expectativa antiga de disponibilidade do endpoint de insights; essa expectativa foi corrigida e a execução final acima passou. Passagens exploratórias de Playwright também revelaram a reabilitação prematura do botão Testar e um nome acessível que incluía o ícone decorativo. Ambos foram corrigidos antes da passagem final. Logs de exceções deliberadas e rejeição TLS de certificado desconhecido pertencem aos testes negativos da suíte e não representam falha de asserção.

Foram encontradas e corrigidas corridas no encadeamento de consulta/escolha/teste: controles passam a permanecer desabilitados até terminar a operação, e uma seleção não é perdida por um clique antecipado. Uma expectativa antiga de regressão exigia sucesso do endpoint de insights numa instalação sem IA; agora exige indisponibilidade, preservando a verificação de autenticação. O ícone decorativo dos convites também recebeu nome acessível explícito para não alterar a pergunta lida pelo leitor de tela.

## Limitações

- Não foram feitos testes reais contra os provedores nem consumidos créditos. A validação de nuvem depende da chave e do plano da instituição.
- A atualização em outros navegadores abertos pode levar até cinco segundos; o servidor bloqueia imediatamente o uso desativado.
- Um teste antigo bem-sucedido é evidência do último contato, não monitoramento contínuo. Não há sondagem de geração paga automática.
- A distribuição continua Windows/DPAPI. Não foram reconstruídos instalador e executável, nem repetido o ensaio em outro dispositivo físico. Servidor HTTPS e bandeja não foram redesenhados.
