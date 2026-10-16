const onboarding=document.getElementById('profile-content').dataset.onboarding==='true';
let savedAvatar, savedAvatarImage, draftAvatar, avatarFields, previewSequence=0;
const avatarCache=new Map();
const avatarQueue=[];let activePreviews=0;
function avatarImage(config,priority=false){
 const key=JSON.stringify(config);
 if(!avatarCache.has(key))avatarCache.set(key,new Promise((resolve,reject)=>{avatarQueue[priority?'unshift':'push']({config,resolve,reject});pumpAvatars();}).catch(error=>{avatarCache.delete(key);throw error;}));
 return avatarCache.get(key);
}
function pumpAvatars(){while(activePreviews<4&&avatarQueue.length){const job=avatarQueue.shift();activePreviews++;accountApi('/api/minha-conta/avatar/previa','POST',job.config).then(r=>job.resolve(r.imagem),job.reject).finally(()=>{activePreviews--;pumpAvatars();});}}
async function previewAvatar() {
 const sequence=++previewSequence, status=document.getElementById('avatar-status');status.textContent='Atualizando prévia…';document.getElementById('save-avatar').disabled=true;
 try{const image=await avatarImage(structuredClone(draftAvatar),true);if(sequence===previewSequence){document.getElementById('preview-avatar').src=image;status.textContent='';}}
 catch(error){if(sequence===previewSequence)status.textContent='Não foi possível atualizar a prévia. Tente outra vez.';}
 finally{if(sequence===previewSequence)document.getElementById('save-avatar').disabled=false;}
}
async function loadProfile() {
    const profile=await accountApi('/api/minha-conta');
    document.getElementById('profile-info').textContent=`${profile.papel==='bibliotecario'?'Bibliotecário · '+profile.email:(profile.tipo || 'Leitor')+(profile.sala?' · Turma '+profile.sala:'')}`;
    if(document.getElementById('email-state')) document.getElementById('email-state').textContent=profile.email_verificado?'E-mail verificado.':'E-mail não verificado. Sua conta está ativa; a recuperação de senha pode ser feita presencialmente na biblioteca.';
    const avatar=await accountApi('/api/minha-conta/avatar'); savedAvatar=avatar.config; avatarFields=avatar.opcoes;
    document.getElementById('saved-avatar').src=savedAvatarImage=avatar.imagem;
    if(onboarding){document.getElementById('edit-avatar').click();return;}
    if(profile.papel!=='leitor'||!profile.leitor_id) return;
    await loadFavorites();
    document.getElementById('profile-history').replaceChildren();
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
            if(path==='emprestimos' && (row.encerramento || row.status==='Devolvido')) document.getElementById('profile-history').append(card);
            else container.append(card);
        }
    }
}
function markAvatarChoices(){
 document.querySelectorAll('[data-avatar-value]').forEach(button=>{
 const name=button.dataset.avatarField,value=button.dataset.avatarValue;
 const selected=name==='glassesVariant'&&value==='none'?draftAvatar.opcoes.glassesProbability===0:draftAvatar.opcoes[name]===value&&(name!=='glassesVariant'||draftAvatar.opcoes.glassesProbability!==0);
 button.setAttribute('aria-pressed',String(selected));
 });
}
async function openAvatarEditor(){
 draftAvatar=structuredClone(savedAvatar);document.getElementById('preview-avatar').src=savedAvatarImage;
 const initialPreview=previewAvatar();
 const fields=document.getElementById('avatar-options');fields.replaceChildren();
 document.querySelector('.profile-hero').hidden=true;document.getElementById('avatar-editor').hidden=false;
 const comparison={...savedAvatar,opcoes:{...savedAvatar.opcoes,eyesProbability:100,mouthProbability:100,eyebrowsProbability:100,glassesProbability:0}};
 const labels={eyesVariant:'Olhos',mouthVariant:'Boca',eyebrowsVariant:'Sobrancelhas',glassesVariant:'Óculos',backgroundColor:'Fundo',eyesColor:'Cor dos olhos',glassesColor:'Cor dos óculos',inkColor:'Traços',lipsColor:'Lábios',scleraColor:'Branco dos olhos',teethColor:'Dentes',throatColor:'Interior da boca',tongueColor:'Língua',uvulaColor:'Detalhe da boca'};
 for(const name of ['eyesVariant','mouthVariant','eyebrowsVariant','glassesVariant']){
  const group=accountText('section','','avatar-group');const heading=accountText('h3',labels[name]);group.append(heading);const grid=accountText('div','','avatar-choices');grid.setAttribute('role','group');grid.setAttribute('aria-label',labels[name]);group.append(grid);fields.append(group);
  const values=[...(name==='glassesVariant'?['none']:[]),...avatarFields[name].values];
  values.forEach((value,index)=>{
   const label=value==='none'?'Sem óculos':`${labels[name]} ${name==='glassesVariant'?index:index+1}`;
   const button=accountButton(label,async()=>{
    if(value==='none')draftAvatar.opcoes.glassesProbability=0;
    else {draftAvatar.opcoes[name]=value;draftAvatar.opcoes[name.replace('Variant','Probability')]=100;}
    markAvatarChoices();await previewAvatar();
   });button.className='avatar-choice';button.dataset.avatarField=name;button.dataset.avatarValue=value;button.setAttribute('aria-label',label);button.setAttribute('aria-busy','true');
   const img=document.createElement('img');img.alt='';img.width=72;img.height=72;button.prepend(img);grid.append(button);
   const config=structuredClone(comparison);
   if(value!=='none'){config.opcoes[name]=value;if(name==='glassesVariant')config.opcoes.glassesProbability=100;}
   avatarImage(config).then(image=>{if(button.isConnected){img.src=image;button.removeAttribute('aria-busy');}}).catch(()=>{button.removeAttribute('aria-busy');button.title='Prévia indisponível. Clique para experimentar.';});
  });
 }
 const advanced=document.createElement('details');advanced.append(accountText('summary','Cores avançadas'));
 const colorNames=['Creme','Areia','Marrom','Verde','Azul','Violeta','Terracota','Carvão','Branco'];
 const palette=['#f2e5cf','#c6a47c','#8c6248','#3d4935','#4c6b88','#7a4667','#bd6754','#202520','#ffffff'];
 for(const [name,descriptor] of Object.entries(avatarFields)){
  if(descriptor.type!=='color')continue;
  const group=accountText('section','','avatar-group');group.append(accountText('h3',labels[name]));const colors=accountText('div','','avatar-colors');colors.setAttribute('role','group');colors.setAttribute('aria-label',labels[name]);group.append(colors);
  palette.forEach((value,index)=>{const button=accountButton(`${labels[name]}: ${colorNames[index]}`,async()=>{draftAvatar.opcoes[name]=value;markAvatarChoices();await previewAvatar();});button.className='avatar-swatch';button.style.backgroundColor=value;button.dataset.avatarField=name;button.dataset.avatarValue=value;button.title=`${labels[name]}: ${colorNames[index]}`;colors.append(button);});
  const label=accountText('label','Outra cor');const custom=document.createElement('input');custom.type='color';custom.value=draftAvatar.opcoes[name]||palette[0];custom.addEventListener('input',()=>{draftAvatar.opcoes[name]=custom.value;markAvatarChoices();previewAvatar();});label.append(custom);group.append(label);
  (['backgroundColor','eyesColor','inkColor','lipsColor','glassesColor'].includes(name)?fields:advanced).append(group);
 }
 fields.append(advanced);markAvatarChoices();await initialPreview;
}
accountAction(document.getElementById('edit-avatar'),openAvatarEditor);
accountAction(document.getElementById('random-avatar'),async()=>{draftAvatar.seed=Array.from(crypto.getRandomValues(new Uint8Array(16)),b=>b.toString(16).padStart(2,'0')).join('');draftAvatar.opcoes={};markAvatarChoices();await previewAvatar();});
accountAction(document.getElementById('save-avatar'),async()=>{
 const committed=structuredClone(draftAvatar),options=document.getElementById('avatar-options');
 const controls=[document.getElementById('random-avatar'),document.getElementById('cancel-avatar')].filter(Boolean);
 options.inert=true;controls.forEach(control=>control.disabled=true);
 try{
  const result=await accountApi('/api/minha-conta/avatar','PUT',committed);savedAvatar=committed;
  document.getElementById('saved-avatar').src=savedAvatarImage=result.imagem;
  document.getElementById('avatar-editor').hidden=true;document.querySelector('.profile-hero').hidden=false;
  if(onboarding)location.assign('/app');
 }finally{options.inert=false;controls.forEach(control=>control.disabled=false);}
});
accountAction(document.getElementById('cancel-avatar'),async()=>{++previewSequence;draftAvatar=null;document.getElementById('avatar-editor').hidden=true;document.querySelector('.profile-hero').hidden=false;document.getElementById('edit-avatar').focus();});
loadProfile().catch(e=>document.getElementById('account-status').textContent=e.message);

accountAction(document.getElementById('suggested-avatar'),async()=>{await accountApi('/api/minha-conta/avatar','PUT',savedAvatar);location.assign('/app');});
let favorites=[];
async function loadFavorites(){
 favorites=await accountApi('/api/minha-conta/favoritos');
 const list=document.getElementById('profile-favorites');list.replaceChildren();
 const save=async ids=>{await accountApi('/api/minha-conta/favoritos','PUT',{livros:ids});await loadFavorites();};
 favorites.forEach((book,index)=>{const card=accountText('article','','profile-row');const link=accountText('a',book.nome+(book.arquivado?' · Arquivado':''));link.href='/app?livro='+book.id;const image=document.createElement('img');image.src=book.capa_url || '/static/images/placeholder.png';image.alt='';image.className='favorite-cover';link.prepend(image);card.append(link);
 card.append(accountButton('Remover',()=>save(favorites.filter(b=>b.id!==book.id).map(b=>b.id))));
 if(index>0)card.append(accountButton('Mover para antes',()=>{const ids=favorites.map(b=>b.id);[ids[index-1],ids[index]]=[ids[index],ids[index-1]];return save(ids);}));list.append(card);});
 const books=await accountApi('/api/livros');const select=document.getElementById('favorite-book');select.replaceChildren();books.filter(b=>!b.arquivado&&!favorites.some(f=>f.id===b.id)).forEach(b=>{const o=accountText('option',b.titulo);o.value=b.id;select.append(o);});
}
accountForm('favorite-form',async()=>{const id=Number(document.getElementById('favorite-book').value);await accountApi('/api/minha-conta/favoritos','PUT',{livros:[...favorites.map(b=>b.id),id]});await loadFavorites();});
