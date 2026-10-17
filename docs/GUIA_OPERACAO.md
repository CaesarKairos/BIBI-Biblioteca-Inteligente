# Guia de operação — evolução de contas e circulação

## Instalação nova e atualização

Abra `python app.py` no ambiente com as dependências de `requirements.txt`, ou o executável da distribuição completa. O servidor Waitress e a janela PyWebView usam a mesma instalação. Importar `create_app` não inicia janela nem rotina periódica.

O diretório de dados continua `%LOCALAPPDATA%\BIBI`. Use o mesmo usuário Windows da instalação antiga. Não apague nem mova o banco para a pasta do executável. Antes das migrações pendentes, o sistema cria `backups/antes-migracao-*.db` com a API de backup SQLite, incluindo o estado do WAL. Esses backups de pré-migração são cópias de recuperação técnica do banco legado, não os ZIPs portáteis da interface; podem conter configurações sensíveis antigas e devem permanecer protegidos.

`001_contas` cria contas, sessões, códigos, tentativas e auditoria. `002_circulacao` adiciona arquivamento, renovações/encerramento, reservas, Quero ler, pedidos de renovação, ocorrências, notificações, avaliações e fila de e-mail. `003_integracao` acrescenta aceite versionado, onboarding, favoritos ordenados, preferências por conta e data da instalação. Contas com avatar mantêm a conclusão; contas sem avatar recebem a etapa uma vez. A data antiga deriva da primeira conta e fica marcada como estimada. `Migracoes` registra as versões aplicadas. Alterações aditivas e versões são verificadas antes de reaplicar; a transação reverte em caso de erro. Referências órfãs impedem a migração sem exclusão automática: preserve o backup e solicite correção explícita do cadastro inconsistente.

## Primeiro bibliotecário, termos e recuperação local

1. Abra o BIBI no computador servidor. Sem contas, o assistente local prepara a biblioteca.
2. Informe biblioteca/escola, nome, e-mail, senha de 12 a 128 caracteres e confirmação.
3. Abra os links Termos de Uso e Aviso de Privacidade. A leitura ocorre em um diálogo na mesma tela; Escape ou Fechar encerram o diálogo e devolvem o foco, preservando o formulário. Registre o aceite.
4. O banco registra a conta, versão e horário UTC do aceite. A escola deve revisar os textos em Configurações → Biblioteca; o texto inicial não inventa responsável, contato, retenção ou certificação jurídica.
5. A sessão inicia automaticamente. Personalize o avatar ou confirme o sugerido para entrar. Não existe etapa de guardar código manual. SMTP permanece opcional; o e-mail inicial não está verificado.

Para recuperar uma conta bibliotecária, pressione **Alt** e abra **Conta → Recuperar conta bibliotecária neste computador** no menu nativo da janela desktop. Informe o e-mail da conta ativa, escolha uma senha nova e confirme. Há cinco tentativas por janela de quinze minutos. O token criptográfico dura três minutos, fica somente em memória e permite um uso. A validação exige loopback, autorização emitida pelo processo desktop e a mesma sessão de recuperação. Abrir a página num navegador não cria essa autorização. Uma nova abertura do menu substitui a anterior.

A recuperação invalida sessões e códigos relacionados, mantém o estado do onboarding e registra auditoria sem senha/token. O segredo de instalação usa SecretStore/DPAPI e não contém senha de conta. Quem controla a sessão local do Windows da instalação já pode operar o servidor e acessar arquivos; essa recuperação reflete esse acesso e não oferece isolamento contra o próprio usuário Windows.

Instalações que já guardavam um código legado podem usá-lo uma única vez em Recuperação do bibliotecário no servidor. Depois disso, o hash legado é removido e nenhum substituto manual é emitido. O PIN de quatro caracteres também foi descontinuado: senhas reais de contas autorizam confirmações sensíveis.

## Contas, categorias e permissões

`Usuarios` continua representando leitores administrativos. `Contas` representa acesso autenticado e vincula o histórico pelo ID do leitor. Uma pessoa pode ter empréstimos sem conta e sem e-mail.

Estudante/professor são categorias de circulação. Leitor/bibliotecário são papéis de acesso. Professor não recebe privilégios. O leitor consulta apenas seus próprios dados pessoais; rankings, telefones, turmas, agenda e relatórios administrativos ficam restritos a bibliotecários.

**Leitores → Convites, recuperação e permissões** permite mudar papel ou bloquear/reativar, exigindo a senha atual do bibliotecário e motivo. Sessões anteriores da conta afetada são revogadas. O último bibliotecário ativo não pode ser bloqueado, rebaixado ou arquivado. A autorização é conferida nas APIs, inclusive para localhost/PyWebView.

## Convite presencial, sem SMTP

1. Cadastre ou selecione o leitor existente em **Leitores**. Confirme presencialmente o e-mail que será usado para entrar.
2. Abra **Acesso / convite**, ou **Leitores → Convites, recuperação e permissões**.
3. Escolha **Ativar conta de leitor** e **Gerar código presencial**.
4. Copie ou mostre o código de 16 caracteres, agrupado para digitação. É válido por 24 horas, para aquele leitor/e-mail, uma única vez. Use **Já entreguei** para ocultar.
5. O leitor acessa o endereço HTTPS fornecido pela escola e escolhe **Ativar convite**. Informa o mesmo e-mail, código, senha própria e confirmação; a sessão inicia automaticamente e abre a personalização do avatar. Salve ou use o sugerido para entrar. Recuperação de senha não reinicia a personalização.

Reemitir invalida códigos anteriores da mesma finalidade. Revogar invalida os códigos do leitor. Se o e-mail estiver errado, corrija o cadastro e emita novo convite. A ativação ignora campos manipulados de papel/categoria: cria sempre papel leitor e preserva a categoria cadastrada.

**Conta ativa não significa e-mail verificado.** O convite presencial autoriza o acesso após conferência na biblioteca, mas não comprova posse da caixa postal. Perfil, avatar, reservas e notificações internas funcionam normalmente sem SMTP. O bibliotecário não conhece nem escolhe a senha do leitor.

Depois de um empréstimo, o aviso **Gerenciar convite** abre a gestão daquele leitor. Convites são uma operação separada: nenhuma falha de convite ou envio desfaz o empréstimo físico.

## Remetente, convite por e-mail e verificação

Em **Configurações → E-mail**, configure servidor SMTP, porta 587 com STARTTLS ou 465 com TLS, endereço remetente e senha de aplicativo apropriada ao provedor. Salve e use **Testar conexão, autenticação e envio**. O teste vai para a conta do bibliotecário que o solicitou. O resultado distingue falha de aceitação pelo SMTP; somente conferir a caixa postal confirma chegada.

A senha salva nunca é devolvida pela API. Deixe a nova senha vazia para mantê-la, informe outra para substituir ou marque **Remover credencial salva**. No Windows, a senha e a chave de sessão são protegidas por DPAPI para o usuário da instalação. `.env` não é lido. Ao atualizar, uma senha SMTP legada que esteja no banco é transferida ao armazenamento protegido e apagada do campo correspondente. Não copie `segredos.dpapi` para outro usuário/computador.

Para convite por e-mail, selecione o leitor e use **Enviar convite por e-mail**. Um envio recusado revoga o código e mostra falha. Um envio aceito não cria a conta nem verifica o e-mail. A ativação com o código recebido exclusivamente por essa caixa confirma sua posse. A mensagem informa que o acesso depende da rede escolar e do servidor ligado; não manda localhost para os leitores.

Em **Configurações → Minha conta → E-mail de acesso**, confirme sua senha e solicite um código para o endereço atual ou novo. Confirme o código recebido para verificar/trocar o e-mail. A operação encerra sessões anteriores. Mensagens com informações pessoais e recuperação automática só são enviadas a contas ativas com endereço verificado. Contas presenciais sem verificação usam notificações internas e recuperação assistida.

## Recuperação assistida

Confira presencialmente a identidade do leitor. Em **Leitores → Convites, recuperação e permissões**, selecione **Recuperação assistida de senha** e gere um código presencial. O leitor usa **Esqueci minha senha**, e-mail, esse código e sua nova senha. O bibliotecário não escolhe a senha. Códigos de ativação, recuperação de senha, verificação de e-mail e recuperação offline têm finalidades separadas.

Quem já possui e-mail verificado pode solicitar recuperação por mensagem na tela de acesso. A resposta pública é genérica para não revelar existência/estado de contas. Se a mensagem não chegar, procure a biblioteca. Não há cadastro público livre.

## Circulação, reservas e ocorrências

Pesquise o nome no formulário de empréstimo e selecione o cadastro existente; o vínculo é por ID. Não selecionar um cadastro significa criar um novo leitor: e-mail repetido pede seleção do existente, sem alterar silenciosamente uma pessoa. A busca na aba Empréstimos ignora maiúsculas/acentos e combina nome, título, turma e status dentro do filtro escolhido. Em **Todos**, devolvidos e perdidos não apresentam ações de empréstimo ativo.

Em **Configurações → Circulação**, defina máximo de exemplares, prazo, limite de renovações e bloqueio por atraso para cada categoria, além das horas para retirar reserva. Até salvar, preserva-se a compatibilidade legada: estudante com máximo de um exemplar e prazo padrão de sete dias; professor sem limite explícito e prazo inicial no mesmo dia; renovação sem novo limite e sem bloqueio por atraso. O formulário administrativo pode informar um prazo pontual. Esses defaults são compatibilidade, não recomendação pedagógica. A escola deve revisar e salvar suas regras. Reservas ficam indisponíveis até definir o prazo de retirada, evitando impor uma regra escolar não aprovada.

Configurar novos prazos não reescreve vencimentos já registrados. Pedidos pessoais de renovação exigem aprovação do bibliotecário. Renovação respeita estado, limite, atraso configurado e fila de reservas. Devoluções repetidas não aumentam estoque duas vezes.

**Quero ler** é lista pessoal; não muda estoque nem cria fila. **Reserva** exige título sem exemplar livre e conta autenticada, permite uma reserva ativa por leitor/título, mostra posição e permite cancelamento próprio. Ordem: data de criação e ID. Ao devolver, cada exemplar é separado para o primeiro elegível, considerando conta ativa, limite e atraso. Leitores temporariamente inelegíveis mantêm sua ordem para próxima distribuição. Exemplares separados não entram no estoque livre. Só o bibliotecário efetiva a retirada como empréstimo, selecionando o leitor correto — o botão permanece acessível mesmo com zero exemplares livres.

Estados: fila → retirada → concluída; ou cancelada/expirada. Expiração devolve o exemplar à distribuição. O worker verifica na abertura e a cada 30 minutos; operações de circulação também conferem prazos. Não há processamento enquanto o servidor está desligado.

Em **Empréstimos → Renovações, reservas e ocorrências**, diferencie observação, retirada para reparo, retorno de reparo, baixa e perda. Observação pode ser vinculada ao empréstimo sem mudar estoque. Perda vinculada encerra a quantidade integral daquele empréstimo sem registrar devolução; não repõe disponibilidade. Reparo atua sobre exemplares livres. Não há multas nem cobrança.

Arquivar livro/leitor preserva referências e histórico. Empréstimos e reservas pendentes impedem o arquivamento. Arquivar leitor bloqueia sua conta e invalida convites. O CRUD comum não exclui fisicamente os registros históricos.

## Navegação, Perfil e Configurações

Perfil preserva os três painéis do BIBI. Configurações abre sobre a página atual pelo ícone de engrenagem, com navegação por seções e rolagem interna. Mantém os tons creme/bege/verde e o tema escuro; fechar devolve o foco sem perder filtros ou o livro selecionado.

Bibliotecários: Dashboard, Acervo, Empréstimos, Agenda, Leitores e Perfil. Leitores: Acervo e Perfil. Os três ícones inferiores alternam tema, abrem Configurações e encerram a sessão. A autorização é conferida no servidor. `/gestao` redireciona para Configurações; os endpoints administrativos antigos continuam como contratos de compatibilidade, sem uma segunda página Gestão.

Configurações organiza Minha conta, Biblioteca, Acervo/cadastro, Agenda, Circulação, E-mail, Dados, Backup/restauração, Moderação, Segurança/auditoria/integridade e Sobre. Há um único formulário SMTP, que salva servidor, porta, endereço e credencial pelo mesmo contrato. Remover credencial exige senha real. Leitores só recebem Minha conta, Aparência, Informações institucionais e Sobre; os formulários administrativos não são renderizados para eles.

Sobre apresenta BIBI, Philocode, versão, projeto e textos institucionais. Bibliotecários também veem biblioteca, data de criação (identificada como aproximada se derivada de conta antiga), schema, migrações, integridade e último backup. Não expõe o diretório local aos leitores.

## Perfil, avatar e comentários

**Perfil do leitor** destaca avatar, nome e categoria/turma. Reúne dados pessoais, até quatro livros favoritos, empréstimos/histórico, Quero ler, reservas, notificações e avaliações. O avatar usa o estilo exato Adventurer Neutral, versão 10.6.0, gerado localmente com DiceBear. Escolha olhos, boca, sobrancelhas, óculos e cores; use prévia, aleatorização, salvar ou cancelar. Configuração, versão e seed aleatória persistem no banco. Nome/e-mail não são usados como seed nem enviados para uma API externa. Atribuição: Lisa Wischofsky, CC BY 4.0.

**Favoritos** representa até quatro obras existentes, sem repetição, com remoção e ordenação. Para trocar, remova uma obra e adicione outra. Livros já favoritos que forem arquivados permanecem identificados; não podem ser adicionados novamente. **Quero ler** é uma lista separada de intenção, sem limite de quatro e sem reserva automática. O perfil permanece privado, sem seguidores ou feed.

O perfil do bibliotecário apresenta identidade, e-mail, verificação, criação da conta, alteração de senha e atalhos de auditoria/configurações; não mostra favoritos ou configurações globais como dados pessoais.

Avalie de uma a cinco estrelas e comente. Uma avaliação atual por leitor/livro; o próprio autor pode editar ou remover. Não se exige empréstimo anterior. Texto é renderizado como texto, não HTML executável. O filtro determinístico sinaliza palavras para revisão e não substitui moderação humana. Intervenções do bibliotecário exigem motivo e geram auditoria/notificação. Opiniões publicadas não incluem nome, e-mail, telefone ou turma do autor.

## Notificações e tarefas

Eventos de empréstimo, devolução, prazo, renovação, reserva e moderação geram notificações internas persistentes com chave única. A fila SMTP registra pendente, enviando, aceito, falha ou incerto. São até três tentativas com intervalo de 30 minutos. Envio interrompido pode ter sido aceito pelo provedor: fica incerto e não é reenviado automaticamente. Falha de e-mail não reverte circulação. O histórico interno continua disponível.

Os quatro templates editoriais de circulação são preservados. **Saúde** mostra integridade SQLite, migrações, espaço livre, backups, estados da fila, worker e últimos resultados observados das fontes ISBN nesta execução. A tela não faz chamadas externas para fingir um estado online. Publicações por ISBN continuam usando as fontes existentes, com páginas opcionais e fallback; ausência de páginas não impede cadastro.

## CSV, exportação e privacidade

Em **Configurações → Dados → Importação CSV**, baixe o modelo de livros/leitores, escolha o CSV, confira o mapeamento e a prévia. Limites: 2 MB e 2.000 linhas. Corrija erros antes de confirmar. A validação é repetida no servidor e a transação evita importação parcial. ISBN/e-mail existentes impedem a importação da duplicata; nomes não mesclam pessoas. Livro sem ISBN é novo título; leitor sem e-mail é novo cadastro sem conta. Importar não gera convite nem promove bibliotecário.

Exportação padrão na interface: agregado mensal por status, sem nomes/turmas/títulos. Pode selecionar relatório detalhado para gestão, com dados pessoais. Ambos são administrativos, têm filtro de período/status e proteção contra fórmulas em planilhas. Pequenos grupos ainda exigem revisão antes de divulgação; não se promete anonimização formal. Empréstimos não provam leitura concluída ou sucesso pedagógico.

Em **Configurações da instituição**, revise termos e aviso de privacidade. Defina responsável, contato, finalidades e retenção; nenhum responsável legal ou prazo foi inventado. Textos ficam acessíveis em `/instituicao`, com link na tela de acesso, sem expor cadastros pessoais.

## Backup e restauração

Use **Criar e baixar backup** para gerar ZIP com banco consistente, capas/arquivos persistentes e manifesto SHA-256. Avatares estão no banco como configuração. Guarde o ZIP fora do computador com acesso restrito: contém dados pessoais e hashes de senha. Não contém segredos DPAPI; sessões são removidas e códigos invalidados na cópia portátil.

A restauração exige bibliotecário autenticado no computador servidor e confirmação da senha real da conta. Selecione o ZIP, valide, marque a confirmação e restaure. O sistema rejeita caminhos inseguros, arquivos/imagens inválidos, hashes incorretos, SQLite inconsistente ou versão incompatível. Limites: 512 MB descompactados e 20.000 arquivos. Cria backup antes de substituir, suspende operações no processo e mantém cópia exata para rollback se houver falha. Assets antigos não referenciados não são apagados automaticamente.

Ao concluir, sessões/convites/tokens anteriores deixam de valer. O vínculo protegido de recuperação local é renovado. Não é emitido código manual; se necessário use o menu nativo do desktop. Entre com uma conta do backup. A credencial SMTP é removida e precisa ser reconfigurada; confira o endereço de rede. O servidor não precisa reiniciar no fluxo normal. Não rode múltiplos processos sobre o mesmo diretório durante restauração.

## Rede e empacotamento

O desktop usa `http://127.0.0.1:5000` apenas no computador da biblioteca. O servidor HTTPS integrado atende a rede privada em `https://IP:5443`, sem domínio ou proxy obrigatório. Configurações → Biblioteca exibe os endereços, certificado público e diagnóstico. Prepare a confiança no certificado nos dispositivos e confira o firewall conforme o [guia de rede local](REDE_LOCAL.md). Minimizá-la mantém o servidor; no Windows, fechar mantém na bandeja quando disponível. Encerrar pelo menu da bandeja desliga o servidor.

`packaging/BIBI.spec` inclui os recursos e dados do DiceBear; o instalador deve copiar toda `dist/BIBI`. O build foi verificado no Windows, mas a janela nativa, instalação/desinstalação em máquina limpa, TLS da escola e entrega real do provedor SMTP precisam de homologação no ambiente de uso. Nenhum envio real ocorreu nos testes.

## Limitações técnicas explícitas

- Execução suportada nesta etapa: um processo de desktop/worker por biblioteca. O bloqueio de operações para restauração é do processo; não é coordenação distribuída.
- SMTP e consultas ISBN podem demorar conforme a rede; indisponibilidade não impede cadastro manual ou circulação.
- Backups portáteis anteriores com migrações conhecidas são atualizados em cópia isolada, com preservação do banco recebido antes da migração. Backups com versões desconhecidas ou mais novas são rejeitados. O banco legado é atualizado na abertura; um arquivo `.db` cru não é tratado como ZIP restaurável.
- Proteção DPAPI é específica do usuário Windows. O fallback para desenvolvimento fora do Windows usa arquivo com permissão restrita, sem alegar criptografia equivalente.
- A integração real de IA, chatbot, decisões automáticas e resultados acadêmicos continuam fora desta etapa. Nenhum SDK, chave ou serviço de IA foi criado.

Consulte [REFINO_INTERFACE.md](REFINO_INTERFACE.md) para o inventário dos formulários centralizados e a verificação da interface.
