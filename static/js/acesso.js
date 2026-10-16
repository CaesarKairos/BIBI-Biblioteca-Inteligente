let recoveryToken = location.hash.slice(1);
if (document.body.dataset.mode === 'offline') history.replaceState(null,'',location.pathname);
(() => {
    try { if (JSON.parse(localStorage.getItem('bibiConfig') || '{}').darkMode) document.body.classList.add('dark-mode'); } catch {}
    let mode = document.body.dataset.mode;
    const form = document.getElementById('access-form');
    const status = document.getElementById('access-status');
    const submit = document.getElementById('access-submit');
    document.querySelectorAll('[data-mode]').forEach(button => {
        if (button.tagName !== 'BUTTON') return;
        button.addEventListener('click', () => {
            mode = button.dataset.mode;
            document.querySelectorAll('.access-tabs button').forEach(b => b.setAttribute('aria-current',String(b === button)));
            document.getElementById('code-label').hidden = mode === 'login';
            document.getElementById('confirm-label').hidden = mode === 'login';
            document.getElementById('password-help').hidden = mode === 'login';
            document.getElementById('request-recovery').hidden = mode !== 'redefinir';
            form.elements.senha.autocomplete = mode === 'login' ? 'current-password' : 'new-password';
            form.elements.senha.minLength = mode === 'login' ? 1 : 12;
            submit.textContent = mode === 'login' ? 'Entrar' : mode === 'ativar' ? 'Ativar minha conta' : 'Redefinir senha';
            document.getElementById('access-help').textContent = mode === 'login' ? 'Entre com seu e-mail e senha.' : mode === 'ativar' ? 'Use o e-mail e o código do convite entregue pela biblioteca. Não há cadastro público.' : 'Informe o código de recuperação. Se seu e-mail não foi verificado ou você não recebeu um código, procure o bibliotecário para recuperação presencial.';
            status.textContent = '';
        });
    });
    form.addEventListener('submit', async event => {
        event.preventDefault(); submit.disabled = true; status.textContent = 'Aguarde...';
        const paths = {setup:'configurar',login:'entrar',ativar:'ativar',redefinir:'redefinir',offline:'recuperacao-local'};
        try {
            const response = await fetch('/api/acesso/' + paths[mode], {method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name=csrf-token]').content},body:JSON.stringify({...Object.fromEntries(new FormData(form)),token:recoveryToken})});
            const data = await response.json();
            if (!response.ok) throw new Error(data.erro || 'Não foi possível concluir.');
            if (data.destino) location.assign(data.destino);
            else { status.textContent = data.mensagem; form.reset(); }
        } catch (error) { status.textContent = error.message; }
        finally { submit.disabled = false; }
    });
    document.getElementById('request-recovery')?.addEventListener('click',async event=>{
        const button=event.target;button.disabled=true;
        try { const response=await fetch('/api/acesso/recuperacao-email',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name=csrf-token]').content},body:JSON.stringify({email:form.elements.email.value})});const result=await response.json();status.textContent=result.mensagem || result.erro; }
        catch { status.textContent='Falha de conexão. Procure o bibliotecário.'; }
        finally { button.disabled=false; }
    });
})();
const legalDialog=document.getElementById('legal-dialog');
let legalOpener;
document.querySelectorAll('[data-legal]').forEach(link=>link.addEventListener('click',event=>{
 event.preventDefault();legalOpener=link;legalDialog.showModal();document.getElementById(link.dataset.legal).scrollIntoView();
}));
legalDialog?.addEventListener('close',()=>legalOpener?.focus());
document.getElementById('close-legal')?.addEventListener('click',()=>legalDialog.close());
if(document.body.dataset.mode==='offline' && !recoveryToken && document.body.dataset.legacy!=='true')document.getElementById('access-form').hidden=true;
if(recoveryToken && document.body.dataset.mode==='offline') {
 const button=document.getElementById('access-submit');button.disabled=true;
 document.getElementById('code-label').hidden=true;
 fetch('/api/acesso/recuperacao-desktop/sessao',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name=csrf-token]').content},body:JSON.stringify({token:recoveryToken})})
 .then(async response=>{const data=await response.json();if(!response.ok)throw new Error(data.erro);button.disabled=false;})
 .catch(error=>{recoveryToken='';document.getElementById('access-status').textContent=error.message;});
}
