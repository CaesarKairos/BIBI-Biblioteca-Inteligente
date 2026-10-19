# Serviços conectados, roteamento e Configurações

Entrega na branch `integracao-bibi`, em 19/10/2026. Este documento descreve a interface atual; `REFINO_IA.md` registra a etapa anterior de configuração única.

## Uso pelo bibliotecário

Em **Configurações → Inteligência Artificial**, use **Adicionar serviço**, identifique a plataforma da chave e salve. A plataforma identifica a autenticação; não escolhe o fornecedor de todas as conversas. OpenAI, Anthropic, Gemini, xAI/Grok, GroqCloud e OpenRouter são cadastros distintos e podem coexistir.

O cadastro permite autorizar modelos pagos/preços desconhecidos e registrar a revisão institucional de privacidade. Sem autorização de custos, somente preço zero informado é elegível, ressalvada a autorização restrita migrada de um modelo anterior já ativo. Isso não promete acesso gratuito ilimitado nem condições de privacidade de um plano pago.

Salvar consulta a lista de modelos, sem geração. **Verificar serviço** envia uma mensagem técnica, pode consumir créditos e é uma ação explícita. Um teste anterior bem-sucedido não garante disponibilidade futura. Depois de verificar ao menos um serviço autorizado, ligue o switch geral. Não é preciso selecionar um modelo.

Alterar uma chave cria uma credencial pendente protegida. A chave anterior permanece em uso até a nova passar na verificação. Uma falha na substituição não derruba o serviço anterior. **Remover** apaga apenas as credenciais do serviço escolhido; **Desativar** mantém sua chave, mas o exclui das novas seleções.

A senha aparece em diálogo somente para salvar/remover credenciais, autorizar custos ou ativar globalmente quando falta confirmação recente. O mesmo clique continua depois da senha. A confirmação pertence à conta e à sessão e expira em dez minutos. Desativar e alterar limites simples não exige senha. A API continua verificando permissões e CSRF.

## Critérios de seleção

Não há IA adicional para decidir a rota. A seleção é determinística em `services/ai/routing.py`.

| Ordem | Critério |
| --- | --- |
| Elegibilidade | Serviço habilitado, credencial correspondente à verificada, revisão institucional e ao menos um teste de geração bem-sucedido no serviço. |
| Compatibilidade | Modelo efetivamente listado pela API e compatível com texto/streaming no transporte. Usa metadados oficiais ou catálogo documentado; prova anterior de geração é preservada. Modelos desconhecidos sem evidência não são declarados compatíveis. |
| Tarefa e limites | Tarefa permitida, contexto/saída suficientes quando conhecidos, cota global por conta/hora e instalação/24h, concorrência, cota de tentativas automáticas por serviço e pausas por falha. |
| Custos | Permissão individual do serviço; estimativa calculada somente quando existem preços suficientes. Teto numérico exclui preços desconhecidos. |
| Preferência opcional | Um modelo preferencial por tarefa só participa se continuar elegível; não contorna autorização nem limites. |
| Português | Avaliação categórica opcional registrada pela escola: não avaliado, adequado ou não utilizar. Não se inventa benchmark nem se deduz qualidade pelo nome. Atualizar o catálogo não apaga essa avaliação. |
| Histórico | Menos falhas consecutivas antes dos critérios seguintes. Sucesso limpa o contador; falha pausa o modelo. Erros de chave/permissão invalidam a prova do serviço. |
| Conversas | Entre os restantes, prioriza o último tempo real observado até o primeiro token; depois, custo estimado. Na preferência de economia, inverte essa ordem. |
| Insights | Prioriza custo estimado e depois latência observada, pois não exige a mesma interatividade do chat. |
| Empate | Identificadores de serviço/modelo, com ordem estável. Não implica superioridade do modelo. |

Latência desconhecida permanece desconhecida. Não há chamadas de exploração para fabricar medidas. A estimativa de entrada usa caracteres/3, mais a saída máxima configurada; não é tokenização exata, garantia de contexto ou fatura. Informações de custo podem faltar, especialmente em APIs de listagem que retornam somente identificadores. O custo efetivo só é registrado quando o transporte reconhece a informação fornecida, atualmente `usage.cost` em USD no OpenRouter. Ausência de custo informado não equivale a zero.

O primeiro teste valida um candidato escolhido automaticamente. Outros modelos documentadamente compatíveis do mesmo serviço podem ser selecionados depois, com estados separados de listado/verificado/indisponível. Uma lista de modelos não prova que todos geram com aquela chave. A revisão opcional de português também não é inferida do teste técnico de conexão.

As recomendações de livros continuam em `recommendations.py`, usando somente o catálogo e dados autorizados, com preferência determinística por autoras brasileiras. Não há geração externa para escolher os livros da quinta prateleira.

## Fallback e consumo

Há no máximo **duas tentativas externas por solicitação**. O transporte marca como seguras para fallback apenas rejeições HTTP explícitas 401/403/404/429, antes de qualquer texto entregue. A alternativa precisa ser compatível, habilitada e autorizada. Um modelo pago ou de preço desconhecido não entra por ser uma alternativa conveniente.

Timeout, queda de rede, erro genérico do provedor e resposta parcial não autorizam reenvio: podem ter ocorrido depois de o fornecedor aceitar e cobrar a geração. Não existe promessa de reembolso ou cancelamento instantâneo no fornecedor. Cancelar/limpar conversa e desativar o serviço interrompem a entrega local; nenhuma alternativa é iniciada depois de uma resposta parcial.

Uma resposta já autorizada pode terminar quando consome a última tentativa diária permitida; isso bloqueia a próxima chamada, sem interromper a própria última resposta. Revogações são conferidas durante o streaming. A cache de autorização é invalidada a cada alteração do registro para evitar reler centenas de metadados a cada fragmento.

O limite individual conta tentativas automáticas, inclusive fallback. Testes administrativos e consultas de catálogo continuam sujeitos ao limite geral, à concorrência e a limites de frequência próprios. Os cabeçalhos de limite retornados pelo serviço são retidos; não se presume conhecer toda a cota contratual. Uma rejeição por limite aplica pausa de cinco minutos; outras falhas de modelo aplicam pausa de um minuto. Não há sondagem paga automática durante essa pausa.

O cache de insights dura até uma hora. Sua assinatura considera fatos e configuração relevante; atualizar latência ou saúde não dispara outra análise paga. Mudanças de autorização/serviço/política invalidam o cache correspondente.

## Migração e segurança

- `005_roteamento_ia.sql` acrescenta `IATentativas`, sem apagar tabelas. A infraestrutura existente cria backup antes de migrações.
- A migração idempotente cria `Configuracoes.ia_servicos_v1`. Preserva as chaves ativas, rascunhos e chaves de outros serviços conhecidos que não estavam selecionados. Não lê `.env` nem exige arquivos novos de credenciais.
- Uma configuração anterior ativa, verificada e com revisão institucional conserva autorização **somente para seu modelo anterior**, inclusive se o preço não era informado. Isso não libera modelos novos pagos. Salvar explicitamente a permissão de custos desmarcada revoga essa autorização anterior.
- Serviços anteriores sem prova válida ficam pendentes de verificação. Um serviço anterior não reconhecido mantém suas credenciais originais, desativa globalmente a IA e recebe orientação de recadastro.
- Chaves continuam no armazenamento protegido existente. JSON administrativo nunca inclui chaves, hashes de credencial ou senhas. A chave pode existir no navegador enquanto é digitada, mas não é reexibida após salva.
- A restauração de backup mantém a política anterior de limpar credenciais e desativar IA; agora inclui as novas chaves pendentes e o registro de roteamento. Isso é distinto da migração de versão, que as preserva.
- `IAUtilizacao` identifica o provedor/modelo final. `IATentativas` registra cada tentativa, tarefa, motivo da escolha, estado, tempo, tokens e custos disponíveis, sem armazenar perguntas, respostas ou catálogo enviado. Os registros vinculados são limpos junto do uso após 90 dias.
- Estudantes não podem cadastrar serviços nem escolher provedores/modelos na requisição. Conversas continuam isoladas por conta e sessão.

Sem serviço elegível e ativação global, chat, quinta prateleira e insights de IA permanecem ocultos desde o carregamento. Indicadores locais, catálogo, circulação, comentários e detalhes dos livros permanecem disponíveis. Outras páginas abertas atualizam a visibilidade em até cinco segundos; o backend verifica autorização nas novas solicitações.

## Interface compartilhada

As 13 áreas de Configurações usam os mesmos estilos de campos, títulos, espaçamentos, botões, switches, divisórias e mensagens em `contas.css`. Foram removidos os estilos exclusivos de etapas, os círculos numerados e o expansível de identidade da IA. Textos técnicos ficam em detalhes/opções avançadas. A navegação lateral de desktop e a faixa navegável no celular foram preservadas.

As capturas e a verificação real de Chromium incluem Minha conta, Aparência, Biblioteca, Acervo e agenda, Circulação, Contas e acesso, IA, E-mail, Dados, Moderação, Sistema e segurança, Informações institucionais e Sobre.

## Arquivos

Novos: `database/migrations/005_roteamento_ia.sql`; `services/ai/connections.py`, `model_catalog.py`, `routing.py`; `tests/test_ai_routing.py`, `browser_ai_routing.py`; este relatório e evidências.

Adaptados: `app.py`; `routes/ia.py`; `services/ai/providers.py`, `runtime.py`, `settings.py`; `services/dados_service.py`; `static/css/contas.css`, `ia.css`; `static/js/ia_config.js`; `templates/configuracoes.html`, `ia_settings.html`; `tests/browser_ia.py`, `browser_ia_refino.py`; README, documentação de integração e roteiro.

## Verificações

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m unittest tests.test_ai_routing -q
python tests/browser_ia.py
python tests/browser_ia.py --loading-only
node --check static/js/ia_config.js
python -m compileall -q services/ai routes/ia.py app.py
git diff --check
```

Resultados já concluídos:

- Suíte geral final: **105 testes, OK**, 356,472 s, saída 0. [Log integral](validacao/roteamento-ia/unittest-geral.txt). As falhas de gravação/restauração simuladas e a rejeição de certificados no log são cenários previstos, não reprovações.
- Módulo final de roteamento: **15 testes, OK**, 72,654 s, saída 0. Os dois cenários acrescentados após o discovery geral verificam revogação durante o streaming e preservação do cache de insights. São 107 cenários distintos cobertos pelas duas execuções; não foi executado outro discovery completo de 107 testes.
- Suíte geral intermediária: **102 testes, OK**, 431,354 s, saída 0.
- Roteamento com revisão de catálogo e migração: **13 testes, OK**, 86,877 s. Uma execução anterior detectou variável local sombreando a credencial na atualização dos metadados; foi corrigida e repetida com sucesso.
- Roteamento com revogação em streaming: **14 testes, OK**, 90,038 s.
- Chromium principal: **PASS**, saída 0. Um e dois serviços, diálogo de senha que conclui o salvamento, confirmação recente reutilizada, ativação, recomendações com autora brasileira em primeiro, sugestão contextual, streaming, cancelamento, nova conversa, isolamento de contas, troca de chave pendente/verificada, remoção e desativação global com catálogo preservado.
- Configurações: **13 seções × 3 larguras (1366/800/390) × 2 temas**, verificadas no navegador, com 52 capturas em desktop/celular e sem transbordamento horizontal dos campos/painéis. Capturas inspecionadas também levaram à correção do alinhamento de ajuda dos checkboxes no celular.
- Carregamento retido: **PASS**, saída 0; ausência do chat e da quinta prateleira antes e depois da resposta de instalação não configurada.
- Sintaxe JavaScript, compilação Python e `git diff --check`: aprovados. Avisos de LF/CRLF do Git não representam falha de conteúdo.

[Resumo estruturado](validacao/roteamento-ia/resultados.json). Foram preservadas 26 capturas: todas as seções no desktop claro e no celular escuro. Exemplos: [IA no desktop](validacao/roteamento-ia/inteligencia-artificial-1366-False.png), [IA no celular](validacao/roteamento-ia/inteligencia-artificial-390-True.png), [Minha conta](validacao/roteamento-ia/minha-conta-1366-False.png), [Circulação no celular](validacao/roteamento-ia/circulacao-390-True.png) e [E-mail](validacao/roteamento-ia/email-1366-False.png). As 52 capturas originais ficam em `%TEMP%/bibi-auto-routing/`.

Execuções exploratórias não são contabilizadas como aprovadas: o teste da última tentativa diária revelou uma checagem de disponibilidade que interrompia a própria resposta; houve também um mock de iterator sem fechamento de gerador. A checagem foi corrigida e o mock passou a respeitar o contrato real de streaming. As falhas seguintes da revisão de catálogo foram corrigidas antes da execução específica aprovada.

Todos os dados e provedores dos testes são sintéticos, com bancos temporários e rede externa bloqueada. Não houve conectividade real com os seis serviços, consumo de créditos ou validação contratual de plano escolar. Não se comprovou nesta etapa acesso de outro dispositivo físico nem se reconstruiu o instalador.

## Fontes e limites do catálogo

Compatibilidade não é ranking de qualidade. As fontes oficiais consultadas foram [OpenAI — GPT‑4.1 mini e endpoints](https://developers.openai.com/api/docs/models/gpt-4.1-mini), [Claude — listagem e ciclo de vida](https://platform.claude.com/docs/en/api/models/list), [Gemini — modelos e capacidades](https://ai.google.dev/gemini-api/docs/models), [xAI — modelos](https://docs.x.ai/developers/models), [Groq — modelos de produção](https://console.groq.com/docs/models) e [OpenRouter — arquitetura, parâmetros e preços](https://openrouter.ai/docs/api/api-reference/models/get-models).

O catálogo é conservador: onde a API não informa compatibilidade suficiente, há uma lista explícita de identificadores documentados ou prova anterior de geração. Não se adivinha capacidade pelo nome. Um modelo novo pode permanecer sem compatibilidade confirmada até atualização do catálogo; ele não é enviado às cegas ao endpoint. Catálogos/preços são atualizados ao salvar/consultar/verificar o serviço, sem monitoramento pago em segundo plano. Não há benchmark automático de português nem garantia de que o menor tempo observado continue sendo o menor no futuro.
