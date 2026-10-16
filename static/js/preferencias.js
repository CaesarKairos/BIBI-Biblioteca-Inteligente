const theme=document.getElementById('settings-theme');
accountApi('/api/minha-conta/preferencias').then(p=>{theme.value=p.tema;});
theme.addEventListener('change',async()=>{
 try{await accountApi('/api/minha-conta/preferencias','PUT',{tema:theme.value});
 const config=JSON.parse(localStorage.getItem('bibiConfig')||'{}');config.darkMode=theme.value==='escuro';localStorage.setItem('bibiConfig',JSON.stringify(config));document.body.classList.toggle('dark-mode',config.darkMode);
 }catch(e){document.getElementById('account-status').textContent=e.message;}
});
async function settingsControls(){
 if(!document.getElementById('book-settings'))return;
 const config=JSON.parse(localStorage.getItem('bibiConfig')||'{}');
 const globalFields=await accountApi('/api/config/cadastro');Object.assign(config,globalFields);
 const fieldKeys=['campoDescricaoVisivel','campoTemasVisivel','campoAnoVisivel','campoCategoriaVisivel','bloquearExcluirLivro','campoNumeroUsuario','mostrarColunaAula'];
 for(const [key,label] of [['campoDescricaoVisivel','Descrição'],['campoTemasVisivel','Temas'],['campoAnoVisivel','Ano'],['campoCategoriaVisivel','Categoria'],['bloquearExcluirLivro','Ocultar exclusão de livros'],['campoNumeroUsuario','Telefone no empréstimo'],['mostrarColunaAula','Mostrar coluna Aula']]){
  const row=accountText('label',label);const input=document.createElement('input');input.type='checkbox';input.checked=config[key]??!['bloquearExcluirLivro','campoNumeroUsuario'].includes(key);row.prepend(input);
  input.onchange=async()=>{config[key]=input.checked;try{await accountApi('/api/config/cadastro','PUT',Object.fromEntries(fieldKeys.map(k=>[k,config[k]??!['bloquearExcluirLivro','campoNumeroUsuario'].includes(k)])));localStorage.setItem('bibiConfig',JSON.stringify(config));}catch(e){input.checked=!input.checked;config[key]=input.checked;document.getElementById('account-status').textContent=e.message;}};document.getElementById(key==='mostrarColunaAula'?'agenda-settings':'book-settings').append(row);
 }
 for(const [key,label,container,field] of [['obrigar_localizacao_livro','Exigir localização física','book-settings','ativo'],['bloquear_excluir_agendamento','Bloquear exclusão de agendamento','agenda-settings','ativo'],['exigir_senha_agendamento','Confirmar senha da conta ao agendar','agenda-settings','ativo'],['exigir_senha_emprestimo','Confirmar senha da conta ao emprestar','book-settings','ativo'],['bloquear_email','Bloquear envio de e-mail','email','bloqueado']]){
  const value=await accountApi('/api/config/'+key+'/status');const labelEl=accountText('label',label);const input=document.createElement('input');input.type='checkbox';input.checked=value[field];labelEl.prepend(input);document.getElementById(container).append(labelEl);
  input.onchange=async()=>{try{const senha_atual=key.startsWith('exigir_senha')?await confirmarSenhaConta():undefined;if(senha_atual===null){input.checked=!input.checked;return;}await accountApi('/api/config/'+key+'/set','POST',{[field]:input.checked,senha_atual});}catch(e){input.checked=!input.checked;document.getElementById('account-status').textContent=e.message;}};
 }
 document.getElementById('settings-lessons').value=(await accountApi('/api/config/quantidade_aulas/status')).quantidade;
}
accountAction(document.getElementById('save-lessons'),async()=>{await accountApi('/api/config/quantidade_aulas/set','POST',{quantidade:Number(document.getElementById('settings-lessons').value)});document.getElementById('account-status').textContent='Quantidade de aulas salva.';});
settingsControls().catch(e=>document.getElementById('account-status').textContent=e.message);
