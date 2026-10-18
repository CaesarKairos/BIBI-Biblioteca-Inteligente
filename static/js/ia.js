/* IA na interface existente. Texto remoto sempre renderizado com textContent. */
(() => {
    async function initializeSettings() {
        const form=document.getElementById('ai-config-form');
        if(!form||form.dataset.ready)return;
        form.dataset.ready='true';
        const state=document.getElementById('ai-config-state'),info=document.getElementById('ai-model-info');
        const model=form.elements.modelo;
        async function refresh(){
            const data=await accountApi('/api/ia/config');
            for(const [key,value] of Object.entries(data)){
                const field=form.elements.namedItem(key);if(!field||key==='modelo')continue;
                if(field.type==='checkbox')field.checked=value;else field.value=value;
            }
            model.replaceChildren(new Option(data.modelo||'Consulte os modelos após salvar e ativar',data.modelo));
            state.textContent=`${data.ativa?'IA ativa':'IA desativada'} · ${data.chave_configurada?'Chave salva':'Sem chave'} · ${data.modelo||'Selecione um modelo para gerar respostas'} · ${data.solicitacoes_24h} solicitações nas últimas 24h. Tokens informados: ${data.tokens_informados_24h??'não disponíveis'}. ${data.custo}`;
            if(Object.keys(data.limites_provedor).length)state.textContent+=' Limites informados pelo provedor na última resposta: '+JSON.stringify(data.limites_provedor);
            state.textContent+=' '+(data.teste?data.teste.mensagem:'Geração ainda não verificada nesta sessão do servidor.');
            window.settingsSaved?.(form);
        }
        form.elements.provedor.addEventListener('change',()=>{model.replaceChildren(new Option('Salve o provedor e consulte seus modelos',''));state.textContent='Salve para configurar este provedor. Credenciais anteriores são preservadas no servidor.';});
        accountForm('ai-config-form',async(_,current)=>{
            // accountForm desabilita controles durante a operação; leia valores diretamente.
            const data={};
            for(const name of ['ativa','privacidade_revisada','remover_chave'])data[name]=current.elements[name].checked;
            for(const name of ['por_hora','por_dia','concorrencia','max_tokens'])data[name]=Number(current.elements[name].value);
            for(const name of ['provedor','modelo','senha_atual'])data[name]=current.elements[name].value;
            if(current.elements.chave.value)data.chave=current.elements.chave.value;
            try{await accountApi('/api/ia/config','PUT',data);await refresh();}
            finally{current.elements.chave.value='';current.elements.senha_atual.value='';}
        });
        accountAction(document.getElementById('ai-disable'),async()=>{await accountApi('/api/ia/config','PUT',{ativa:false});await refresh();});
        accountAction(document.getElementById('ai-models'),async()=>{
            const data=await accountApi('/api/ia/modelos','POST',{}),previous=model.value;
            model.replaceChildren(new Option('Selecione um modelo',''));
            data.modelos.forEach(row=>{const option=new Option(`${row.nome} — ${row.estado}`,row.id);option.dataset.cost=JSON.stringify(row.precos);model.add(option);});
            if([...model.options].some(o=>o.value===previous))model.value=previous;
            else if(previous){const missing=new Option(previous+' — não listado / indisponível',previous);missing.disabled=true;model.add(missing);model.value=previous;}
            info.textContent='Lista informada pelo provedor. Geração e permissões dependem do plano e precisam de teste. Custos não informados não significam gratuidade.';
        });
        model.addEventListener('change',()=>{const cost=model.selectedOptions[0]?.dataset.cost;info.textContent=cost&&cost!=='null'?`Preços informados pelo provedor (USD por token, quando aplicável): ${cost}. Não representam cobrança efetiva.`:'Custos não informados nesta listagem. Confira o painel e os termos do provedor.';});
        accountAction(document.getElementById('ai-test'),async()=>{state.textContent='Verificando conexão e geração…';const data=await accountApi('/api/ia/testar','POST',{});state.textContent=data.mensagem;});
        accountForm('ai-metadata-form',async(data,current)=>{await accountApi('/api/ia/livros/'+data.id+'/autoria','PUT',{genero:data.genero||null,pais:data.pais||null,fonte:data.fonte||null});accountStatus('Metadados salvos. A seleção será recalculada.',current);});
        const metadataForm=document.getElementById('ai-metadata-form'),bookSelect=metadataForm.elements.id;
        bookSelect.addEventListener('change',async()=>{
            if(!bookSelect.value)return;
            try{const data=await accountApi('/api/ia/livros/'+bookSelect.value+'/autoria');for(const field of ['genero','pais','fonte'])metadataForm.elements[field].value=data[field]||'';window.settingsSaved?.(metadataForm);}
            catch(error){accountStatus(error.message,metadataForm);}
        });
        accountApi('/api/livros').then(books=>{bookSelect.replaceChildren(new Option('Selecione uma obra',''));books.forEach(book=>bookSelect.add(new Option(`${book.titulo} — ${book.autor}`,book.id)));window.settingsSaved?.(metadataForm);}).catch(error=>accountStatus(error.message,metadataForm));
        try{await refresh();}catch(error){state.textContent=error.message;}
    }
    window.initializeAISettings=initializeSettings;
    initializeSettings();
    const form=document.getElementById('bibi-chat-form');
    if(!form)return;
    const messages=document.getElementById('bibi-messages'),status=document.getElementById('bibi-status'),suggestions=document.getElementById('bibi-suggestions');
    let conversation=null,controller=null;
    function questions(){
        suggestions.replaceChildren();
        const selected=typeof livroSelecionado!=='undefined'&&livroSelecionado;
        const labels=selected?['Quero conversar sobre os temas deste livro.','Podemos discutir os personagens?','Me ajude a refletir sobre a história.','Existem livros parecidos no nosso acervo?','Quero falar sobre o final, mas sem spoilers desnecessários.']:['Quero descobrir um livro diferente.','Me recomende uma obra de uma autora brasileira.','Quero conhecer livros escritos por mulheres.','Terminei um livro e gostaria de conversar sobre ele.','Quais livros combinam com minhas leituras favoritas?'];
        labels.forEach(label=>{const button=accountText('button',label,'btn-small');button.type='button';button.onclick=()=>{form.elements.mensagem.value=label;form.requestSubmit();};suggestions.append(button);});
    }
    window.bibiQuestions=questions;
    questions();
    accountApi('/api/minha-conta/ia/estado').then(data=>{document.getElementById('bibi-privacy').textContent=data.ativa?`${data.provedor}. ${data.aviso}`:'IA desativada. As sugestões locais do acervo continuam disponíveis.';}).catch(()=>{});
    document.getElementById('bibi-cancel').onclick=()=>controller?.abort();
    document.getElementById('bibi-clear').onclick=async()=>{
        controller?.abort();
        if(conversation){try{await accountApi('/api/minha-conta/ia/conversa/'+conversation,'DELETE');}catch(error){status.textContent=error.message;return;}}
        conversation=null;messages.replaceChildren();status.textContent='Nova conversa.';
    };
    form.onsubmit=async event=>{
        event.preventDefault();if(controller)return;
        const message=form.elements.mensagem.value.trim();if(!message)return;
        const payload={mensagem:message,conversa_id:conversation};
        if(typeof livroSelecionado!=='undefined'&&livroSelecionado)payload.livro_id=livroSelecionado.id;
        messages.append(accountText('p',message,'bibi-user'));
        const answer=accountText('p','','bibi-answer');messages.append(answer);
        const waiting=/recomend|descobrir|parecid/i.test(message)?['Procurando livros que combinam com seus interesses…','Preparando sua recomendação…']:['A BIBI está preparando uma resposta para você…','Organizando uma resposta sobre sua leitura…'];
        let index=0;status.textContent=waiting[0];status.classList.add('bibi-loading');
        const timer=setInterval(()=>{status.textContent=waiting[++index%waiting.length];},6000);
        controller=new AbortController();const active=controller,timeout=setTimeout(()=>active.abort(),65000);
        form.querySelector('button').disabled=true;document.getElementById('bibi-cancel').disabled=false;
        let finished=false;
        try{
            const response=await fetch('/api/minha-conta/ia/chat',{method:'POST',signal:active.signal,headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name=csrf-token]').content},body:JSON.stringify(payload)});
            if(!response.ok){const data=await response.json();throw new Error(data.erro||'A BIBI está indisponível.');}
            const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
            while(true){const {value,done}=await reader.read();buffer+=decoder.decode(value||new Uint8Array(),{stream:!done});const lines=buffer.split('\n');buffer=lines.pop();for(const line of lines){if(!line.trim())continue;const item=JSON.parse(line);if(item.tipo==='inicio')conversation=item.conversa_id;if(item.tipo==='texto')answer.textContent+=item.texto;if(item.tipo==='erro')throw new Error(item.mensagem);if(item.tipo==='fim'){finished=item.sucesso;if(!finished)throw new Error('Resposta interrompida.');}}if(done)break;}
            if(!finished)throw new Error('A conexão foi interrompida antes do fim da resposta.');
            status.textContent='Resposta concluída. Confira os dados do acervo.';form.elements.mensagem.value='';
        }catch(error){active.abort();status.textContent=error.name==='AbortError'?'Resposta interrompida ou tempo de espera excedido. O texto parcial pode estar incompleto.':error.message;}
        finally{clearInterval(timer);clearTimeout(timeout);controller=null;status.classList.remove('bibi-loading');form.querySelector('button').disabled=false;document.getElementById('bibi-cancel').disabled=true;}
    };
    const dash=document.getElementById('dash');
    if(dash&&document.body.dataset.admin==='true'){
        const panel=accountText('section','','bibi-insights');panel.append(accountText('h3','Insights da BIBI'));const content=accountText('p','Organizando as informações da biblioteca…');panel.append(content);dash.append(panel);
        let explanation;
        function refreshInsights(){
            content.textContent='Organizando as informações da biblioteca…';
            accountApi('/api/ia/insights').then(data=>{content.textContent=data.texto;explanation?.remove();explanation=accountText('p',data.origem+(data.aviso?' · '+data.aviso:''));panel.append(explanation);}).catch(error=>content.textContent=error.message);
        }
        refreshInsights();
        window.addEventListener('bibi-settings-changed',event=>{if(event.detail.some(path=>path.startsWith('/api/ia/')))refreshInsights();});
    }
})();
