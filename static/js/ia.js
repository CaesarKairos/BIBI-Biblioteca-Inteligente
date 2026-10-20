/* IA na interface existente. Texto remoto sempre renderizado com textContent. */
(() => {
    window.bibiAIState={disponivel:false,estado:'verificando'};
    let stateRequest=0,statePending=0;
    window.refreshBibiAvailability=async(force=true)=>{
        if(!force&&statePending)return;
        statePending++;
        const sequence=++stateRequest;let data;
        try{data=await accountApi('/api/minha-conta/ia/estado');}catch{data={disponivel:false,estado:'indisponivel'};}finally{statePending--;}
        if(sequence!==stateRequest)return;
        const changed=window.bibiAIState.disponivel!==data.disponivel;
        window.bibiAIState=data;
        window.updateBibiChatVisibility();
        if(!data.disponivel){document.getElementById('prateleira-bibi')?.remove();document.querySelector('.bibi-insights')?.remove();window.abortBibiResponse?.();}
        if(data.disponivel){
            const privacy=document.getElementById('bibi-privacy');if(privacy)privacy.textContent=`${data.provedor}. ${data.aviso}`;
            if(changed&&typeof aplicarFiltroAcervo==='function')aplicarFiltroAcervo();
            window.refreshBibiInsights?.();
        }
        window.dispatchEvent(new CustomEvent('bibi-ai-state',{detail:data}));
    };
    window.updateBibiChatVisibility=()=>{
        const selected=typeof livroSelecionado!=='undefined'&&livroSelecionado;
        const chat=document.getElementById('bibi-chat');
        if(chat)chat.hidden=!window.bibiAIState.disponivel||Boolean(selected);
        if(selected)window.abortBibiResponse?.();
    };
    window.refreshBibiAvailability();
    setInterval(()=>{if(!document.hidden)window.refreshBibiAvailability(false);},5000);
    window.addEventListener('focus',()=>window.refreshBibiAvailability(false));
    const form=document.getElementById('bibi-chat-form');
    if(!form)return;
    const messages=document.getElementById('bibi-messages'),status=document.getElementById('bibi-status'),suggestions=document.getElementById('bibi-suggestions');
    let conversation=null,controller=null;
    let followTail=true;
    messages.addEventListener('scroll',()=>{followTail=messages.scrollHeight-messages.scrollTop-messages.clientHeight<50;});
    form.elements.mensagem.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();form.requestSubmit();}});
    function questions(){
        window.updateBibiChatVisibility();
        suggestions.replaceChildren();
        const selected=typeof livroSelecionado!=='undefined'&&livroSelecionado;
        document.getElementById('bibi-context').textContent=selected?`Vamos conversar sobre “${selected.titulo}”?`:'Um novo livro, uma personagem, uma ideia…';
        const labels=selected?['Quero conversar sobre os temas deste livro.','Podemos discutir os personagens?','Me ajude a refletir sobre a história.','Existem livros parecidos no nosso acervo?','Quero falar sobre o final, mas sem spoilers desnecessários.']:['Quero descobrir um livro diferente.','Me recomende uma obra de uma autora brasileira.','Quero conhecer livros escritos por mulheres.','Terminei um livro e gostaria de conversar sobre ele.','Quais livros combinam com minhas leituras favoritas?'];
        labels.forEach(label=>{const button=accountText('button',label);button.type='button';button.setAttribute('aria-label',label);button.onclick=()=>{form.elements.mensagem.value=label;form.requestSubmit();};suggestions.append(button);});
    }
    window.bibiQuestions=questions;
    questions();
    window.abortBibiResponse=()=>controller?.abort();
    document.getElementById('bibi-cancel').onclick=()=>controller?.abort();
    document.getElementById('bibi-clear').onclick=async()=>{
        if(controller)return;
        if(conversation){try{await accountApi('/api/minha-conta/ia/conversa/'+conversation,'DELETE');}catch{/* Uma conversa expirada já não precisa ser removida. */}}
        conversation=null;messages.replaceChildren();suggestions.hidden=false;status.textContent='Nova conversa.';form.elements.mensagem.focus();
    };
    form.onsubmit=async event=>{
        event.preventDefault();if(controller||!window.bibiAIState.disponivel)return;
        const message=form.elements.mensagem.value.trim();if(!message)return;
        const payload={mensagem:message,conversa_id:conversation};
        if(typeof livroSelecionado!=='undefined'&&livroSelecionado)payload.livro_id=livroSelecionado.id;
        messages.append(accountText('p',message,'bibi-message bibi-user'));
        const answer=accountText('p','','bibi-message bibi-answer');messages.append(answer);
        followTail=true;messages.scrollTop=messages.scrollHeight;
        suggestions.hidden=true;
        const waiting=/recomend|descobrir|parecid/i.test(message)?['Procurando livros que combinam com seus interesses…','Preparando sua recomendação…']:['A BIBI está preparando uma resposta para você…','Organizando uma resposta sobre sua leitura…'];
        let index=0;status.textContent=waiting[0];status.classList.add('bibi-loading');
        const timer=setInterval(()=>{status.textContent=waiting[++index%waiting.length];},6000);
        controller=new AbortController();const active=controller,timeout=setTimeout(()=>active.abort(),65000);
        document.getElementById('bibi-send').disabled=true;document.getElementById('bibi-cancel').hidden=false;document.getElementById('bibi-clear').disabled=true;
        let finished=false;
        try{
            const response=await fetch('/api/minha-conta/ia/chat',{method:'POST',signal:active.signal,headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name=csrf-token]').content},body:JSON.stringify(payload)});
            if(!response.ok){const data=await response.json();throw new Error(data.erro||'A BIBI está indisponível.');}
            const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
            while(true){const {value,done}=await reader.read();buffer+=decoder.decode(value||new Uint8Array(),{stream:!done});const lines=buffer.split('\n');buffer=lines.pop();for(const line of lines){if(!line.trim())continue;const item=JSON.parse(line);if(item.tipo==='inicio')conversation=item.conversa_id;if(item.tipo==='texto'){answer.textContent+=item.texto;if(followTail)messages.scrollTop=messages.scrollHeight;}if(item.tipo==='erro')throw new Error(item.mensagem);if(item.tipo==='fim'){finished=item.sucesso;if(!finished)throw new Error('Resposta interrompida.');}}if(done)break;}
            if(!finished)throw new Error('A conexão foi interrompida antes do fim da resposta.');
            status.textContent='Resposta concluída. Confira os dados do acervo.';form.elements.mensagem.value='';
        }catch(error){active.abort();status.textContent=error.name==='AbortError'?'Resposta interrompida ou tempo de espera excedido. O texto parcial pode estar incompleto.':error.message;}
        finally{clearInterval(timer);clearTimeout(timeout);controller=null;if(!answer.textContent.trim())answer.remove();status.classList.remove('bibi-loading');document.getElementById('bibi-send').disabled=false;document.getElementById('bibi-cancel').hidden=true;document.getElementById('bibi-clear').disabled=false;window.refreshBibiAvailability();}
    };
    const dash=document.getElementById('dash');
    if(dash&&document.body.dataset.admin==='true'){
        let panel,content;
        let explanation;
        function refreshInsights(){
            if(!window.bibiAIState.disponivel||document.querySelector('.bibi-insights'))return;
            panel=accountText('section','','bibi-insights');panel.append(accountText('h3','Insights da BIBI'));content=accountText('p','Organizando as informações da biblioteca…');panel.append(content);dash.append(panel);
            content.textContent='Organizando as informações da biblioteca…';
            accountApi('/api/ia/insights').then(data=>{if(!window.bibiAIState.disponivel){panel.remove();return;}content.textContent=data.texto;explanation?.remove();explanation=accountText('p',data.origem+(data.aviso?' · '+data.aviso:''));panel.append(explanation);}).catch(()=>{panel.remove();window.refreshBibiAvailability();});
        }
        window.refreshBibiInsights=refreshInsights;
        refreshInsights();
        window.addEventListener('bibi-settings-changed',()=>window.refreshBibiAvailability());
    }
})();
