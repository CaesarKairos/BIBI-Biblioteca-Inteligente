# Servidor da biblioteca na rede local

Abra a BIBI no computador da biblioteca. Em **Configurações → Biblioteca**, o endereço real aparece como `https://192.168.…:5443`, com botão para copiar, certificado público e diagnóstico. Não precisa de domínio nem proxy. A janela local continua em `http://127.0.0.1:5000`; essa porta não escuta na rede.

## Preparar os dispositivos

1. Conecte computador e celular à mesma rede. Redes de convidados podem impedir comunicação entre dispositivos.
2. No computador da biblioteca, baixe **Certificado desta biblioteca** nas configurações. Transfira esse arquivo público ao dispositivo por um canal confiável, por exemplo USB. Nunca transfira `segredos.dpapi` nem arquivos de chave.
3. Confira a impressão SHA-256 com a exibida na própria BIBI. Instale o certificado como autoridade confiável apenas nos dispositivos autorizados para esta biblioteca. Não prossiga ignorando avisos de certificado do navegador.
4. No Android, procure em Configurações por **Instalar certificado → Certificado de CA** (o caminho depende do fabricante/versão; pode exigir bloqueio de tela). Selecione `BIBI-rede-local.crt`. Abra o endereço copiado no Chrome e confira que não há aviso TLS antes de entrar. Dispositivos gerenciados podem exigir instalação pela equipe da escola; alguns aplicativos não aceitam autoridades instaladas pelo usuário.
5. No Windows cliente, importe o certificado no armazenamento **Autoridades de Certificação Raiz Confiáveis** do usuário, após verificar sua origem. Não é necessário instalar a BIBI nos clientes.

A confiança é por instalação, não por IP: uma mudança de IP renova o certificado do servidor automaticamente, preservando a autoridade. Use o novo endereço exibido. Ao remover o acesso à biblioteca, remova também essa autoridade dos dispositivos. A autoridade está restrita a endereços privados e localhost; não emite certificados para domínios públicos. Validade da autoridade: dez anos; certificado do servidor: noventa dias, renovado automaticamente antes de vencer enquanto o aplicativo estiver em execução. A proximidade do vencimento da autoridade é apresentada como erro para exigir renovação explícita da confiança.

Referências: [certificados no Android/Pixel](https://support.google.com/pixelphone/answer/2844832?hl=pt-BR), [armazenamento de confiança no Windows](https://learn.microsoft.com/en-us/windows-hardware/drivers/install/trusted-root-certification-authorities-certificate-store), [certificados X.509](https://cryptography.io/en/stable/x509/tutorial/).

## Se outro dispositivo não conectar

- Confira se o servidor aparece em execução e use **Verificar conexão**. Esse autoteste usa a interface da rede e valida TLS, mas não comprova acesso de outro equipamento.
- No Windows, use perfil de rede **Privada** somente na rede confiável da escola. Se o firewall bloquear, uma pessoa autorizada deve permitir TCP de entrada na porta 5443, no perfil Privado e com origem limitada à sub-rede local. Não desative o firewall. A BIBI não cria regras nem instala certificados silenciosamente.
- Confira isolamento entre clientes Wi-Fi, redes de convidados, VLANs e bloqueios do roteador. Não encaminhe portas para a internet. Endereços IPv4 privados são detectados automaticamente; redes exclusivamente IPv6 não são atendidas nesta versão.
- Se aparecer aviso TLS, confira data/hora, endereço atual e certificado instalado. Não envie senha antes de resolver o aviso. Uma instalação diferente tem outra autoridade.
- Porta ocupada ou erro de certificado não impede abrir a janela local: o diagnóstico mostra a falha do servidor de rede. Feche a outra instância antes de reabrir.

## Janela e disponibilidade

Minimizar mantém os servidores. No Windows, fechar a janela mantém a BIBI na bandeja quando o ícone foi criado; clique nele para reabrir ou use **Encerrar BIBI e servidor** para sair de verdade. Se a bandeja não estiver disponível, fechar a janela encerra os servidores. Suspender, desligar ou sair da sessão Windows interrompe o acesso; bandeja não substitui serviço do sistema.

## Segurança e compatibilidade

O histórico `d262282` iniciava Flask em `0.0.0.0`, oferecendo acesso direto à rede. A implementação anterior desta branch restringia Waitress a loopback e exigia proxy TLS externo. Agora Cheroot atende HTTPS diretamente em `0.0.0.0:5443`; Waitress continua restrito a loopback para a janela desktop e recuperação local. O servidor LAN ignora cabeçalhos de proxy e recusa origens fora das redes privadas. Estar na rede não concede permissões.

Contas, senhas, sessões, CSRF, auditoria, proteção do último bibliotecário e recuperação local permanecem nos mesmos serviços. Cookies de rede recebem Secure/HttpOnly/SameSite. HTTP remoto continua recusado. O endereço legado de proxy permanece no banco para compatibilidade, sem ser sobrescrito pelo endereço detectado.

Não há migração destrutiva do banco. Certificados ficam em `%LOCALAPPDATA%\BIBI\rede`; autoridade privada e senha da chave TLS ficam em `segredos.dpapi`, protegidas pelo usuário Windows. Backups portáteis continuam sem esses segredos: uma instalação nova exige novo certificado confiável nos clientes. Não copie segredos entre usuários Windows.

## Validação em outro dispositivo

No Android, abra o endereço exibido, valide TLS, entre com uma conta sintética e consulte o Acervo. Minimize e depois feche a janela para a bandeja: atualize a página no celular em cada situação. Reabra a BIBI pelo ícone. Ao encerrar pelo menu da bandeja, confirme que o celular perde o acesso. Registre modelo/Android, rede e resultado; um pedido feito pelo próprio IP no computador servidor não equivale a esse teste.

Para preparar uma instalação descartável, execute `python tests/manual_rede.py`. Ela usa banco temporário, livro sintético, senha aleatória e portas 5001 (loopback) e 5443 (HTTPS LAN). O terminal mostra credenciais, caminho do certificado e endereços. Interromper o processo encerra os servidores e remove essa instalação. Não execute junto com outra instância que já ocupe essas portas. `python tests/browser_rede.py` verifica essa instância no Chromium e grava capturas temporárias.

Capturas desta implementação: [desktop](capturas-rede/rede-1366.png), [1920×1080](capturas-rede/rede-1920.png), [celular claro](capturas-rede/rede-390.png), [celular escuro](capturas-rede/rede-390-escuro.png).

Validação executada em 16/10/2026: **63 testes de unittest aprovados**; após o ajuste de fechamento do socket em conflito de porta, os quatro testes de rede foram repetidos e passaram. TLS com autoridade verificada em loopback e no IPv4 da interface Wi-Fi do próprio servidor; login real por HTTPS com CSRF e cookie Secure; persistência da autoridade e alteração de SAN ao mudar IP; recusa de certificado não confiável; autorização de bibliotecário/leitor, HTTP remoto, Host e cabeçalhos de proxy; conflito de porta sem impedir a aplicação local. Chromium: salvar instituição, diagnóstico, fechar/reabrir sem alteração pendente, IDs, console e três resoluções. Windows/WebView2: teste específico da bandeja aprovado, incluindo fechar, continuar atendendo TLS, reabrir e encerrar. `pip check` e `git diff --check` também passaram.

Limitações da validação: em 17/10/2026, o usuário confirmou acesso e login pelo Android na mesma rede, mas relatou aviso de conexão insegura. Isso confirma a conectividade entre dispositivos; a confiança no certificado ainda não foi confirmada. A instância sintética foi encerrada após identificar que ocupava a porta 5443 ao abrir a instalação real. O teste nativo adicional de recuperação (`desktop_recovery_check.py`) não concluiu o carregamento do WebView2 nesta sessão e apresentou E_ABORT; não é declarado aprovado. A recuperação e suas restrições continuam cobertas por testes de API. Não foi feito novo build do instalador nem homologação em Windows limpo. O WebView2 também registrou aviso ao limpar arquivos temporários ainda ocupados após o teste da bandeja.
