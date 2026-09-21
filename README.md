# BIBI — Biblioteca Inteligente

BIBI administra bibliotecas **físicas**, com Python, Flask, SQLite, HTML/CSS/JavaScript e janela PyWebView no Windows. O computador da biblioteca mantém o banco e atende os navegadores dos leitores quando a rede HTTPS é configurada. Não existem bancos independentes nos celulares.

Esta evolução preserva o acervo, circulação, agenda, Dashboard, capas uniformes, cinco prateleiras, temas e painéis redimensionáveis. Acrescenta contas individuais, convites fechados, perfil, reservas, avaliações, notificações, CSV e backup. **Não há integração de IA.** O gatinho identifica apenas as áreas preparadas para recursos futuros; a prateleira especial informa que mostra uma amostra do acervo.

## Executar no Windows

Use Python 3.11 de 64 bits (ambiente utilizado na validação), com WebView2 disponível para a janela desktop:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Não copie nem configure `.env`: a aplicação não o utiliza. `app.py` cria a aplicação explicitamente; importar o módulo não abre janela, banco ou worker. `desktop.py` inicia Waitress em loopback, o worker periódico e a janela PyWebView. Não execute duas instâncias para a mesma biblioteca.

Na primeira abertura, informe biblioteca/escola, nome, e-mail e senha do primeiro bibliotecário. Guarde o código de recuperação offline mostrado uma única vez. O assistente funciona somente no computador servidor e fecha após concluir. Não há senha padrão nem promoção automática de leitores legados.

**Instalação antiga:** mantenha `%LOCALAPPDATA%\BIBI` intacto e execute sob o mesmo usuário Windows. A migração preserva acervo e histórico, cria backup SQLite antes das alterações e exige o assistente para criar a primeira conta. Referências órfãs interrompem a migração: devem ser corrigidas explicitamente, sem apagar registros. Não substitua o banco antigo por um vazio.

Consulte o [guia de operação e entrega](docs/GUIA_OPERACAO.md) para convites, recuperação, e-mail, permissões, circulação, rede e restauração.

## Recursos e permissões

- **Bibliotecários autenticados:** Dashboard, leitores, circulação, agenda, configuração, convites, moderação, auditoria e operações de dados. Estar em localhost ou no PyWebView não concede privilégios.
- **Leitores autenticados:** acervo, perfil/avatar, próprios empréstimos e histórico, pedidos de renovação, Quero ler, reservas, notificações e avaliações. Professor é uma categoria de leitor, não um administrador.
- **Sem conta:** uma pessoa ainda pode ser cadastrada e receber empréstimos físicos. Não existe cadastro público livre; acesso pessoal exige convite vinculado a um leitor.
- **Acervo:** pesquisa combinada por título, autor, ISBN, temas e localização, categoria/disponibilidade e carregamento progressivo. Capas têm tamanho fixo; páginas continuam sendo informação bibliográfica opcional.
- **Circulação:** vínculo por ID do leitor, devolução idempotente, renovação manual, reservas com exemplares separados, perdas/reparos e arquivamento com histórico preservado.
- **Dados:** CSV com modelo, mapeamento, prévia e confirmação; relatórios agregados ou detalhados; backup consistente de SQLite ativo, assets e manifesto, com restauração local controlada.

Atalhos administrativos: Ctrl+1 Dashboard, Ctrl+2 Acervo, Ctrl+3 Empréstimos, Ctrl+4 Agenda e Ctrl+5 Leitores. Para leitores: Ctrl+1 Acervo e Ctrl+2 Minha conta.

## Arquitetura

| Caminho | Responsabilidade |
|---|---|
| `app.py`, `desktop.py`, `config.py` | Fábrica Flask, início explícito do desktop/worker, caminhos |
| `database/schema.sql`, `database/migrations/` | Schema legado e migrações versionadas aditivas |
| `utils/auth.py`, `utils/secrets_store.py` | Autorização, sessões/CSRF/origem e DPAPI Windows |
| `routes/contas.py`, `services/contas_service.py` | Primeiro acesso, login, convites, recuperação e papéis |
| `routes/perfil.py`, `services/avatar_service.py` | Recursos pessoais e avatar local DiceBear |
| `services/circulacao_service.py` | Regras e transições de estoque, reservas e empréstimos |
| `services/mensagens_service.py`, `services/email_service.py` | Notificações persistentes, SMTP TLS e worker |
| `routes/gestao.py`, `services/dados_service.py` | Políticas, moderação, CSV, backup, auditoria e saúde |
| `templates/`, `static/` | Interface existente e novas páginas de acesso, perfil e gestão |
| `tests/` | Testes sintéticos de serviços, segurança e navegador |
| `legacy/`, `docs/REFATORACAO.md` | Referência histórica, sem execução ou autenticação de produção |

Dependências testadas estão fixadas em `requirements.txt`. Chart.js e Flatpickr são servidos localmente em `static/vendor`, com licenças. ISBN/SMTP dependem de rede; fontes web têm fallback local. Avatar Adventurer Neutral é gerado localmente pelo DiceBear, sem enviar e-mail, nome ou seed para serviço externo.

## Dados e segredos

Dados permanecem em `%LOCALAPPDATA%\BIBI`: `Biblioteca.db`, capas e `backups`. Não copie apenas o `.db` enquanto o sistema está aberto: use **Gestão → Backup** para incluir WAL de maneira consistente.

Senha SMTP e chave da sessão ficam em `segredos.dpapi`, protegidas pelo usuário Windows. Não são exportadas no backup portátil. Senhas de contas usam hash adaptativo; códigos temporários ficam somente como hash. O backup contém dados pessoais e hashes e precisa ser guardado com acesso restrito. Ao restaurar, sessões/códigos são invalidados, um novo código offline é apresentado e o SMTP deve ser reconfigurado.

## Build Windows

```powershell
python -m PyInstaller --noconfirm packaging/BIBI.spec
```

O spec versionado inclui templates, schema, migrações, assets, bibliotecas nativas e dados do DiceBear; não inclui `.env`, bancos nem segredos. Distribua **a pasta inteira** `dist/BIBI`, incluindo `_internal`, não apenas o executável. `setup.iss.example` é o modelo Inno Setup atualizado. O build em Windows foi executado; instalação/desinstalação e a janela nativa em computador limpo ainda exigem homologação. Não confunda o build com essa homologação.

## Verificação

```powershell
python -m unittest discover -s tests -v
python -m pip install playwright
python -m playwright install chromium
python tests/browser_check.py
python tests/browser_loan_search.py
```

Testes usam bancos temporários e dados sintéticos; não enviam e-mails reais. O navegador bloqueia serviços externos. As comparações antigas com autorização por IP foram substituídas por contratos autenticados, preservando verificações de catálogo, páginas, agenda e circulação. Resultados desta etapa estão em [EVOLUCAO_PRODUTO.md](docs/EVOLUCAO_PRODUTO.md).

## Limites relevantes

A equipe da escola precisa configurar HTTPS/proxy/certificado antes de liberar a rede; o campo de endereço não modifica infraestrutura. O servidor precisa permanecer ligado para acesso e envio. Reservas exigem que a biblioteca defina seu prazo de retirada; regras anteriores são mantidas até a configuração explícita. O filtro de comentários é apoio determinístico à moderação humana. Termos e aviso de privacidade precisam ser revisados pela instituição; não representam certificação jurídica.

## Licença

O projeto tinha declaração de MIT, mas não possui arquivo LICENSE versionado nesta revisão; isso precisa ser formalizado pelo responsável. As dependências preservam suas licenças. Adventurer Neutral, de Lisa Wischofsky, usa [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), com atribuição no editor de avatar. Relatórios acadêmicos e resultados de pesquisa não foram alterados.
