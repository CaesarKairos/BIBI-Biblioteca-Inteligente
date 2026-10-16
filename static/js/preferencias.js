(()=>{
const theme=document.getElementById('settings-theme');
const personalReady=window.accountPreferencesReady.then(p=>{theme.value=p.tema;});
theme.addEventListener('change',async()=>{
 window.settingsOperation?.(theme,1);theme.disabled=true;
 try{await accountApi('/api/minha-conta/preferencias','PUT',{tema:theme.value});
 const config=JSON.parse(localStorage.getItem('bibiConfig')||'{}');config.darkMode=theme.value==='escuro';localStorage.setItem('bibiConfig',JSON.stringify(config));document.body.classList.toggle('dark-mode',config.darkMode);document.getElementById('theme-toggle-btn').setAttribute('aria-pressed',String(config.darkMode));if(document.body.dataset.page==='app')toggleTheme(config.darkMode);
 }catch(e){document.getElementById('settings-status').textContent=e.message;}
 finally{theme.disabled=false;window.settingsOperation?.(theme,-1);}
});
async function settingsControls(){
 if(!document.getElementById('book-settings'))return;
 const config=JSON.parse(localStorage.getItem('bibiConfig')||'{}');
 const globalFields=await accountApi('/api/config/cadastro');Object.assign(config,globalFields);
 const fieldKeys=['campoDescricaoVisivel','campoTemasVisivel','campoAnoVisivel','campoCategoriaVisivel','bloquearExcluirLivro','campoNumeroUsuario','mostrarColunaAula'];
 for(const [key,label] of [['campoDescricaoVisivel','Descrição'],['campoTemasVisivel','Temas'],['campoAnoVisivel','Ano'],['campoCategoriaVisivel','Categoria'],['bloquearExcluirLivro','Ocultar exclusão de livros'],['campoNumeroUsuario','Telefone no empréstimo'],['mostrarColunaAula','Mostrar coluna Aula']]){
  const row=accountText('label',label,'config-toggle-row');const input=document.createElement('input');input.type='checkbox';input.checked=config[key]??!['bloquearExcluirLivro','campoNumeroUsuario'].includes(key);row.prepend(input);
  input.onchange=async()=>{window.settingsOperation?.(input,1);input.disabled=true;config[key]=input.checked;try{await accountApi('/api/config/cadastro','PUT',Object.fromEntries(fieldKeys.map(k=>[k,config[k]??!['bloquearExcluirLivro','campoNumeroUsuario'].includes(k)])));config.darkMode=document.body.classList.contains('dark-mode');localStorage.setItem('bibiConfig',JSON.stringify(config));}catch(e){input.checked=!input.checked;config[key]=input.checked;document.getElementById('settings-status').textContent=e.message;}finally{input.disabled=false;window.settingsOperation?.(input,-1);}};document.getElementById(key==='mostrarColunaAula'?'agenda-settings':'book-settings').append(row);
 }
 for(const [key,label,container,field] of [['obrigar_localizacao_livro','Exigir localização física','book-settings','ativo'],['bloquear_excluir_agendamento','Bloquear exclusão de agendamento','agenda-settings','ativo'],['exigir_senha_agendamento','Confirmar senha da conta ao agendar','agenda-settings','ativo'],['exigir_senha_emprestimo','Confirmar senha da conta ao emprestar','book-settings','ativo'],['bloquear_email','Bloquear envio de e-mail','email','bloqueado']]){
  const value=await accountApi('/api/config/'+key+'/status');const labelEl=accountText('label',label,'config-toggle-row');const input=document.createElement('input');input.type='checkbox';input.checked=value[field];labelEl.prepend(input);document.getElementById(container).append(labelEl);
  input.onchange=async()=>{window.settingsOperation?.(input,1);input.disabled=true;try{const senha_atual=key.startsWith('exigir_senha')?await confirmarSenhaConta():undefined;if(senha_atual===null){input.checked=!input.checked;return;}await accountApi('/api/config/'+key+'/set','POST',{[field]:input.checked,senha_atual});}catch(e){input.checked=!input.checked;document.getElementById('settings-status').textContent=e.message;}finally{input.disabled=false;window.settingsOperation?.(input,-1);}};
 }
 document.getElementById('settings-lessons').value=(await accountApi('/api/config/quantidade_aulas/status')).quantidade;
}
accountForm('lessons-form',async()=>{await accountApi('/api/config/quantidade_aulas/set','POST',{quantidade:Number(document.getElementById('settings-lessons').value)});document.getElementById('settings-status').textContent='Quantidade de aulas salva.';});
window.settingsPreferencesReady=Promise.all([personalReady,settingsControls()]);

window.settingsPreferencesReady.then(()=>{document.querySelectorAll('.config-toggle-row').forEach(row=>{const input=row.querySelector('input');const sw=accountText('span','','switch');input.before(sw);sw.append(input,accountText('span','','slider'));input.setAttribute('role','switch');input.title='Salvo imediatamente';});}).catch(()=>{});

})();
