# BIBI — Biblioteca Inteligente 1.1.0

Esta versão reúne gestão da biblioteca escolar, circulação de livros e experiência individual de leitura. A release deve permanecer **em rascunho** até a revisão final pelos responsáveis pelo projeto.

## Principais recursos

- Acervo com capas, pesquisa, categorias, localização e disponibilidade.
- Cadastro de leitores; empréstimos, devoluções, renovações e reservas.
- Contas individuais por convite, perfil, avatar, favoritos, Quero ler e livros lidos.
- Histórico, avaliações, comentários, moderação e notificações.
- Dashboard administrativo, agenda, configurações, importação, exportação e backup/restauração.
- IA opcional para mediação de leitura, recomendações e apoio administrativo, com seleção automática de modelos autorizados e valorização de autoras brasileiras documentadas no catálogo.

## Instalação

Baixe `BIBI-1.1.0-Windows-x64-Portatil.zip`, extraia a pasta completa e abra `BIBI.exe`. Mantenha `_internal` ao lado do executável. Os arquivos Source code não são a distribuição para uso comum.

Requisitos: Windows 10/11 de 64 bits e Microsoft Edge WebView2. Python e ferramentas de desenvolvimento não são necessários. Na primeira abertura, cadastre a instituição e crie a conta administrativa. Os dados ficam em `%LOCALAPPDATA%\BIBI`, separados dos arquivos do programa. Antes de atualizar uma instalação, use o backup da BIBI.

O instalador Inno Setup foi compilado e preservado localmente, mas não é anexado a esta release enquanto sua instalação/desinstalação não for validada. Use o pacote portátil disponibilizado nos assets do rascunho após a publicação autorizada.

## Acesso pela rede

O computador que executa a BIBI funciona como servidor e precisa permanecer ligado. Outros dispositivos autorizados acessam pelo endereço HTTPS da rede local exibido nas Configurações. Certificado e firewall podem precisar de configuração. A instalação não disponibiliza automaticamente o sistema na internet.

## IA opcional

O bibliotecário configura os serviços externos, verifica a conexão e autoriza o uso. A BIBI seleciona modelos compatíveis e autorizados entre esses serviços. Internet, chave de API, limites, custos e condições dependem do provedor. O sistema funciona sem IA.

## Validação e limites conhecidos

O pacote foi compilado no Windows com PyInstaller. Foram testados primeiro cadastro, avatar, acervo, detalhes, perfil, configurações, HTTPS com a CA da instalação, integridade/migrações, reinício, login e persistência em dados descartáveis. A interface foi exercitada com Chromium; serviços de IA foram simulados nos testes, sem consumo externo. Consulte [o relatório de distribuição](https://github.com/CaesarKairos/BIBI-Biblioteca-Inteligente/blob/v1.1.0/docs/DISTRIBUICAO.md) no repositório.

- Não houve homologação em computador Windows limpo nem validação de instalação/desinstalação do instalador.
- A janela nativa do executável e sua tela inicial foram confirmadas por Windows UI Automation. O roteiro separado de bandeja com janela oculta retornou E_ABORT; os controles de ocultar, reabrir e encerrar pela bandeja ainda precisam de homologação.
- Capas externas dependem de internet e das fontes. Há sete capas pendentes no catálogo local auditado; esse catálogo não acompanha o programa.
- Edição física de algumas capas corrigidas ainda precisa de conferência pela biblioteca. As fontes e os motivos estão no relatório de capas.
- SMTP real, conectividade com provedores de IA reais e acesso em outro dispositivo da rede não foram homologados nesta entrega.
- Os executáveis não receberam assinatura digital.

## Integridade, créditos e licença

`SHA256SUMS.txt` contém o SHA-256 do pacote portátil. A distribuição começa sem banco, usuários, capas do catálogo, configurações particulares ou credenciais.

Projeto Philocode. Autoria e contribuições registradas: Cesar Augusto (CaesarKairos) e Nicolly França. Avatares Adventurer Neutral por Lisa Wischofsky, via DiceBear, CC BY 4.0; componentes de terceiros mantêm suas licenças.

A BIBI é software proprietário, de uso gratuito nas condições de `LICENSE`. A consulta ao código não concede autorização geral para modificar ou redistribuir o programa.
