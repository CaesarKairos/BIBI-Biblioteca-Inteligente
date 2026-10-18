# Inteligência Artificial na BIBI

## Arquitetura

A aplicação Flask existente registra `routes/ia.py`. Não há segundo servidor, interface antiga ou banco demonstrativo. A migração versionada `004_ia` acrescenta três campos opcionais de autoria e uma tabela de utilização. O mecanismo existente cria backup antes de migrar bancos anteriores.

Referência analisada: `CaesarKairos/Agente-de-IA-em-Bibliotecas`, commit `be010a39d73398a59b32664129ad106251f8399c`. Foram examinados prompts, política pedagógica, serviços de chat, recomendações e conversas, provedores Gemini/Ollama e testes de política, API, biblioteca, transporte e provedores. A política determinística foi reutilizada em `services/ai/policy.py`; o prompt foi adaptado para distinguir catálogo verificado, conhecimento literário geral e interpretação. Não foram trazidos o acervo de demonstração, a interface, raciocínio exposto, seleção livre de provedor pelo aluno ou fallback do agente original.

`services/ai/providers.py` fornece um contrato comum `models()` e `stream(model, system, messages, max_tokens)`. Endpoints são constantes internas; usuários não fornecem URLs. Autenticação, paginação e eventos SSE são adaptados por provedor. A interface recebe NDJSON de mesmo domínio e renderiza texto com `textContent`. Não há execução de ferramentas pelo modelo.

As consultas ao catálogo e os indicadores são locais. Os estudantes recebem contexto de obras e candidatos, sem agregados administrativos ou dados de outras contas. O Dashboard envia apenas contagens e títulos agregados. O bloqueio global do banco é liberado durante operações de rede para preservar circulação e permitir desativação.

## Configuração pelo bibliotecário

1. Entre como bibliotecário e abra **Configurações → Inteligência Artificial**.
2. Escolha OpenAI, Anthropic, Google Gemini, xAI — Grok, GroqCloud ou OpenRouter. Grok e GroqCloud são distintos.
3. Confira os termos do plano, tratamento de dados, retenção, disponibilidade regional e uso com menores. Registre a política da instituição; a caixa de revisão não substitui essa análise.
4. Insira a chave, confirme sua senha, assinale a revisão institucional e ative a IA. Salve. Uma instalação pode estar ativa para consulta de modelos e ainda não estar pronta para chat por faltar modelo.
5. Clique **Consultar modelos**, selecione um identificador retornado pela API, confirme sua senha e salve novamente. Nenhum modelo de produção é pré-fixado.
6. Clique **Testar conexão e geração**. O teste usa um pedido técnico curto e pode consumir saldo. Um sucesso vale para aquele instante, não garante solicitações futuras.
7. Configure solicitações por usuário/hora, total da instalação em 24 horas, concorrência e saída máxima. São janelas móveis, não viradas de dia civil.

Uma chave vazia mantém a credencial; uma nova chave substitui a salva. Remoção exige senha e desativa o uso se necessário. **Desativar imediatamente** não exige reenviar senha e impede novas chamadas. Operações já iniciadas podem chegar ao provedor antes da desativação; o chat verifica o estado entre fragmentos. Não é possível desfazer processamento remoto já recebido.

Chaves ficam em `segredos.dpapi`, protegidas por DPAPI do usuário Windows. A API nunca as devolve, nem mesmo parcialmente. Não entram no banco, exportações ou pacote. O navegador contém a chave apenas enquanto o bibliotecário a digita/envia, e limpa o campo após salvar; não é possível ocultar do próprio navegador um segredo que está sendo digitado nele. Para acesso pela rede, use o HTTPS existente com certificado confiável.

Nesta distribuição, salvar credenciais de IA fora do Windows falha de forma fechada; não há armazenamento de chave de IA em texto simples em outros sistemas. Restauração remove todas as credenciais de IA, limpa estado efêmero e volta à configuração desativada.

## Provedores

| Provedor | Geração | Modelos | Limitações |
|---|---|---|---|
| OpenAI | Responses `/v1/responses`, `store:false` | `/v1/models` | Listagem pode incluir modelos sem geração textual compatível; teste a seleção. Sem preço fornecido pela listagem. |
| Anthropic | Messages `/v1/messages`, versão `2023-06-01` | `/v1/models`, paginação `after_id` | Credencial da API direta, sem implementação de Bedrock/Vertex. |
| Google Gemini | `streamGenerateContent`, cabeçalho `x-goog-api-key` | `models`, paginação; filtra suporte a `generateContent` | API Gemini direta; não usa autenticação Vertex. Partes marcadas `thought` são descartadas. |
| xAI — Grok | Responses `/v1/responses`, `store:false` | `/v1/models` | Sem ferramentas externas ou pesquisa web. Acesso depende da chave e plano. |
| GroqCloud | Chat Completions compatível | `/openai/v1/models` | Não confundir com Grok. Modelos especializados podem não aceitar chat. |
| OpenRouter | Chat Completions compatível | `/api/v1/models` | Exibe preços informados pelo catálogo; `allow_fallbacks:false` e `data_collection:deny`. Uma rota gratuita pode não ter capacidade ou não atender a essa política. |

Os transportes usam TLS verificado, não seguem redirecionamentos e não repetem solicitações em falhas. 401, 403, 404 e 429 são traduzidos sem devolver corpo bruto do provedor. SSE expõe somente texto, nunca eventos de raciocínio. Uma conexão encerrada sem marcador de conclusão é interrupção, não sucesso. Limites locais não substituem limites de gastos no painel do fornecedor.

Documentação oficial consultada em 18/10/2026:

- [OpenAI: listagem de modelos](https://developers.openai.com/api/reference/resources/models/methods/list) e [Responses](https://platform.openai.com/docs/api-reference/responses).
- [Anthropic: API](https://platform.claude.com/docs/en/api/overview) e [modelos](https://platform.claude.com/docs/en/api/models/list).
- [Gemini: modelos](https://ai.google.dev/api/models) e [geração progressiva](https://ai.google.dev/api/generate-content).
- [xAI: Responses](https://docs.x.ai/developers/rest-api-reference/inference/responses) e [modelos](https://docs.x.ai/developers/rest-api-reference/inference/models).
- [Groq: compatibilidade](https://console.groq.com/docs/openai) e [modelos](https://console.groq.com/docs/models).
- [OpenRouter: modelos e preços](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties) e [tratamento de dados](https://openrouter.ai/docs/guides/privacy/data-collection).

Não foi feita avaliação contratual de um plano real de escola. `store:false` e a política de roteamento não são garantia universal de retenção zero. A instituição deve verificar condições efetivas antes do uso com alunos.

## Recomendações e CIÊNCIA DELAS

`recommendations.py` classifica exclusivamente livros ativos da instalação. Interesses vêm de favoritos, Quero ler, histórico de empréstimos e avaliações altas; avaliações baixas reduzem a posição. Usa categorias e temas cadastrados, disponibilidade, novidade e diversidade de prateleiras. Não afirma que empréstimo prova leitura concluída.

Entre candidatos do mesmo patamar de afinidade, a ordem explícita é: **autoria feminina brasileira documentada → autoria feminina ou brasileira documentada → classificação restante/desconhecida**. Em seguida considera disponibilidade e títulos ainda não emprestados. A diversidade distribui gêneros dentro do mesmo patamar de afinidade/prioridade. Autoria mista não é automaticamente classificada como feminina.

Os campos `autoria_genero`, `autoria_pais` e `autoria_fonte` são opcionais. A prioridade exige fonte registrada; nunca se deduz identidade pelo nome. País aceita Brasil/BR/Brazil. Sem fonte, a classificação não eleva a posição. A seção administrativa permite registrar os metadados. Para múltiplas nacionalidades ou autorias complexas, mantenha desconhecido quando o esquema não representar corretamente a obra.

Filtros explícitos de gênero, autor, autoria feminina, brasileira e disponibilidade são aplicados antes da ordenação. O chat reconhece pedidos comuns e nomes completos/categorias existentes; não é um interpretador universal de filtros em linguagem natural. Quando não há candidatos compatíveis, a IA deve explicar a ausência, sem completar com livros externos.

A quinta prateleira sempre identifica a seleção como algoritmo local, mesmo se o chat estiver ativo. Não faz geração externa ao abrir o acervo. Cache por assinatura inclui catálogo, disponibilidade, histórico, favoritos, avaliações, Quero ler e filtros, invalidando alterações relevantes. As outras quatro prateleiras permanecem.

## Conversas, privacidade e limites

Conversas ficam apenas na memória do processo, vinculadas a conta **e sessão autenticada**, com expiração após 30 minutos de inatividade, até 200 conversas na instalação e dez por conta. A limpeza de expiradas ocorre ao acessar/criar conversas, sem gravá-las no banco ou backups. Conversas vazias que falham são descartadas. Reiniciar apaga as conversas. Retêm até 12 mensagens; o contexto enviado é reduzido por tamanho. Mensagem do aluno tem limite de 2000 caracteres, catálogo remoto de 12000 caracteres e histórico remoto de 12000 caracteres, além do prompt central. O limite de tokens configurável aplica-se à saída; não equivale a um tokenizador exato de entrada.

Há saída máxima de 20000 caracteres, limite de resposta de 60 segundos verificado nos eventos, conexão de 5 segundos e leitura de rede de 35 segundos. O navegador interrompe a espera em 65 segundos e oferece cancelamento. Interrupção não adiciona resposta incompleta ao histórico contextual. Fechar a conexão no navegador não garante reembolso nem cancelamento instantâneo da inferência já iniciada no fornecedor.

Utilização local registra conta, instante, operação, provedor, modelo, estado e tokens quando informados. Não registra mensagens, chaves ou nomes. Registros são mantidos por até 90 dias, com limpeza ao iniciar nova solicitação. Falhas e cancelamentos contam para proteção de consumo. Os cabeçalhos de limites fornecidos pelo provedor são apresentados na configuração. Tokens são totais reportados por respostas, não estimativa de custo nem uma fatura completa. Preços do catálogo OpenRouter não são cobranças efetivas.

O Dashboard conserva indicadores reais e resumo local quando desligado ou indisponível. Interpretações de IA usam cache de uma hora e assinatura dos agregados/configuração. Devem ser revisadas pelo bibliotecário. O prompt não elimina todos os riscos de erro ou injeção; o controle de privilégios está no backend, sem ferramentas executáveis pelo modelo.

## Testes e empacotamento

```powershell
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python -m unittest discover -s tests -p "test_*.py"
python tests/browser_check.py
python tests/browser_ia.py
```

As suítes usam diretórios temporários, contas e catálogos sintéticos. O teste de IA bloqueia tráfego externo e simula provedores. Não roda teste real em `unittest discover`.

Verificação opcional, **somente executada pelo responsável com autorização de consumo**, uma vez por provedor desejado:

```powershell
python tests/check_ia_online.py --autorizar-consumo --provedor openai --modelo IDENTIFICADOR_LISTADO --data-dir CAMINHO_DOS_DADOS
```

Exige credencial já salva e IA globalmente ativa. Não passe chaves na linha de comando. Não envia dados do acervo ou de leitores. Não foi executada nesta entrega.

`requests`, TLS e DPAPI já fazem parte da distribuição existente; não há SDK adicional obrigatório, Ollama ou modelo local. `requirements-dev.txt` acrescenta somente a ferramenta de navegador. O spec PyInstaller inclui migrações, templates e scripts novos por suas pastas e importa o módulo de IA pelo registro estático de rotas. O executável final deve ser reconstruído e testado separadamente antes da distribuição.
