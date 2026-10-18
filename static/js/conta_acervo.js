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
        if(Number(livro.disponivel)<=0) area.append(action('Reservar este título','/api/minha-conta/reservas/'+livro.id));
        const form=document.createElement('form');const label=textElement('label','Sua avaliação');const stars=document.createElement('select');stars.name='estrelas';stars.setAttribute('aria-label','Nota de uma a cinco estrelas');
        for(let i=1;i<=5;i++){const option=textElement('option',`${i} ${i===1?'estrela':'estrelas'}`);option.value=i;stars.append(option);}label.append(stars);
        const comment=document.createElement('textarea');comment.name='comentario';comment.maxLength=2000;comment.placeholder='Seu comentário sobre a obra';comment.setAttribute('aria-label','Comentário sobre a obra');
        const save=textElement('button','Salvar avaliação','btn-primary btn-small');form.append(label,comment,save);
        form.onsubmit=async event=>{event.preventDefault();save.disabled=true;try{await apiFetch('/api/minha-conta/avaliacoes/'+livro.id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({estrelas:Number(stars.value),comentario:comment.value})});showToast('Avaliação salva. Conteúdo sinalizado passa por revisão.','success');}finally{save.disabled=false;}};
        area.append(form);
        apiFetch('/api/minha-conta/avaliacoes').then(r=>r.json()).then(rows=>{
            const own=rows.find(row=>row.livro_id===livro.id);
            if(own&&form.isConnected){
                stars.value=own.estrelas;comment.value=own.comentario;
                const remove=textElement('button','Excluir minha avaliação','btn-small');remove.type='button';
                remove.onclick=async()=>{remove.disabled=true;try{await apiFetch('/api/minha-conta/avaliacoes/'+livro.id,{method:'DELETE'});if(form.isConnected)verDetalhes(livro);showToast('Sua avaliação foi excluída.','success');}finally{remove.disabled=false;}};
                form.append(remove);
            }
        });
    }
    const reviews=textElement('div','Carregando opiniões…');area.append(reviews);document.getElementById('info-livro').append(area);
    apiFetch('/api/minha-conta/avaliacoes/'+livro.id).then(r=>r.json()).then(rows=>{reviews.replaceChildren(textElement('h3','Opiniões sobre a obra'));if(!rows.length)reviews.append(textElement('p','Ainda não há opiniões publicadas.'));rows.forEach(r=>reviews.append(textElement('p',`${r.estrelas}/5 — ${r.comentario}`)));});
};

window.addEventListener('load',()=>{const section=location.hash.slice(1);if(['dash','acervo','emp','age','lei'].includes(section))tab(section);});
