let savedAvatar, draftAvatar, avatarFields, previewSequence=0;
async function previewAvatar() {
    const sequence=++previewSequence;
    const result=await accountApi('/api/minha-conta/avatar/previa','POST',draftAvatar);
    if(sequence===previewSequence) document.getElementById('preview-avatar').src=result.imagem;
}
async function loadProfile() {
    const profile=await accountApi('/api/minha-conta');
    document.getElementById('profile-info').textContent=`${profile.nome} · ${profile.email} · ${profile.papel}${profile.tipo?' · '+profile.tipo:''}`;
    document.getElementById('email-state').textContent=profile.email_verificado?'E-mail verificado.':'E-mail não verificado. Sua conta está ativa; a recuperação de senha pode ser feita presencialmente na biblioteca.';
    const avatar=await accountApi('/api/minha-conta/avatar'); savedAvatar=avatar.config; avatarFields=avatar.opcoes;
    document.getElementById('saved-avatar').src=avatar.imagem;
    if(!profile.leitor_id) return;
    const sections=[['emprestimos','profile-loans'],['quero-ler','profile-wishes'],['reservas','profile-reservations'],['notificacoes','profile-notifications'],['avaliacoes','profile-reviews']];
    for(const [path,id] of sections) {
        const rows=await accountApi('/api/minha-conta/'+path), container=document.getElementById(id); container.replaceChildren();
        if(!rows.length) container.append(accountText('p','Nenhum registro nesta seção.'));
        for(const row of rows) {
            const card=accountText('article','','profile-row');
            if(path==='emprestimos') {
                card.append(accountText('strong',row.livro),accountText('p',`${row.encerramento || row.status} · Prazo: ${row.data_vencimento}${row.pedido?' · Renovação: '+row.pedido:''}`));
                if(['Aprovado','Atrasado'].includes(row.status)&&!row.encerramento&&row.pedido!=='pendente') card.append(accountButton('Solicitar renovação',async()=>{const r=await accountApi(`/api/minha-conta/emprestimos/${row.id}/renovacao`,'POST',{});document.getElementById('account-status').textContent=r.mensagem;await loadProfile();}));
            } else if(path==='quero-ler') {
                card.append(accountText('strong',row.nome),accountText('p',row.arquivado?'Arquivado':`${row.disponivel} exemplares disponíveis`));
                const link=accountText('a','Abrir detalhes');link.href='/app?livro='+row.id;card.append(link);
                card.append(accountButton('Remover',async()=>{await accountApi('/api/minha-conta/quero-ler/'+row.id,'DELETE');await loadProfile();}));
                if(!row.arquivado&&row.disponivel===0) card.append(accountButton('Reservar',async()=>{await accountApi('/api/minha-conta/reservas/'+row.id,'POST',{});await loadProfile();}));
            } else if(path==='reservas') {
                card.append(accountText('strong',row.nome),accountText('p',row.estado==='fila'?`Posição na fila: ${row.posicao}`:row.estado==='retirada'?`Retire até ${new Date(row.expira*1000).toLocaleString('pt-BR')}`:row.estado));
                if(['fila','retirada'].includes(row.estado)) card.append(accountButton('Cancelar reserva',async()=>{await accountApi('/api/minha-conta/reservas/'+row.id,'DELETE');await loadProfile();}));
            } else if(path==='notificacoes') {
                card.append(accountText('p',row.mensagem));
                if(!row.lida) card.append(accountButton('Marcar como lida',async()=>{await accountApi(`/api/minha-conta/notificacoes/${row.id}/ler`,'POST',{});await loadProfile();}));
            } else {
                card.append(accountText('strong',`${row.nome} · ${row.estrelas}/5`),accountText('p',row.comentario),accountText('small',`${row.estado}${row.motivo?' · '+row.motivo:''}`));
                const link=accountText('a','Editar no livro');link.href='/app?livro='+row.livro_id;card.append(link);
                card.append(accountButton('Remover avaliação',async()=>{await accountApi('/api/minha-conta/avaliacoes/'+row.livro_id,'DELETE');await loadProfile();}));
            }
            container.append(card);
        }
    }
}
accountAction(document.getElementById('edit-avatar'),async()=>{
    draftAvatar=structuredClone(savedAvatar); const fields=document.getElementById('avatar-options');fields.replaceChildren();
    const labels={eyebrowsVariant:'Sobrancelhas',eyesVariant:'Olhos',glassesVariant:'Óculos',mouthVariant:'Boca',backgroundColor:'Fundo',eyesColor:'Cor dos olhos',glassesColor:'Cor dos óculos',inkColor:'Traços',lipsColor:'Lábios',scleraColor:'Esclera',teethColor:'Dentes',throatColor:'Garganta',tongueColor:'Língua',uvulaColor:'Úvula'};
    for(const [name,descriptor] of Object.entries(avatarFields)) {
        if(name.endsWith('Probability')&&name!=='glassesProbability') continue;
        const label=accountText('label',labels[name] || 'Óculos: frequência (%)'); let control;
        if(descriptor.type==='enum') {
            control=document.createElement('select');const auto=accountText('option','Aleatório');auto.value='';control.append(auto);
            descriptor.values.forEach(value=>{const option=accountText('option',value.replace('variant','Opção '));option.value=value;control.append(option);});
        } else { control=document.createElement('input');control.type=descriptor.type==='color'?'color':'number';control.min=0;control.max=100; }
        control.value=draftAvatar.opcoes[name] ?? (descriptor.type==='color'?'#c6a47c':descriptor.type==='number'?0:'');
        control.addEventListener('change',async()=>{if(control.value==='') delete draftAvatar.opcoes[name];else draftAvatar.opcoes[name]=descriptor.type==='number'?Number(control.value):control.value;await previewAvatar();});
        control.dataset.avatarOption=name;
        label.append(control);fields.append(label);
        if(descriptor.type==='enum') {
            const choices=document.createElement('details');const summary=accountText('summary','Escolher visualmente');choices.append(summary);label.append(choices);
            choices.addEventListener('toggle',async()=>{
                if(!choices.open||choices.dataset.loaded)return;choices.dataset.loaded='true';
                const grid=accountText('div','','avatar-choices');choices.append(grid);
                for(const value of descriptor.values) {
                    if(!draftAvatar||!grid.isConnected)break;
                    const candidate={...draftAvatar,opcoes:{...draftAvatar.opcoes,[name]:value}};
                    if(name==='glassesVariant')candidate.opcoes.glassesProbability=100;
                    try {
                        const r=await accountApi('/api/minha-conta/avatar/previa','POST',candidate);
                        if(!draftAvatar||!grid.isConnected)break;
                        const button=accountButton(value.replace('variant','Opção '),async()=>{draftAvatar.opcoes[name]=value;control.value=value;if(name==='glassesVariant'){draftAvatar.opcoes.glassesProbability=100;document.querySelector('[data-avatar-option=glassesProbability]').value=100;}await previewAvatar();});
                        const img=document.createElement('img');img.src=r.imagem;img.alt='';img.width=56;img.height=56;button.prepend(img);grid.append(button);
                    }catch(error){document.getElementById('account-status').textContent=error.message;break;}
                }
            });
        }
    }
    document.getElementById('avatar-editor').hidden=false;await previewAvatar();
});
accountAction(document.getElementById('random-avatar'),async()=>{draftAvatar.seed=Array.from(crypto.getRandomValues(new Uint8Array(16)),b=>b.toString(16).padStart(2,'0')).join('');draftAvatar.opcoes={};document.querySelectorAll('[data-avatar-option]').forEach(control=>{control.value=control.tagName==='SELECT'?'':control.type==='color'?'#c6a47c':0;});document.querySelectorAll('#avatar-options details').forEach(d=>{d.open=false;delete d.dataset.loaded;d.querySelector('.avatar-choices')?.remove();});await previewAvatar();});
accountAction(document.getElementById('save-avatar'),async()=>{const r=await accountApi('/api/minha-conta/avatar','PUT',draftAvatar);savedAvatar=structuredClone(draftAvatar);document.getElementById('saved-avatar').src=r.imagem;document.getElementById('avatar-editor').hidden=true;});
accountAction(document.getElementById('cancel-avatar'),async()=>{++previewSequence;draftAvatar=null;document.getElementById('avatar-editor').hidden=true;});
accountForm('password-form',async data=>{await accountApi('/api/minha-conta/senha','POST',data);location.assign('/acesso');});
accountForm('verify-email-form',async data=>{const r=await accountApi('/api/minha-conta/email/enviar','POST',data);document.getElementById('account-status').textContent=r.mensagem;});
accountForm('confirm-email-form',async data=>{await accountApi('/api/minha-conta/email/confirmar','POST',data);location.assign('/acesso');});
loadProfile().catch(e=>document.getElementById('account-status').textContent=e.message);
