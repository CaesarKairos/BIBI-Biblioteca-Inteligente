try { if (JSON.parse(localStorage.getItem('bibiConfig') || '{}').darkMode) document.body.classList.add('dark-mode'); } catch {}
function accountText(tag,text,className) { const e=document.createElement(tag); e.textContent=text; if(className) e.className=className; return e; }
async function accountApi(path,method='GET',data) {
    const response=await fetch(path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name=csrf-token]').content},body:data===undefined?undefined:JSON.stringify(data)});
    const result=await response.json();
    if(!response.ok) throw new Error(result.erro || 'Não foi possível concluir.');
    if(method!=='GET')window.settingsMutation?.(path);
    return result;
}
function accountAction(button,action) {
    if(!button) return;
    button.addEventListener('click',async()=>{
        button.disabled=true; window.settingsOperation?.(button,1);
        try { await action(); } catch(e) { accountStatus(e.message,button); }
        finally { button.disabled=false; window.settingsOperation?.(button,-1); }
    });
}
function accountButton(text,action) { const b=accountText('button',text,'btn-small'); b.type='button'; accountAction(b,action); return b; }
function accountForm(id,action) {
    const form=document.getElementById(id); if(!form) return;
    form.addEventListener('submit',async event=>{
        event.preventDefault();
        const data=Object.fromEntries(new FormData(form));
        const fields=[...form.elements].filter(control=>control.matches('input,select,textarea'));
        const previous=fields.map(control=>control.disabled);
        const button=form.querySelector('button[type=submit],button:not([type])');
        if(button) button.disabled=true;
        fields.forEach(control=>control.disabled=true);window.settingsOperation?.(form,1);
        try { await action(data,form); if(!['csv-form','restore-form'].includes(form.id))window.settingsSaved?.(form); } catch(e) { accountStatus(e.message,form); }
        finally { fields.forEach((control,index)=>control.disabled=previous[index]);if(button) button.disabled=false; window.settingsOperation?.(form,-1); }
    });
}
accountAction(document.getElementById('account-logout'),async()=>{await accountApi('/api/acesso/sair','POST',{});location.assign('/acesso');});

// The saved preference belongs to the signed-in account; localStorage is a cache.
window.accountPreferencesReady=accountApi('/api/minha-conta/preferencias');
window.accountPreferencesReady.catch(()=>{});
window.addEventListener('load',()=>window.accountPreferencesReady.then(preferences=>{
    const dark=preferences.tema==='escuro';
    const config=JSON.parse(localStorage.getItem('bibiConfig')||'{}');config.darkMode=dark;
    localStorage.setItem('bibiConfig',JSON.stringify(config));
    if(document.body.dataset.page==='app')toggleTheme(dark);
    else document.body.classList.toggle('dark-mode',dark);
    document.getElementById('theme-toggle-btn')?.setAttribute('aria-pressed',String(dark));
}).catch(error=>accountStatus(error.message)));

function confirmarSenhaConta() {
    return new Promise(resolve=>{
        const previous=document.activeElement;
        const dialog=document.createElement('dialog');dialog.className='password-confirm-dialog';
        const form=document.createElement('form');form.method='dialog';
        const title=accountText('h2','Confirmar alteração de segurança');title.id='password-confirm-title';dialog.setAttribute('aria-labelledby',title.id);
        const label=accountText('label','Senha atual da sua conta');const input=document.createElement('input');input.type='password';input.autocomplete='current-password';input.maxLength=128;input.required=true;label.append(input);
        const submit=accountText('button','Confirmar','btn-primary');submit.type='submit';
        const cancel=accountText('button','Cancelar');cancel.type='button';cancel.onclick=()=>dialog.close();
        let password=null;
        form.addEventListener('submit',()=>{password=input.value;});
        form.append(title,label,submit,cancel);dialog.append(form);document.body.append(dialog);
        dialog.addEventListener('close',()=>{input.value='';dialog.remove();previous?.focus();resolve(password);},{once:true});
        dialog.showModal();input.focus();
    });
}

function accountStatus(message,source) {
 const dialog=document.getElementById('settings-dialog');
 const status=dialog?.open?document.getElementById('settings-status'):document.getElementById('account-status');
 if(status)status.textContent=message;
 else if(typeof showToast==='function')showToast(message,'error');
 else {const notice=accountText('p',message);notice.setAttribute('role','alert');document.querySelector('main').prepend(notice);}
 if(source?.closest('#settings-content')) {
  const panel=source.closest('section');
  if(panel){let local=panel.querySelector(':scope > .operation-status');if(!local){local=accountText('p','','operation-status');local.setAttribute('role','status');panel.append(local);}local.textContent=message;}
 }
}
