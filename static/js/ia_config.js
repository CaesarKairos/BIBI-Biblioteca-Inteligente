/* Preparação explícita: nenhuma geração é disparada ao escolher um campo. */
window.initializeAISettings=async function(){
    const form=document.getElementById('ai-config-form');if(!form||form.dataset.ready)return;form.dataset.ready='true';
    const state=document.getElementById('ai-config-state'),feedback=document.getElementById('ai-feedback'),model=form.elements.modelo;
    let saved,models=[];
    const identity=()=>form.elements.senha_atual.value?{senha_atual:form.elements.senha_atual.value}:{};
    const choice=()=>({provedor:form.elements.provedor.value,modelo:model.value});
    function notify(text,error=false){feedback.textContent=text;feedback.dataset.error=String(error);}
    async function refresh(){
        saved=await accountApi('/api/ia/config');
        form.elements.provedor.value=saved.provedor;
        if(![...model.options].some(option=>option.value===saved.modelo))model.add(new Option(saved.modelo||'Escolha um modelo',saved.modelo));
        model.value=saved.modelo;
        for(const name of ['por_hora','por_dia','concorrencia','max_tokens'])form.elements[name].value=saved[name];
        form.elements.ativa.checked=saved.ativa;form.elements.privacidade_revisada.checked=saved.privacidade_revisada;
        state.textContent=saved.mensagem;state.closest('.ai-state-card').dataset.ready=String(saved.disponivel);
        const provider=saved.provedores.find(p=>p.id===saved.provedor)?.nome;
        const currentProvider=saved.provedores.find(p=>p.id===saved.em_uso.provedor)?.nome;
        document.getElementById('ai-current-provider').textContent=`${provider} · ${saved.modelo||'Modelo ainda não escolhido'}${saved.ativa?' · Em uso na biblioteca: '+currentProvider+' / '+saved.em_uso.modelo:' · IA desativada'}`;
        document.getElementById('ai-key-state').textContent=saved.chave_configurada?'Chave salva e protegida. Deixe o campo vazio para mantê-la.':'Cole a chave de API que a escola obteve no serviço escolhido.';
        document.getElementById('ai-usage').textContent=`${saved.solicitacoes_24h} solicitações nas últimas 24 horas. Tokens informados pelo serviço: ${saved.tokens_informados_24h??'não disponíveis'}. Isso não representa uma fatura.`;
        document.getElementById('ai-test').disabled=Boolean(form.dataset.busy)||!saved.chave_configurada||!saved.modelo;
        window.settingsSaved?.(form);
    }
    async function operation(action){
        if(form.dataset.busy)return;form.dataset.busy='true';window.settingsOperation?.(form,1);
        const buttons=[...form.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);
        const fields=[...form.querySelectorAll('input,select,textarea')],previous=fields.map(field=>field.disabled);fields.forEach(field=>field.disabled=true);
        try{await action();await refresh();await window.refreshBibiAvailability?.();}
        catch(error){notify(error.message,true);if(/senha|identidade/i.test(error.message)){document.getElementById('ai-identity').open=true;form.elements.senha_atual.focus();}else{try{await refresh();await window.refreshBibiAvailability?.();}catch{/* Mantém o erro compreensível da operação original. */}}}
        finally{delete form.dataset.busy;buttons.forEach(b=>b.disabled=false);fields.forEach((field,index)=>field.disabled=previous[index]);document.getElementById('ai-test').disabled=!saved?.chave_configurada||!model.value;form.elements.senha_atual.value='';window.settingsSaved?.(form);window.settingsOperation?.(form,-1);}
    }
    form.elements.provedor.onchange=()=>{model.replaceChildren(new Option('Consulte as opções deste provedor',''));form.elements.chave.value='';form.elements.privacidade_revisada.checked=false;notify('Alteração em preparação. A configuração em uso será mantida até sua confirmação.');document.getElementById('ai-test').disabled=true;};
    document.getElementById('ai-save-key').onclick=()=>operation(async()=>{
        const data={...choice(),...identity()};if(form.elements.chave.value)data.chave=form.elements.chave.value;
        await accountApi('/api/ia/config','PUT',data);form.elements.chave.value='';
        document.getElementById('ai-identity').open=false;notify('Chave salva. Agora consulte os modelos.');
    });
    document.getElementById('ai-remove-key').onclick=()=>operation(async()=>{await accountApi('/api/ia/config','PUT',{...choice(),...identity(),remover_chave:true});notify('Chave removida. O uso dessa integração foi desativado.');});
    document.getElementById('ai-models').onclick=()=>operation(async()=>{
        await accountApi('/api/ia/config','PUT',choice());
        const data=await accountApi('/api/ia/modelos','POST',{});models=data.modelos;const previous=model.value;
        model.replaceChildren(new Option('Selecione um modelo',''));
        models.forEach(row=>model.add(new Option(row.nome,row.id)));
        if(models.some(row=>row.id===previous))model.value=previous;
        notify(models.length?'Opções recebidas. Escolha um modelo para continuar.':'O serviço não retornou modelos utilizáveis para esta chave.');
    });
    model.onchange=()=>operation(async()=>{
        await accountApi('/api/ia/config','PUT',choice());
        const prices=models.find(row=>row.id===model.value)?.precos;
        const number=value=>Number(value).toLocaleString('pt-BR',{maximumFractionDigits:4});
        document.getElementById('ai-model-info').textContent=prices&&typeof prices.prompt==='string'&&typeof prices.completion==='string'?`Preço informado: US$ ${number(Number(prices.prompt)*1000000)} por milhão de tokens de entrada e US$ ${number(Number(prices.completion)*1000000)} de saída. Não equivale ao custo final da solicitação.`:'Confira custos e condições na conta do serviço. Um modelo listado ainda precisa de teste.';
        notify('Modelo salvo para teste. A configuração em uso continua preservada.');
    });
    document.getElementById('ai-test').onclick=()=>operation(async()=>{
        await accountApi('/api/ia/config','PUT',choice());state.textContent='Verificando a conexão…';notify('Enviando uma mensagem técnica ao serviço…');
        try{const result=await accountApi('/api/ia/testar','POST',{});notify(result.mensagem);}
        catch(error){await refresh();throw error;}
    });
    form.elements.ativa.onchange=()=>{
        if(!form.elements.ativa.checked)operation(async()=>{await accountApi('/api/ia/config','PUT',{ativa:false});notify('IA desativada. O acervo e a circulação continuam funcionando.');});
        else if(!saved?.pode_ativar){form.elements.ativa.checked=false;notify('Primeiro escolha um modelo e teste a conexão.',true);}
    };
    document.getElementById('ai-discard').onclick=()=>operation(async()=>{await accountApi('/api/ia/config','PUT',{descartar:true});notify('Preparação descartada. A configuração em uso foi preservada.');});
    form.onsubmit=event=>{event.preventDefault();operation(async()=>{
        const data={...choice(),...identity(),ativa:form.elements.ativa.checked,privacidade_revisada:form.elements.privacidade_revisada.checked};
        for(const name of ['por_hora','por_dia','concorrencia','max_tokens'])data[name]=Number(form.elements[name].value);
        await accountApi('/api/ia/config','PUT',data);notify(data.ativa?'BIBI disponível para a biblioteca.':'Configuração salva. A IA continua desativada.');
    });};
    try{await refresh();}catch(error){notify(error.message,true);}
};
window.initializeAISettings();
