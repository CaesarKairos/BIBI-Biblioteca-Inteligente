window.addEventListener('load',async()=>{const id=new URLSearchParams(location.search).get('livro');if(id&&/^\d+$/.test(id)){const r=await apiFetch('/api/livros/'+id);verDetalhes(await r.json());}});
function oferecerAcessoLeitor(id) {
    const toast=textElement('div','','toast');toast.append(textElement('p','Empréstimo registrado. O leitor pode ativar uma conta quando desejar.'));
    const link=textElement('a','Gerenciar convite');link.href='/leitores/contas?leitor='+id;toast.append(link);document.getElementById('toast-container').append(toast);setTimeout(()=>toast.remove(),15000);
}
const originalDetalhes=verDetalhes;
verDetalhes=function(livro) {
    originalDetalhes(livro);
    document.getElementById('reader-book-actions')?.remove();
    const area=textElement('section','','reader-book-actions');area.id='reader-book-actions';
    const action=(label,path)=>{const button=textElement('button',label,'btn-primary btn-small');button.type='button';button.onclick=async()=>{button.disabled=true;try{await apiFetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});showToast('Salvo na sua conta.','success');}finally{button.disabled=false;}};return button;};
    if(!isAdminGlobal) {
        area.append(action('Quero ler','/api/minha-conta/quero-ler/'+livro.id));
        const read=action('Marcar como lido','/api/minha-conta/lidos/'+livro.id);
        let marked=false;
        read.onclick=async()=>{read.disabled=true;try{await apiFetch('/api/minha-conta/lidos/'+livro.id,{method:marked?'DELETE':'POST'});marked=!marked;read.textContent=marked?'Desmarcar como lido':'Marcar como lido';read.setAttribute('aria-pressed',String(marked));showToast(marked?'Livro marcado como lido.':'Registro de leitura removido.','success');}finally{read.disabled=false;}};
        area.append(read);
        apiFetch('/api/minha-conta/lidos').then(r=>r.json()).then(rows=>{if(read.isConnected){marked=rows.some(row=>row.id===livro.id);read.textContent=marked?'Desmarcar como lido':'Marcar como lido';read.setAttribute('aria-pressed',String(marked));}});
        if(Number(livro.disponivel)<=0) area.append(action('Reservar este título','/api/minha-conta/reservas/'+livro.id));
        const form=document.createElement('form');form.className='book-review-form';
        const label=textElement('fieldset','','review-rating');label.append(textElement('legend','Sua avaliação'));
        let rating=0;
        const updateStars=value=>{rating=value;label.querySelectorAll('label').forEach((item,index)=>item.classList.toggle('is-filled',index<value));};
        for(let i=1;i<=5;i++){const item=textElement('label','','review-star');const input=document.createElement('input');input.type='radio';input.name='estrelas';input.value=i;input.required=true;input.setAttribute('aria-label',`${i} ${i===1?'estrela':'estrelas'}`);input.onchange=()=>updateStars(i);const icon=textElement('span','★');icon.setAttribute('aria-hidden','true');item.append(input,icon);label.append(item);}
        const comment=document.createElement('textarea');comment.name='comentario';comment.maxLength=2000;comment.placeholder='Seu comentário sobre a obra';comment.setAttribute('aria-label','Comentário sobre a obra');
        const save=textElement('button','Salvar avaliação','btn-primary btn-small');const state=textElement('p','','review-state');state.setAttribute('role','status');form.append(label,comment,save,state);
        form.onsubmit=async event=>{event.preventDefault();save.disabled=true;try{await apiFetch('/api/minha-conta/avaliacoes/'+livro.id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({estrelas:rating,comentario:comment.value})});if(form.isConnected)verDetalhes(livro);showToast('Avaliação salva. Conteúdo sinalizado passa por revisão.','success');}finally{save.disabled=false;}};
        area.append(form);
        apiFetch('/api/minha-conta/avaliacoes').then(r=>r.json()).then(rows=>{
            const own=rows.find(row=>row.livro_id===livro.id);
            if(own&&form.isConnected){
                label.querySelector(`input[value="${own.estrelas}"]`).checked=true;updateStars(own.estrelas);comment.value=own.comentario;save.textContent='Atualizar avaliação';
                state.textContent=own.estado==='publicado'?'Sua opinião está publicada.':own.estado==='revisao'?'Sua opinião aguarda revisão da biblioteca.':'Sua opinião foi ocultada pela biblioteca.';
                const remove=textElement('button','Excluir minha avaliação','btn-small');remove.type='button';
                remove.onclick=async()=>{remove.disabled=true;try{await apiFetch('/api/minha-conta/avaliacoes/'+livro.id,{method:'DELETE'});if(form.isConnected)verDetalhes(livro);showToast('Sua avaliação foi excluída.','success');}finally{remove.disabled=false;}};
                form.append(remove);
            }
        });
    }
    const reviews=textElement('div','Carregando opiniões…');area.append(reviews);document.getElementById('info-livro').append(area);
    apiFetch('/api/minha-conta/avaliacoes/'+livro.id).then(r=>r.json()).then(rows=>{reviews.replaceChildren(textElement('h3','Opiniões sobre a obra'));if(!rows.length)reviews.append(textElement('p','Ainda não há opiniões publicadas.'));rows.forEach(r=>{const card=textElement('article','','book-review-card');const stars=textElement('span','★'.repeat(r.estrelas)+'☆'.repeat(5-r.estrelas),'review-stars');stars.setAttribute('aria-label',r.estrelas+' de 5 estrelas');card.append(stars,textElement('small','Leitor da biblioteca'),textElement('p',r.comentario||'Avaliação sem comentário.'));reviews.append(card);});});
};

window.addEventListener('load',()=>{const section=location.hash.slice(1);if(['dash','acervo','emp','age','lei'].includes(section))tab(section);});
