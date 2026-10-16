(() => {
    const dialog=document.getElementById('settings-dialog');
    const content=document.getElementById('settings-content');
    const status=document.getElementById('settings-status');
    const warning=document.getElementById('settings-discard');
    let ready, opener, snapshots=new Map(),pending=0;
    const changes=new Set();
    window.settingsMutation=path=>{if(dialog.open)changes.add(path);};
    window.settingsOperation=(source,delta)=>{if(!content.contains(source))return;pending=Math.max(0,pending+delta);document.getElementById("settings-close").disabled=pending>0;};
    const fingerprint=form=>JSON.stringify([...form.elements].filter(e=>e.matches('input,select,textarea')).map(e=>[e.name||e.id,e.type==='checkbox'?e.checked:e.type==='file'?[...e.files].map(f=>f.name):e.value]));
    function snapshot(){content.querySelectorAll('form:not([method=get])').forEach(form=>snapshots.set(form,fingerprint(form)));}
    function dirty(){return [...snapshots].some(([form,value])=>form.isConnected&&fingerprint(form)!==value);}
    function section(key){
        const target=content.querySelector(`[data-settings-section="${CSS.escape(key)}"]`) || content.querySelector('[data-settings-section]');
        if(!target)return;
        key=target.dataset.settingsSection;
        content.querySelectorAll('.settings-panels > section').forEach(panel=>panel.hidden=(panel.dataset.group||panel.id)!==key);
        content.querySelectorAll('[data-settings-section]').forEach(button=>button.setAttribute('aria-current',String(button===target)));
        content.querySelector('.settings-panels').scrollTop=0;
        status.textContent='';
    }
    const script=src=>new Promise((resolve,reject)=>{const el=document.createElement('script');el.src=src;el.onload=resolve;el.onerror=()=>reject(new Error('Não foi possível carregar Configurações.'));document.body.append(el);});
    async function load(){
        const response=await fetch('/configuracoes?fragmento=1');
        if(!response.ok)throw new Error('Não foi possível abrir Configurações.');
        content.innerHTML=await response.text();
        accountForm('password-form',async data=>{await accountApi('/api/minha-conta/senha','POST',data);location.assign('/acesso');});
        accountForm('verify-email-form',async(data,form)=>{const r=await accountApi('/api/minha-conta/email/enviar','POST',data);form.elements.senha_atual.value='';accountStatus(r.mensagem,form);});
        accountForm('confirm-email-form',async data=>{await accountApi('/api/minha-conta/email/confirmar','POST',data);location.assign('/acesso');});
        await script('/static/js/settings_help.js');
        await script('/static/js/preferencias.js');
        await window.settingsPreferencesReady;
        if(document.body.dataset.admin==='true'){
            await script('/static/js/gestao.js');
            await window.settingsManagementReady;
        }
        content.querySelectorAll('.settings-panels > section').forEach(panel=>panel.classList.add('config-panel'));
        const note=accountText('p','As opções de exibição e os switches são salvos imediatamente.');
        document.getElementById('cadastro')?.prepend(note);
        window.descreverConfiguracoes(content);
        snapshot();
    }
    window.abrirConfiguracoesCompartilhadas=async(key='minha-conta')=>{
        if(typeof key!=='string')key='minha-conta';
        if(!dialog.open){opener=document.activeElement;dialog.showModal();}
        status.textContent='Carregando…';
        try{ready??=load();await ready;document.getElementById('settings-theme').value=document.body.classList.contains('dark-mode')?'escuro':'claro';section(key);}
        catch(error){status.textContent=error.message;ready=null;}
    };
    function close(){
        if(pending){status.textContent="Aguarde a operação em andamento.";return;}
        if(dirty()){warning.hidden=false;document.getElementById('settings-continue').focus();return;}
        dialog.close();
    }
    dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
    dialog.addEventListener('keydown',event=>{
        if(event.key!=='Tab')return;
        const controls=[...dialog.querySelectorAll('button,a[href],input,select,textarea,summary,[tabindex="0"]')]
            .filter(control=>!control.disabled&&control.tabIndex>=0&&control.getClientRects().length);
        const first=controls[0],last=controls[controls.length-1];
        if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
        else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
    });
    dialog.addEventListener('close',()=>{
        document.getElementById('invite-code')?.replaceChildren();
        const invite=document.getElementById('invite-result');if(invite)invite.hidden=true;
        warning.hidden=true;(opener?.isConnected?opener:document.getElementById('config-open'))?.focus({preventScroll:true});
        if(changes.size){window.dispatchEvent(new CustomEvent('bibi-settings-changed',{detail:[...changes]}));changes.clear();}
    });
    document.getElementById('settings-close').addEventListener('click',close);
    document.getElementById('settings-continue').addEventListener('click',()=>{warning.hidden=true;document.getElementById('settings-close').focus();});
    document.getElementById('settings-discard-confirm').addEventListener('click',()=>{
        // A fresh fragment restores server values; immediate preferences stay saved.
        window.settingsStatusObserver?.disconnect();content.replaceChildren();snapshots.clear();ready=null;dialog.close();
    });
    content.addEventListener('click',event=>{const button=event.target.closest('[data-settings-section]');if(button)section(button.dataset.settingsSection);});
    window.settingsSaved=form=>{if(content.contains(form))snapshots.set(form,fingerprint(form));};
    document.getElementById('config-open')?.addEventListener('click',()=>window.abrirConfiguracoesCompartilhadas());
    document.addEventListener('click',event=>{
        const link=event.target.closest('a[href]');if(!link)return;
        const url=new URL(link.href,location.href);if(url.origin!==location.origin)return;
        const sections={'/configuracoes':'minha-conta','/leitores/contas':'gestao-convites','/emprestimos/circulacao':'circulacao','/acervo/importacao':'dados','/leitores/importacao':'dados'};
        if(!sections[url.pathname])return;
        event.preventDefault();
        window.abrirConfiguracoesCompartilhadas(url.hash.slice(1)||sections[url.pathname]).then(()=>{
            if(url.searchParams.has('leitor')){const reader=document.getElementById('invite-reader');if(reader){reader.value=url.searchParams.get('leitor');reader.dispatchEvent(new Event('change'));}}
            if(url.pathname.endsWith('/importacao')){
                const kind=document.getElementById('csv-kind');
                if(kind){kind.value=url.pathname.startsWith('/leitores')?'leitores':'livros';kind.dispatchEvent(new Event('change'));}
            }
        });
    });
    const params=new URLSearchParams(location.search);
    if(params.has('config'))window.abrirConfiguracoesCompartilhadas(location.hash.slice(1)||params.get('config'));
    else if(document.referrer.includes('/configuracoes')&&location.hash)window.abrirConfiguracoesCompartilhadas(location.hash.slice(1));
})();
