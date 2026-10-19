/* The server selects models. Rendering settings never starts a generation. */
window.initializeAISettings=async function(){
 const root=document.getElementById('inteligencia-artificial');if(!root||root.dataset.ready)return;root.dataset.ready='true';
 const form=document.getElementById('ai-service-form'),advanced=document.getElementById('ai-routing-form');
 const feedback=document.getElementById('ai-feedback'),toggle=document.getElementById('ai-enabled');let saved,busy=false;
 const notify=(text,error=false)=>{feedback.textContent=text;feedback.dataset.error=String(error);};
 async function sensitive(path,method,data){
  saved=await accountApi('/api/ia/servicos');
  if(!saved.identidade_confirmada){const password=await confirmarSenhaConta();if(password===null)throw new Error('Operação cancelada.');data={...data,senha_atual:password};}
  return accountApi(path,method,data);
 }
 function resetForm(){form.reset();form.hidden=true;form.elements.provedor.disabled=false;form.elements.provedor.dispatchEvent(new Event('change'));window.settingsSaved?.(form);}
 function edit(service){
  form.hidden=false;form.elements.provedor.disabled=false;
  form.elements.provedor.value=service?.id||'openai';form.elements.provedor.disabled=Boolean(service);
  form.elements.provedor.dispatchEvent(new Event('change'));
  form.elements.chave.value='';form.elements.custos_autorizados.checked=service?.custos_autorizados||false;
  form.elements.chave.required=!service?.chave_salva&&!service?.chave_pendente;
  form.elements.privacidade_revisada.checked=service?.privacidade_revisada||false;
  form.elements.limite_diario.value=service?.limite_diario||200;
  document.getElementById('ai-service-title').textContent=service?'Alterar serviço':'Adicionar serviço';
  window.settingsSaved?.(form);form.scrollIntoView({block:'nearest'});form.elements.chave.focus();
 }
 async function refresh(){
  saved=await accountApi('/api/ia/servicos');toggle.checked=saved.ativa;
  document.getElementById('ai-config-state').textContent=saved.disponivel?'IA ativada':saved.ativa?'IA indisponível': 'IA desativada';
  const list=document.getElementById('ai-services');list.replaceChildren();
  if(!saved.servicos.length)list.append(accountText('p','Nenhum serviço cadastrado.'));
  saved.pendencias.forEach(text=>list.append(accountText('p',text)));
  const labels={disponivel:'Disponível',desativado:'Desativado',verificacao_necessaria:'Verificação necessária'};
  saved.servicos.forEach(service=>{
   const row=accountText('article','','settings-service');const header=accountText('div','','settings-row');
   const info=accountText('div');info.append(accountText('strong',service.nome),accountText('p',`${labels[service.estado]} · ${service.chave_salva?'Chave protegida':'Chave ainda não verificada'}${service.chave_pendente?' · Alteração pendente':''}`));header.append(info);row.append(header);
   const actions=accountText('div','','settings-actions');
   const button=(text,action,parent=actions)=>{const b=accountText('button',text);b.type='button';b.onclick=()=>operation(action);parent.append(b);};
   button('Verificar serviço',async()=>{notify('Verificando o serviço…');const r=await accountApi(`/api/ia/servicos/${service.id}/testar`,'POST',{});notify(r.mensagem);});
   const change=accountText('button','Alterar');change.type='button';change.onclick=()=>edit(service);actions.append(change);
   button(service.habilitado?'Desativar':'Habilitar',async()=>{await accountApi(`/api/ia/servicos/${service.id}`,'PUT',{habilitado:!service.habilitado});notify('Estado do serviço atualizado.');});
   button('Remover',async()=>{if(!confirm(`Remover o serviço ${service.nome} e sua chave?`))return;await sensitive(`/api/ia/servicos/${service.id}`,'DELETE',{});notify('Serviço removido.');});
   row.append(actions,accountText('p','A verificação envia uma mensagem de teste e pode consumir créditos.'));
   if(service.modelos.some(m=>m.legado_autorizado))row.append(accountText('p','A configuração anterior autoriza somente seu modelo já verificado. Salvar a opção de custos desmarcada revoga essa autorização.'));
   const details=accountText('details');details.append(accountText('summary','Modelos e condições'));
   button('Atualizar modelos',async()=>{await accountApi(`/api/ia/servicos/${service.id}/modelos`,'POST',{});notify('Modelos atualizados sem geração de resposta.');},details);
   const models=service.chave_pendente?service.modelos_pendentes:service.modelos;
   models.slice(0,50).forEach(m=>{const prices=m.precos;let cost='Preço não informado';if(prices?.prompt!==undefined&&prices?.completion!==undefined)cost=`US$ ${Number(prices.prompt)*1e6} / ${Number(prices.completion)*1e6} por milhão de tokens de entrada / saída`;
    details.append(accountText('p',`${m.nome||m.id} · ${m.compativel?(m.estado||'Listado; geração não verificada'):'Compatibilidade não confirmada'} · ${cost}`));
    if(m.compativel&&!service.chave_pendente){const label=accountText('label','Português: avaliação da escola (opcional)');const select=document.createElement('select');for(const [value,text] of [['nao_avaliado','Não avaliado'],['aprovado','Adequado às leituras da escola'],['rejeitado','Não utilizar']])select.add(new Option(text,value));select.value=m.portugues||'nao_avaliado';select.onchange=()=>{const value=select.value;operation(async()=>{await accountApi(`/api/ia/servicos/${service.id}/modelos/${encodeURIComponent(m.id)}`,'PUT',{portugues:value});notify('Avaliação local registrada.');});};label.append(select);details.append(label);}
   });
   if(models.length>50)details.append(accountText('p',`Exibindo 50 de ${models.length} modelos. O roteamento considera todo o registro compatível.`));
   if(!models.length)details.append(accountText('p','Consulte os modelos ou verifique o serviço.'));
   row.append(details);list.append(row);
  });
  for(const [name,value] of Object.entries(saved.limites))advanced.elements[name].value=value;
  advanced.elements.preferencia.value=saved.politica.preferencia;
  advanced.elements.max_estimado_usd.value=saved.politica.max_estimado_usd??'';
  for(const task of ['chat','insights']){const select=advanced.elements[task];select.replaceChildren(new Option('Automático',''));saved.servicos.forEach(s=>s.modelos.filter(m=>m.compativel).forEach(m=>select.add(new Option(s.nome+' · '+(m.nome||m.id),s.id+'/'+m.id))));select.value=saved.politica.preferidos?.[task]||'';select.dispatchEvent(new Event('change'));}
  document.getElementById('ai-usage').textContent=`${saved.solicitacoes_24h} solicitações nas últimas 24 horas. Tokens informados: ${saved.tokens_24h??'não disponíveis'}.`;
  const attempts=document.getElementById('ai-attempts');attempts.replaceChildren();saved.tentativas.forEach(a=>attempts.append(accountText('p',`${a.provedor} · ${a.modelo} · ${a.operacao} · ${a.estado} · ${a.tokens??'—'} tokens`)));
  window.settingsSaved?.(advanced);
 }
 async function operation(action){
  if(busy)return;busy=true;window.settingsOperation?.(root,1);root.setAttribute('aria-busy','true');
  const controls=[...root.querySelectorAll('button,input,select')],states=controls.map(c=>c.disabled);controls.forEach(c=>c.disabled=true);
  try{await action();await refresh();await window.refreshBibiAvailability?.();}
  catch(error){notify(error.message,true);try{await refresh();await window.refreshBibiAvailability?.();}catch{}}
  finally{controls.forEach((c,i)=>{if(c.isConnected)c.disabled=states[i];});root.setAttribute('aria-busy','false');busy=false;window.settingsOperation?.(root,-1);}
 }
 document.getElementById('ai-add-service').onclick=()=>edit();document.getElementById('ai-service-cancel').onclick=resetForm;
 form.onsubmit=e=>{e.preventDefault();const name=form.elements.provedor.value;const data={custos_autorizados:form.elements.custos_autorizados.checked,privacidade_revisada:form.elements.privacidade_revisada.checked,limite_diario:Number(form.elements.limite_diario.value)};if(form.elements.chave.value)data.chave=form.elements.chave.value;
  operation(async()=>{await sensitive(`/api/ia/servicos/${name}`,'PUT',data);resetForm();notify('Serviço salvo. Verifique a conexão antes de ativar.');try{await accountApi(`/api/ia/servicos/${name}/modelos`,'POST',{});}catch(error){notify('Serviço salvo. '+error.message,true);}});
 };
 toggle.onchange=()=>{const value=toggle.checked;if(value&&!saved.pode_ativar){toggle.checked=false;notify('Verifique pelo menos um serviço e suas permissões antes de ativar.',true);return;}operation(async()=>{if(value)await sensitive('/api/ia/servicos','PUT',{ativa:true});else await accountApi('/api/ia/servicos','PUT',{ativa:false});notify(value?'IA ativada.':'IA desativada.');});};
 advanced.onsubmit=e=>{e.preventDefault();const data={};for(const name of ['por_hora','por_dia','concorrencia','max_tokens'])data[name]=Number(advanced.elements[name].value);data.politica={preferencia:advanced.elements.preferencia.value,max_estimado_usd:advanced.elements.max_estimado_usd.value===''?null:Number(advanced.elements.max_estimado_usd.value),preferidos:{}};for(const task of ['chat','insights'])if(advanced.elements[task].value)data.politica.preferidos[task]=advanced.elements[task].value;operation(async()=>{await accountApi('/api/ia/servicos','PUT',data);notify('Opções salvas.');});};
 try{await refresh();}catch(error){notify(error.message,true);throw error;}
};
window.initializeAISettings();
