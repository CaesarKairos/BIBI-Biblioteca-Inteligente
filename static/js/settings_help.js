(() => {
    const descriptions = {
        '#settings-theme': 'Escolha entre as cores claras e escuras do BIBI. A preferência fica vinculada à sua conta e é salva na hora.',
        '[data-setting="campoDescricaoVisivel"]': 'Mostra o campo de descrição ao cadastrar ou editar um livro.',
        '[data-setting="campoTemasVisivel"]': 'Mostra o campo de temas e assuntos ao cadastrar ou editar um livro.',
        '[data-setting="campoAnoVisivel"]': 'Mostra o ano de publicação no cadastro e na edição dos livros.',
        '[data-setting="campoCategoriaVisivel"]': 'Mostra a seleção de categoria no cadastro e na edição dos livros.',
        '[data-setting="bloquearExcluirLivro"]': 'Oculta o botão de excluir nos detalhes do livro. Os livros já cadastrados permanecem no acervo.',
        '[data-setting="campoNumeroUsuario"]': 'Exibe e exige o telefone do estudante no formulário de empréstimo rápido.',
        '[data-setting="mostrarColunaAula"]': 'Exibe a coluna com a numeração dos horários: 1ª aula, 2ª aula e assim por diante.',
        '[data-setting="obrigar_localizacao_livro"]': 'Exige informar a prateleira ou localização física ao cadastrar um livro.',
        '[data-setting="bloquear_excluir_agendamento"]': 'Impede excluir agendamentos já registrados. Novos agendamentos continuam disponíveis.',
        '[data-setting="exigir_senha_agendamento"]': 'Solicita a senha real da conta para registrar um agendamento. Alterar esta opção também exige sua senha.',
        '[data-setting="exigir_senha_emprestimo"]': 'Solicita a senha real da conta para registrar um empréstimo. Alterar esta opção também exige sua senha.',
        '[data-setting="bloquear_email"]': 'Suspende os envios de e-mail da instalação. As notificações internas continuam disponíveis.',
        '#password-form [name="senha_atual"]': 'Informe a senha que você usa atualmente para entrar no BIBI.',
        '#password-form [name="senha"]': 'Use de 12 a 128 caracteres. Após a alteração, será necessário entrar novamente.',
        '#password-form [name="confirmacao"]': 'Repita a nova senha para evitar erros de digitação.',
        '#verify-email-form [name="email"]': 'Informe o endereço atual para verificá-lo ou um novo endereço para trocar seu e-mail de acesso.',
        '#verify-email-form [name="senha_atual"]': 'Confirma que você autoriza o envio do código de verificação.',
        '#confirm-email-form [name="codigo"]': 'Digite o código enviado ao endereço que deseja verificar.',
        '#confirm-email-form [name="email"]': 'Use o mesmo endereço informado ao solicitar o código.',
        '#institution-form [name="biblioteca_nome"]': 'Nome que identifica esta biblioteca nas informações institucionais.',
        '#network-address': 'Endereço real do computador servidor, identificado automaticamente. Use-o nos dispositivos da rede; o acesso é protegido pelo HTTPS integrado ao BIBI.',
        '#institution-form [name="termos_uso"]': 'Regras de uso da biblioteca, responsabilidades e condições de acesso, visíveis na página institucional.',
        '#institution-form [name="aviso_privacidade"]': 'Informe quem cuida dos dados, como entrar em contato, as finalidades de uso e os prazos de retenção.',
        '#settings-lessons': 'Quantidade de horários exibidos por dia e período na Agenda, de 1 a 20. Use Salvar quantidade para aplicar.',
        '#rules-form [name="retirada_horas"]': 'Tempo para o leitor retirar um exemplar separado. Defina este prazo para habilitar as reservas.',
        '#invite-reader': 'Selecione o leitor que receberá o convite ou o código de recuperação. Confira sua identidade e seu e-mail.',
        '#invite-form [name="finalidade"]': 'Ativação cria o acesso pessoal do leitor; recuperação permite que ele defina uma nova senha para uma conta existente.',
        '#managed-account': 'Selecione a conta cujo acesso será alterado. Confira o nome e o papel antes de confirmar.',
        '#access-form-admin [name="papel"]': 'Leitores acessam seus próprios dados. Bibliotecários também podem administrar a biblioteca.',
        '#access-form-admin [name="ativa"]': 'Bloquear impede o acesso à conta. Reativar permite que a pessoa volte a entrar.',
        '#access-form-admin [name="motivo"]': 'Explique a alteração. O motivo será registrado na auditoria.',
        '#access-form-admin [name="senha_atual"]': 'Informe a senha da sua própria conta para autorizar a mudança de acesso.',
        '#smtp-form [name="smtp_host"]': 'Servidor de envio informado pelo provedor do e-mail remetente, como smtp.gmail.com.',
        '#smtp-form [name="smtp_port"]': 'Use a porta indicada pelo provedor: 587 com STARTTLS ou 465 com TLS.',
        '#smtp-form [name="email_organizacao"]': 'Endereço que enviará os convites e avisos da biblioteca.',
        '#smtp-form [name="email_app_password"]': 'Credencial de envio fornecida pelo provedor. Deixe vazio para manter a credencial já salva.',
        '#smtp-form [name="remover_credencial"]': 'Apaga a credencial de envio ao salvar o remetente. Os envios precisarão ser configurados novamente.',
        '#smtp-form [name="senha_atual"]': 'Necessária somente para autorizar a remoção da credencial salva.',
        '#occurrence-book': 'Livro ao qual a perda, o dano, o reparo ou a baixa se refere.',
        '#occurrence-form [name="tipo"]': 'Observação apenas registra o dano; reparo retira exemplares livres e retorno os devolve. Baixa e perda reduzem o estoque.',
        '#occurrence-form [name="quantidade"]': 'Número de exemplares envolvidos nesta ocorrência.',
        '#occurrence-form [name="emprestimo_id"]': 'Preencha para vincular uma perda ou observação a um empréstimo. Para exemplares livres, deixe vazio.',
        '#occurrence-form [name="observacao"]': 'Descreva o ocorrido para preservar o contexto no histórico da biblioteca.',
        '#csv-kind': 'Escolha o cadastro que será importado. Cada tipo possui seu próprio modelo de colunas.',
        '#csv-file': 'Selecione um CSV com até 2 MB e 2.000 linhas. A prévia permite conferir os dados antes de importar.',
        '#csv-mapping select': 'Escolha a coluna do arquivo que contém este dado. Confira o resultado na prévia antes de confirmar.',
        '#dados form[method="get"] [name="formato"]': 'O agregado reúne totais mensais sem nomes. O detalhado inclui dados pessoais para uso administrativo.',
        '#dados form[method="get"] [name="inicio"]': 'Inclui empréstimos a partir desta data. Deixe vazio para não definir uma data inicial.',
        '#dados form[method="get"] [name="fim"]': 'Inclui empréstimos até esta data. Deixe vazio para não definir uma data final.',
        '#dados form[method="get"] [name="status"]': 'Limita o relatório à situação escolhida ou inclui todas as situações.',
        '#restore-password': 'Sua senha atual autoriza validar e restaurar o backup nesta instalação.',
        '#restore-file': 'Selecione o arquivo ZIP de backup criado pelo BIBI. A validação confere o formato e os arquivos antes da restauração.',
        '#restore-confirm': 'Confirma a substituição dos dados atuais pelo backup validado. Sessões e códigos anteriores serão invalidados.',
        '#download-backup': 'Cria uma cópia consistente do banco e dos arquivos persistentes para baixar. Guarde o ZIP em local protegido.',
        '#refresh-health': 'Consulta o estado atual desta instalação, sem fazer testes de conexão com serviços externos.',
        '#hide-invite': 'Oculta o código nesta tela sem revogá-lo. Use após entregá-lo ao leitor.',
        '#renewal-list input': 'Informe por que o pedido de renovação será recusado.',
        '#moderation-list input': 'Registre o motivo para publicar ou ocultar o comentário; ele acompanha a decisão de moderação.',
    };
    for (const category of ['estudante','professor']) {
        for (const [key,description] of Object.entries({
            maximo:'Quantidade máxima de exemplares que uma pessoa desta categoria pode manter emprestados ao mesmo tempo.',
            prazo:'Prazo de empréstimo em dias para esta categoria. Salvar não altera os vencimentos já registrados.',
            renovacoes:'Número máximo de renovações permitidas por empréstimo. Zero impede renovações.',
            bloquear_atraso:'Impede novos empréstimos e renovações para pessoas desta categoria com devoluções em atraso.',
        })) descriptions[`#rules-form [name="${category}_${key}"]`]=description;
    }
    const formNotes = {
        'verify-email-form':'O endereço de acesso só é atualizado após a confirmação do código. Sem envio de e-mail configurado, procure o bibliotecário.',
        'confirm-email-form':'Confirmar o código verifica o endereço e encerra as sessões anteriores da conta.',
        'institution-form':'Use Salvar instituição para aplicar as alterações destes campos.',
        'rules-form':'Use Salvar regras para aplicar os limites e prazos de cada categoria.',
        'invite-form':'Gerar código permite a entrega presencial. Enviar convite usa o remetente configurado. Revogar invalida os códigos ainda abertos deste leitor.',
        'access-form-admin':'A confirmação encerra as sessões anteriores da conta alterada. O último bibliotecário ativo não pode ser bloqueado nem perder seu papel.',
        'smtp-form':'Salve o remetente antes de testar. O teste envia uma mensagem ao e-mail da conta bibliotecária que o solicitou.',
        'occurrence-form':'Registrar ocorrência grava o histórico e ajusta o estoque conforme o tipo escolhido.',
        'csv-form':'Pré-visualizar não grava cadastros. Confira o mapeamento e os erros; só Confirmar importação adiciona os registros.',
        'restore-form':'Validar backup não substitui dados. Restaurar exige um arquivo validado e a confirmação acima; ao concluir, você voltará ao login.',
    };
    const groupNotes = {
        'renewal-list':'Revise os pedidos dos leitores. Aprovar estende o empréstimo conforme as regras; recusar exige informar o motivo.',
        'audit-list':'Histórico das operações administrativas: quando ocorreram, qual conta agiu e o resultado registrado.',
    };
    let sequence=0;
    window.descreverConfiguracoes=(root=document.getElementById('settings-content'))=>{
        if(!root)return;
        for(const [selector,text] of Object.entries(descriptions)) {
            root.querySelectorAll(selector).forEach(control=>{
                if(control.dataset.settingsHelp)return;
                const help=document.createElement('small');help.className='settings-help';help.id='settings-help-'+(++sequence);help.textContent=text;
                const label=control.closest('label');
                if(label&&!control.hasAttribute('aria-label')){
                    const title=[...label.childNodes].filter(node=>node.nodeType===Node.TEXT_NODE).map(node=>node.textContent).join(' ').trim();
                    if(title)control.setAttribute('aria-label',title);
                }
                if(label?.classList.contains('config-toggle-row')){
                    const copy=document.createElement('span');copy.className='config-toggle-copy';
                    [...label.childNodes].filter(node=>node.nodeType===Node.TEXT_NODE).forEach(node=>copy.append(node));
                    copy.append(help);label.prepend(copy);
                }else if(label)label.append(help);
                else control.after(help);
                control.dataset.settingsHelp=help.id;
                control.setAttribute('aria-describedby',[control.getAttribute('aria-describedby'),help.id].filter(Boolean).join(' '));
                const wrapper=control.nextElementSibling;
                if(control.tagName==='SELECT'&&wrapper?.classList.contains('custom-select')){
                    wrapper.dataset.descriptionId=help.id;wrapper.querySelector('button')?.setAttribute('aria-describedby',help.id);
                }
            });
        }
        for(const [id,text] of Object.entries(formNotes)){
            const form=root.querySelector('#'+id);
            if(!form||form.querySelector('.settings-form-help'))continue;
            const note=document.createElement('p');note.className='settings-form-help';note.textContent=text;form.append(note);
        }
        for(const [id,text] of Object.entries(groupNotes)){
            const group=root.querySelector('#'+id);
            if(!group||group.previousElementSibling?.dataset.settingsGroupHelp===id)continue;
            const note=document.createElement('p');note.dataset.settingsGroupHelp=id;note.textContent=text;group.before(note);
        }
    };
})();
