let recoveryToken = location.hash.slice(1);
if (document.body.dataset.mode === 'offline') history.replaceState(null,'',location.pathname);
(() => {
    try { if (JSON.parse(localStorage.getItem('bibiConfig') || '{}').darkMode) document.body.classList.add('dark-mode'); } catch {}
    let mode = document.body.dataset.mode;
    const form = document.getElementById('access-form');
    const status = document.getElementById('access-status');
    const submit = document.getElementById('access-submit');
    function changeMode(next){
        mode=next;
        const login=mode==='login',request=mode==='solicitar';
        document.getElementById('access-title').textContent=login?'Entrar na biblioteca':mode==='ativar'?'Ativar convite':request?'Recuperar senha':'Definir nova senha';
        document.getElementById('back-login').hidden=login;
        document.getElementById('login-actions').hidden=!login;
        document.getElementById('have-code').hidden=!request;
        document.getElementById('code-label').hidden=login||request;
        form.elements.codigo.required=!login&&!request;
        document.getElementById('password-label').hidden=request;
        form.elements.senha.required=!request;form.elements.senha.disabled=request;
        document.getElementById('confirm-label').hidden=login||request;
        form.elements.confirmacao.required=!login&&!request;form.elements.confirmacao.disabled=login||request;
        document.getElementById('password-help').hidden=login||request;
        form.elements.senha.autocomplete=login?'current-password':'new-password';
        form.elements.senha.minLength=login?1:12;
        submit.textContent=login?'Entrar':mode==='ativar'?'Ativar minha conta':request?'Enviar código':'Redefinir senha';
        const help=document.getElementById('access-help');help.hidden=login;
        help.textContent=mode==='ativar'?'Use o convite entregue pela biblioteca.':request?'Informe seu e-mail para solicitar um código.':'Informe o código recebido e escolha uma nova senha. Sem acesso ao e-mail, procure o bibliotecário.';
        form.elements.senha.value='';form.elements.confirmacao.value='';form.elements.codigo.value='';status.textContent='';
    }
    document.querySelectorAll('[data-access-mode]').forEach(button=>button.addEventListener('click',()=>changeMode(button.dataset.accessMode)));
    document.getElementById('back-login')?.addEventListener('click',()=>changeMode('login'));
    document.getElementById('have-code')?.addEventListener('click',()=>changeMode('redefinir'));
    form.addEventListener('submit', async event => {
        event.preventDefault(); submit.disabled = true; status.textContent = 'Aguarde...';
        const paths = {setup:'configurar',login:'entrar',ativar:'ativar',redefinir:'redefinir',offline:'recuperacao-local',solicitar:'recuperacao-email'};
        try {
            const response = await fetch('/api/acesso/' + paths[mode], {method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name=csrf-token]').content},body:JSON.stringify({...Object.fromEntries(new FormData(form)),token:recoveryToken})});
            const data = await response.json();
            if (!response.ok) throw new Error(data.erro || 'Não foi possível concluir.');
            if (data.destino) location.assign(data.destino);
            else if(mode==='solicitar'){changeMode('redefinir');status.textContent=data.mensagem;}
            else { status.textContent = data.mensagem; form.reset(); }
        } catch (error) { status.textContent = error.message; }
        finally { submit.disabled = false; }
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
