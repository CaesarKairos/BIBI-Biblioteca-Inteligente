# Relatório verificável — integração de IA

Data: 18/10/2026. Branch de trabalho: `integracao-bibi`. Base local: `d76bdd71e62aa8ea88a69354805d7b657e92695d`. Referência do agente: `be010a39d73398a59b32664129ad106251f8399c`.

## Entrega

- Chat literário dentro do painel lateral existente, com perguntas gerais ou relacionadas ao livro selecionado, escrita livre, continuidade por conta/sessão, resposta progressiva, estados de espera, interrupção e expiração.
- Prompt BIBI adaptado e política pedagógica do agente original reaproveitada. Sem banco, UI antiga, Ollama ou modelo local.
- Transportes REST para OpenAI, Anthropic, Google Gemini, xAI/Grok, GroqCloud e OpenRouter. Modelos consultados no provedor, sem identificador de produção inventado ou fixado.
- Configuração administrativa direta com chave protegida por DPAPI, confirmação de senha, troca/remoção, seleção de modelo, teste real acionado pelo responsável, limites, métricas informadas e desligamento.
- Quinta prateleira com seleção local real e personalizada, justificativa no título acessível da capa e prioridade explícita de autoras brasileiras documentadas. Preservação das outras quatro prateleiras.
- Metadados opcionais de autoria com fonte, migração compatível e cache invalidado pela assinatura dos dados relevantes.
- Insights administrativos sobre totais, circulação mensal, títulos, categorias e reservas agregados; resumo local preservado quando IA está desligada ou falha.
- Avaliações existentes reaproveitadas, com edição/publicação preservadas, exclusão acrescentada ao painel do livro e moderação local independente da IA.
- Restauração apaga credenciais de IA e desativa a integração. Chamadas externas liberam o bloqueio operacional; uma barreira compartilhada permite geração concorrente e impede restauração durante essas operações.
- README, documentação técnica, teste opcional de nuvem e roteiro de demonstração.

O armazenamento de segredos em repouso para IA está habilitado apenas no Windows/DPAPI. Não foi implementado armazenamento equivalente para outras plataformas. Não foi alterado nem substituído um banco real da escola: execuções de teste usam diretórios temporários.

## Arquivos alterados e criados

| Grupo | Arquivos |
|---|---|
| Documentação | `README.md`, `docs/INTEGRACAO_IA.md`, `docs/RELATORIO_IA.md`, `docs/ROTEIRO_DEMONSTRACAO.md`, `docs/validacao/` (resultados JSON e logs sanitizados) |
| Banco | `database/database.py`, `database/migrations/004_ia.sql` |
| Backend HTTP | `routes/__init__.py`, `routes/ia.py` |
| Serviços | `services/ai/__init__.py`, `services/ai/policy.py`, `services/ai/prompts.py`, `services/ai/providers.py`, `services/ai/recommendations.py`, `services/ai/runtime.py`, `services/dados_service.py` |
| Segurança | `utils/auth.py`, `utils/secrets_store.py` |
| Interface | `templates/app.html`, `templates/configuracoes.html`, `templates/shell.html`, `static/js/ia.js`, `static/css/ia.css`, `static/js/livros.js`, `static/js/conta_acervo.js`, `static/js/settings_modal.js` |
| Testes | `tests/test_ia.py`, `tests/browser_ia.py`, `tests/check_ia_online.py`, `tests/browser_check.py` |
| Distribuição | `requirements-dev.txt`, `packaging/BIBI.spec` |

Já havia uma edição de licença no README no início da sessão; ela foi preservada. Não houve commit, push ou publicação automática.

## Configuração e priorização

O procedimento completo e as fontes oficiais estão em [INTEGRACAO_IA.md](INTEGRACAO_IA.md). Bibliotecário: abra Configurações → Inteligência Artificial, revise as condições institucionais e do plano, insira chave, confirme senha e salve a ativação. Consulte modelos, selecione um, confirme senha e salve. Teste conexão/geração com consciência do possível consumo. O botão Desativar imediatamente impede novas chamadas sem afetar os módulos convencionais.

Não se confunde modelo listado com geração comprovada, nem tokens reportados com custo cobrado. Nenhum provedor alternativo pago é escolhido automaticamente. OpenRouter recebe instrução de não fazer fallback e de negar rotas com coleta de dados; isso pode reduzir os modelos utilizáveis.

A ordem de recomendação é verificável no backend: compatibilidade com filtros, sinais positivos/negativos de interesse, afinidade temática, prioridade de autoria feminina brasileira documentada, depois feminina ou brasileira documentada, disponibilidade, novidade e diversidade dentro do mesmo patamar. Não infere identidade pelo nome. Sem histórico, a afinidade fica neutra e a prioridade documentada e a diversidade orientam a descoberta. Preferências explícitas estruturadas são filtradas antes do ranking; reconhecimento de linguagem natural é limitado e documentado.

## Validação e resultados

Comandos executados com Python 3.11, Windows, SQLite temporário e Chromium/Playwright:

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m unittest tests.test_ia -v
python tests/browser_check.py
python -u tests/browser_ia.py
python -m compileall -q routes/ia.py services/ai tests/test_ia.py tests/browser_ia.py tests/check_ia_online.py
git diff --check
```

| Verificação | Resultado real |
|---|---|
| `unittest discover` final | **78 testes aprovados**, 287,403 s, sem falhas de asserção |
| Suíte específica de IA | **15 testes aprovados**, incluindo concorrência real em threads e os contratos dos seis provedores |
| Contratos após ajuste do corpo Responses da xAI | **3 testes aprovados**, 0,133 s; xAI usa mensagem `system` no `input`, conforme exemplo oficial |
| `tests/browser_check.py` | **Aprovado**, Chromium, primeira instalação/convite real e regressão de interface |
| `tests/browser_ia.py` ampliado | **Aprovado**, Chromium, Dashboard, conversa, edição/moderação/notificação e desligamento; nuvem simulada |
| Compilação Python e `git diff --check` | Aprovados; Git apenas informa conversão futura de LF para CRLF em arquivos Windows |
| Nuvem real, outro dispositivo, executável reconstruído | **Não executados** |

As execuções exploratórias anteriores não substituem esses resultados. Consulte o [registro de resultados com hashes dos arquivos](validacao/resultados.json), o [log da suíte](validacao/unittest-78.txt), o [log específico de IA](validacao/ia-15.txt), a [regressão Chromium](validacao/browser-regressao.txt) e o [fluxo Chromium de IA](validacao/browser-ia.txt). As capturas da regressão ampla ficam em `%TEMP%/bibi-contas-review`. Os registros negativos esperados também foram preservados para auditoria.

As suites de IA não consomem créditos: transportes externos são substituídos por mocks e o teste de navegador de IA bloqueia rede externa. O teste amplo de navegador também bloqueia destinos externos no Chromium e SMTP real. Não usa contas ou acervo da escola.

Cobertura de serviço/HTTP: instalação, contas, convites, CSRF/origem, autorização, favoritos, Quero ler, reservas e estoque, empréstimos/devoluções/renovações, avaliações/moderação, notificações, recuperação, SMTP simulado, importação/exportação, backup/restauração, configuração de IA, chaves, listagem de modelo, teste de geração simulado, prioridade documentada, filtros, dados reais agregados, cache, expiração e isolamento. Contratos dos seis provedores verificam autenticação, formatos, streaming e erros 401/403/404/429/500, timeout de rede, ausência de retries e descarte de raciocínio.

O teste de concorrência executa duas gerações bloqueadas em threads distintas, acessa o catálogo, recusa uma terceira geração e desativa a IA antes de liberar as duas respostas. O histórico incompleto não é promovido a conversa concluída.

### Falhas encontradas durante o trabalho

- Consulta inicial de recomendações concatenava uma cláusula `FROM` incorretamente. Corrigida e coberta por testes de catálogo e personalização.
- Evento malformado de streaming podia gerar `AttributeError`. Agora vira erro sanitizado, sem expor a resposta bruta.
- Carregamento das Configurações podia sobrescrever a seção escolhida durante a inicialização. A seção atual passa a ser preservada; a configuração de IA inicializa junto ao fragmento.
- A regressão de navegador esperava painel vazio também ao abrir `/configuracoes`, que redireciona ao acervo. A expectativa foi atualizada para exigir chat nessa tela e continuar exigindo painel vazio no Perfil.
- A primeira passagem ampliada de moderação consultava o painel antes de terminar sua carga assíncrona. O teste passou a aguardar a conclusão de salvamento/carga; as Configurações também ocultam os demais painéis imediatamente, evitando exibir todas as seções durante o carregamento.
- Execuções exploratórias de navegador foram interrompidas e repetidas durante o diagnóstico. Não são contadas como aprovações.

Logs de falhas deliberadamente injetadas (`PRIVATE-DETAIL`, erro de integridade, falha simulada de restauração) e rejeições TLS de certificado desconhecido fazem parte de testes negativos. Devem ser avaliados junto do resultado final, não confundidos automaticamente com falha da suíte. Houve aviso de arquivo de backup não fechado no teste novo; o fechamento explícito da resposta foi acrescentado e esse teste foi repetido isoladamente com aprovação, sem o aviso. O PowerShell 5 representa mensagens de stderr como `NativeCommandError` em redirecionamentos, inclusive quando unittest termina com `OK`; a execução específica final usa subprocesso com captura conjunta para preservar o código de saída Python.

## Fluxos comprovados no navegador

`tests/browser_check.py` aprovado: primeira configuração com aceite, onboarding/avatar, cadastro de livros e leitor, empréstimo e convite por requisições autenticadas no navegador, ativação real do convite na UI, separação de papéis, acervo/busca, seleção e desmarcação de livro, Quero ler, favoritos, personalização/persistência de avatar, configurações, quatro resoluções, claro/escuro, painéis redimensionáveis e redução de movimento.

`tests/browser_ia.py` aprovado: bibliotecário configura chave, ativa, lista/seleciona modelo e testa conexão **simulada pela implementação de transporte**, depois consulta insights no Dashboard; leitor recebe obra priorizada, seleciona livro e sugestão, acompanha streaming e conversa contextual; segunda conta começa sem histórico; avaliação é publicada, exibida a outro leitor, editada, sinalizada pelo filtro, moderada pelo bibliotecário e excluída pelo autor; a notificação de moderação é conferida pela API autenticada no navegador. Claro/escuro e 1366/390 px sem transbordamento, cancelamento e desligamento global também passaram. As contas desse teste são fixtures para concentrar a validação nos novos fluxos; ativação por convite é exercitada no outro teste.

Não se declara que recuperação, devolução, renovação, backup/restauração e todos os tipos de notificações tenham sido percorridos por cliques em navegador: possuem cobertura automatizada de serviço/HTTP, com diferentes níveis de interação visual. O teste TLS utiliza o próprio computador, inclusive seu IP local; não comprova funcionamento em celular ou outro computador.

## Pendências antes da apresentação e distribuição

1. Configurar uma chave real e plano institucional adequado. Nenhum teste real de nuvem foi executado; não houve autorização de consumo de créditos. Todos os seis provedores continuam pendentes de conectividade real por chave/modelo escolhido.
2. Registrar metadados confiáveis das obras reais de autoras brasileiras. Sem metadados, a BIBI não inventa a classificação.
3. Revisar termos, retenção, tratamento de menores e política da escola. A confirmação administrativa registra a decisão institucional, não uma certificação jurídica do software.
4. Testar HTTPS e confiança do certificado em outro dispositivo na mesma rede; validar firewall e isolamento Wi-Fi.
5. Reconstruir o executável/instalador e testar a instalação resultante. A execução nativa de bandeja/segundo plano e distribuição não foi refeita nesta etapa.
6. Completar o ensaio humano dos fluxos restantes da lista solicitada, especialmente recuperação, notificações, reservas/renovações e restauração pela UI, usando instalação de demonstração isolada.

Roteiro curto: [ROTEIRO_DEMONSTRACAO.md](ROTEIRO_DEMONSTRACAO.md). A implementação local pode ser demonstrada com mocks identificados; isso não equivale a integração real em nuvem validada.
