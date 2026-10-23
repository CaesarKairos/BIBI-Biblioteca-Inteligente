# Preparação da distribuição 1.1.1

Validação realizada em Windows x64, em 22 e 23/10/2026. Este documento separa a preparação dos arquivos da homologação em uma instalação limpa do Windows.

## Resultado técnico

| Verificação | Resultado |
| --- | --- |
| `unittest discover -s tests -v` | 117 testes aprovados; [registro](validacao/distribuicao-unittest-release.txt). |
| Playwright de IA (`tests/browser_ia.py`) | Aprovado: ativação, seleção automática, chat isolado, troca e remoção de serviços, desligamento e 13 seções de configurações, em três larguras e nos dois temas; [registro](validacao/distribuicao-ia-final.txt). Provedores simulados, sem consumo de API. |
| Catálogo local e capas em Chromium | 76 títulos examinados; 76 capas renderizadas e nenhuma referência ausente; [resultado](validacao/capas-navegador.json) e [fontes](CAPAS_DISTRIBUICAO.md). |
| Executável Windows | Aprovado em dados descartáveis: primeiro cadastro, avatar, 32 livros/32 capas próprias, assets, navegação Chromium, HTTPS com certificado validado, migrações, integridade, reinício, login e persistência; [registro](validacao/distribuicao-exe-final.txt). |
| PyInstaller | Build nativo Windows, PE x64, distribuição onedir completa. Inclui templates, arquivos estáticos, migrações, dependências nativas e schemas do avatar. |
| Inno Setup | Compilado; instalação e desinstalação ainda não homologadas. Não anexar o instalador ao rascunho enquanto essa etapa não for validada. |
| Janela nativa do executável | Aprovada: janela e conteúdo real da tela inicial confirmados por Windows UI Automation; [resultado](validacao/distribuicao-janela-exe.json). |
| Bandeja e seus controles | Teste separado `desktop_tray_check.py` não concluído: inicialização WebView2 retornou E_ABORT no roteiro com janela oculta. Não declarar homologação desses controles. |
| Windows limpo | Não testado. Há uma BIBI 1.0.0 instalada neste computador, preservada durante o trabalho. |
| OpenRouter real | Conexão, geração e conversa literária verificadas com modelo gratuito; capturas sem simulação. |
| SMTP real / outro dispositivo da rede | Não homologados nesta entrega. |

As capturas atuais estão em [docs/readme](readme/README.md). O roteiro usa o catálogo local, com contas e circulação sintéticas em outra pasta de dados. A IA aparece ativada e em conversa real via OpenRouter, sem respostas simuladas; a credencial foi fornecida apenas no ambiente de execução e armazenada localmente com DPAPI.

## Correções relevantes

- O pacote anterior não incluía `dicebear_schema`, lido dinamicamente pelo editor de avatar. O cadastro inicial funcionava, mas o avatar retornava erro 500. O spec agora inclui os schemas, e o teste do executável exige completar o avatar e navegar pela interface.
- O build usa apenas arquivos estáticos versionados. Uploads locais não são incorporados por uma cópia indiscriminada da pasta `static`.
- O acervo e os detalhes preservam o placeholder quando uma capa falha ou retorna uma imagem remota de 1×1 pixel. Vinte e duas referências ausentes foram corrigidas no banco local, com backup e fontes registradas.
- As prévias do editor de avatar são solicitadas quando as opções entram na área visível. O servidor reutiliza renderizações em memória.
- A versão da interface e dos backups é compartilhada em `version.py`.
- A inicialização preserva a ativação do registro atual de serviços de IA verificados. Uma checagem destinada ao fluxo legado estava desativando o novo registro no reinício; um teste de regressão cobre esse cenário.
- Erros de execução podem ser consultados em `BIBI.log`, na pasta persistente da instalação, com rotação de tamanho. O registro não inclui corpos de pedidos ou credenciais.
- Portas opcionais de execução permitem testar outra instalação sem ocupar as portas da BIBI do usuário. Os padrões continuam 5000 em loopback e 5443 no HTTPS da rede.

## Arquivos de distribuição

- `dist/release/BIBI-1.1.1-Windows-x64-Portatil.zip`: pasta completa, incluindo `BIBI.exe` e `_internal`.
- `dist/release/SHA256SUMS.txt`: integridade do ZIP anexável ao rascunho.
- `dist/release/BIBI-1.1.1-Windows-x64-Setup.exe`: instalador compilado, preservado localmente enquanto aguarda homologação.

O ZIP também foi extraído em outra pasta descartável e o executável extraído passou pelo mesmo fluxo completo; [registro](validacao/distribuicao-zip-executado.txt).

O [manifesto do pacote](validacao/distribuicao-pacote.json) registra tamanho, hash e verificações dos arquivos. O empacotador rejeita bancos, segredos, logs e capas do catálogo. O ZIP não contém contas iniciais, acervo da escola, SMTP, chaves de IA ou certificados da instalação. A autoridade TLS é criada na primeira execução de cada instalação.

## Reproduzir no desenvolvimento

Use Python 3.11 x64 e as dependências fixadas do projeto. O ambiente desta validação utilizou PyInstaller 6.20.0 e Playwright 1.63.0 (a versão declarada em requirements-dev é 1.62.0; a execução não comprova especificamente essa versão).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tests/browser_ia.py
.\.venv\Scripts\python.exe tests/browser_distribuicao.py --catalogo-local "$env:LOCALAPPDATA\BIBI"
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --distpath dist/Windows-1.1.1 packaging/BIBI.spec
.\.venv\Scripts\python.exe tools/catalogo_distribuicao.py "$env:TEMP\bibi-distribuicao-demo.zip"
.\.venv\Scripts\python.exe tests/smoke_executavel.py --exe dist/Windows-1.1.1/BIBI/BIBI.exe --zip "$env:TEMP\bibi-distribuicao-demo.zip"
.\.venv\Scripts\python.exe tests/smoke_janela_executavel.py --exe dist/Windows-1.1.1/BIBI/BIBI.exe
.\.venv\Scripts\python.exe tools/pacote_windows.py --build dist/Windows-1.1.1/BIBI
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" setup.iss.example
```

O build usa `git ls-files` para identificar os assets; por isso requer um checkout Git. O caminho do compilador Inno Setup depende de sua instalação. As pastas antigas em `dist` não foram apagadas para contornar falhas de acesso do OneDrive.

O smoke usa `LOCALAPPDATA` temporário e portas livres para os dois servidores. `BIBI_DESKTOP_PORT` e `BIBI_LAN_PORT` permitem esse isolamento; não representam publicação na internet. O teste encerra somente o processo que iniciou, sem interromper a BIBI aberta pelo usuário. O encerramento automatizado do processo comprova reinício e persistência, mas não substitui o teste do menu e da bandeja nativos.

## Operação e privacidade

Usuários comuns devem seguir a instalação descrita no [README](../README.md). Instalações e dados ficam separados: o programa pode estar em Program Files ou em uma pasta portátil, enquanto dados e segredos ficam em `%LOCALAPPDATA%\BIBI`.

A auditoria do catálogo usa somente os campos bibliográficos, sem abrir contas, leitores ou configurações privadas. As credenciais fornecidas durante o atendimento foram utilizadas apenas na autenticação da aplicação em execução e não foram gravadas nos scripts, nas capturas, no Git ou nos pacotes.

O [guia de operação](GUIA_OPERACAO.md) descreve backup e restauração. O [guia de rede](REDE_LOCAL.md) descreve HTTPS, dispositivos autorizados e certificados. As [notas da versão](NOTAS_VERSAO_1.1.1.md) estão preparadas para a release em rascunho. A tag deve apontar para o commit final da `main`; o rascunho não deve ser publicado automaticamente.
