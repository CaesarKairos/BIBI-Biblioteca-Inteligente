try { if (JSON.parse(localStorage.getItem('bibiConfig') || '{}').darkMode) document.body.classList.add('dark-mode'); } catch {}
function accountText(tag,text,className) { const e=document.createElement(tag); e.textContent=text; if(className) e.className=className; return e; }
async function accountApi(path,method='GET',data) {
    const response=await fetch(path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name=csrf-token]').content},body:data===undefined?undefined:JSON.stringify(data)});
    const result=await response.json();
    if(!response.ok) throw new Error(result.erro || 'Não foi possível concluir.');
    return result;
}
function accountAction(button,action) {
    button.addEventListener('click',async()=>{
        button.disabled=true;
        try { await action(); } catch(e) { document.getElementById('account-status').textContent=e.message; }
        finally { button.disabled=false; }
    });
}
function accountButton(text,action) { const b=accountText('button',text,'btn-primary btn-small'); b.type='button'; accountAction(b,action); return b; }
function accountForm(id,action) {
    const form=document.getElementById(id); if(!form) return;
    form.addEventListener('submit',async event=>{
        event.preventDefault(); const button=form.querySelector('button[type=submit],button:not([type])'); if(button) button.disabled=true;
        try { await action(Object.fromEntries(new FormData(form)),form); } catch(e) { document.getElementById('account-status').textContent=e.message; }
        finally { if(button) button.disabled=false; }
    });
}
document.getElementById('account-logout')?.addEventListener('click',async()=>{await accountApi('/api/acesso/sair','POST',{});location.assign('/acesso');});
