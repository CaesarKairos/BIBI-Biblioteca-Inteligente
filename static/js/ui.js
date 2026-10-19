async function verificarAdmin() {
    // j� temos isAdminGlobal vindo do backend
    // Aplica restrições visuais no frontend
    const adminElements = document.querySelectorAll('.admin-only');
    adminElements.forEach(el => {
        if (!isAdminGlobal) el.style.display = 'none';
        else el.style.display = '';
    });
    // Se não for admin, remove a aba ativa que não deveria estar visível
    if (!isAdminGlobal) {
        const activeTab = document.querySelector('.section.active');
        if (activeTab && !['acervo', 'age'].includes(activeTab.id)) {
            tab('acervo');
        }
    }
}


function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerText = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}


const modalFocus = new Map();
const modalStack = [];
function openModal(id) {
    if(id==='modalLeitor')aplicarVisibilidadeCamposEmprestimo();
    const modal = document.getElementById(id);
    modalFocus.set(id, document.activeElement);
    const previousIndex = modalStack.indexOf(id);
    if (previousIndex >= 0) modalStack.splice(previousIndex, 1);
    modalStack.push(id);
    modal.style.zIndex = 1000 + modalStack.length;
    modal.style.display = 'flex';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    const heading = modal.querySelector('h3');
    if (heading) {
        if (!heading.id) heading.id = `${id}-title`;
        modal.setAttribute('aria-labelledby', heading.id);
    }
    requestAnimationFrame(() => {
        modal.querySelector('input:not([type="hidden"]), textarea, button')?.focus();
    });
}

function closeModal(id) {
    document.getElementById(id).style.display = 'none';
    const index = modalStack.indexOf(id);
    if (index >= 0) modalStack.splice(index, 1);
    const target = modalFocus.get(id);
    if (target?.isConnected) target.focus({preventScroll: true});
    modalFocus.delete(id);
}

document.addEventListener('keydown', event => {
    if(document.querySelector('dialog[open]'))return;
    const id = modalStack[modalStack.length - 1];
    if (!id) return;
    if (event.key === 'Escape') { event.preventDefault(); closeModal(id); }
    if (event.key !== 'Tab') return;
    const focusable = [...document.getElementById(id).querySelectorAll('button, input, textarea, select, [tabindex="0"]')]
        .filter(el => !el.disabled && el.getClientRects().length);
    const first = focusable[0], last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
});

function confirmAction(titulo, mensagem, callback) {
    document.getElementById('confirm-titulo').innerText = titulo;
    document.getElementById('confirm-mensagem').innerText = mensagem;
    confirmCallback = callback;
    openModal('modalConfirmacao');
}

function toggleTheme(ativar) {
    if (ativar === undefined) ativar = !document.body.classList.contains('dark-mode');
    if (ativar) {
        document.body.classList.add('dark-mode');
        document.getElementById('theme-icon').innerHTML = '<path d="M8 11a3 3 0 1 1 0-6 3 3 0 0 1 0 6m0 1a4 4 0 1 0 0-8 4 4 0 0 0 0 8M8 0a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 0m0 13a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 13m8-5a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2a.5.5 0 0 1 .5.5M3 8a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2A.5.5 0 0 1 3 8m10.657-5.657a.5.5 0 0 1 0 .707l-1.414 1.415a.5.5 0 1 1-.707-.708l1.414-1.414a.5.5 0 0 1 .707 0m-9.193 9.193a.5.5 0 0 1 0 .707L3.05 13.657a.5.5 0 0 1-.707-.707l1.414-1.414a.5.5 0 0 1 .707 0m9.193 2.121a.5.5 0 0 1-.707 0l-1.414-1.414a.5.5 0 0 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .707M4.464 4.465a.5.5 0 0 1-.707 0L2.343 3.05a.5.5 0 1 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .708"/>';
    } else {
        document.body.classList.remove('dark-mode');
        document.getElementById('theme-icon').innerHTML = '<path d="M6 .278a.77.77 0 0 1 .08.858 7.2 7.2 0 0 0-.878 3.46c0 4.021 3.278 7.277 7.318 7.277q.792-.001 1.533-.16a.79.79 0 0 1 .81.316.73.73 0 0 1-.031.893A8.35 8.35 0 0 1 8.344 16C3.734 16 0 12.286 0 7.71 0 4.266 2.114 1.312 5.124.06A.75.75 0 0 1 6 .278M4.858 1.311A7.27 7.27 0 0 0 1.025 7.71c0 4.02 3.279 7.276 7.319 7.276a7.32 7.32 0 0 0 5.205-2.162q-.506.063-1.029.063c-4.61 0-8.343-3.714-8.343-8.29 0-1.167.242-2.278.681-3.286"/><path d="M10.794 3.148a.217.217 0 0 1 .412 0l.387 1.162c.173.518.579.924 1.097 1.097l1.162.387a.217.217 0 0 1 0 .412l-1.162.387a1.73 1.73 0 0 0-1.097 1.097l-.387 1.162a.217.217 0 0 1-.412 0l-.387-1.162A1.73 1.73 0 0 0 9.31 6.593l-1.162-.387a.217.217 0 0 1 0-.412l1.162-.387a1.73 1.73 0 0 0 1.097-1.097zM13.863.099a.145.145 0 0 1 .274 0l.258.774c.115.346.386.617.732.732l.774.258a.145.145 0 0 1 0 .274l-.774.258a1.16 1.16 0 0 0-.732.732l-.258.774a.145.145 0 0 1-.274 0l-.258-.774a1.16 1.16 0 0 0-.732-.732l-.774-.258a.145.145 0 0 1 0-.274l.774-.258c.346-.115.617-.386.732-.732z"/>';
    }
    document.getElementById("theme-toggle-btn").setAttribute("aria-pressed",String(ativar));
    const config = carregarConfig();
    config.darkMode = ativar;
    salvarConfig(config);
    if (isAdminGlobal) {
        carregarGraficoGeneros();
        carregarGraficoHistorico();
    }
    verificarObrigarLocalizacao();
}


class CustomSelect {
    constructor(container, options, onChange, defaultValue = null) {
        this.container=container;this.options=options;this.onChange=onChange;
        this.selectedValue=defaultValue ?? options[0]?.value ?? '';
        this.render();
    }
    render(){
        this.container.replaceChildren();this.container.className='custom-select';
        const control=document.createElement('button');control.type='button';control.className='select-selected';
        control.setAttribute('role','combobox');control.setAttribute('aria-haspopup','listbox');control.setAttribute('aria-expanded','false');
        control.setAttribute('aria-label',this.container.dataset.label || this.container.previousElementSibling?.textContent || 'Selecionar opção');
        if(this.container.dataset.descriptionId)control.setAttribute('aria-describedby',this.container.dataset.descriptionId);
        const label=document.createElement('span');control.append(label);
        const list=document.createElement('div');list.className='select-items';list.role='listbox';list.id='bibi-options-'+crypto.getRandomValues(new Uint32Array(1))[0];control.setAttribute('aria-controls',list.id);
        this.options.forEach((opt,index)=>{const item=document.createElement('div');item.textContent=opt.text;item.dataset.value=String(opt.value);item.role='option';item.id=list.id+'-'+index;
            // Keep focus on the combobox until click commits the option.
            item.addEventListener('mousedown',event=>event.preventDefault());
            item.addEventListener('click',()=>{if(opt.disabled)return;this.setValue(opt.value);this.close();control.focus();});list.append(item);});
        control.addEventListener('click',()=>this.toggle());
        control.addEventListener('keydown',event=>{
            if(['ArrowDown','ArrowUp','Home','End'].includes(event.key)){
                event.preventDefault();event.stopPropagation();const enabled=this.options.filter(o=>!o.disabled);if(!enabled.length)return;
                let index=enabled.findIndex(o=>String(o.value)===String(this.selectedValue));
                index=event.key==='Home'?0:event.key==='End'?enabled.length-1:(index+(event.key==='ArrowDown'?1:-1)+enabled.length)%enabled.length;
                this.setValue(enabled[index].value);
            }else if(event.key==='Escape'&&list.style.display==='block'){event.preventDefault();event.stopPropagation();this.close();}
        });
        this.container.append(control,list);this.sync();
        if(!this.outside){this.outside=event=>{if(!this.container.isConnected){document.removeEventListener('click',this.outside);return;}if(!this.container.contains(event.target))this.close();};document.addEventListener('click',this.outside);}
        if(!this.focusOut){this.focusOut=event=>{if(!this.container.contains(event.relatedTarget))this.close();};this.container.addEventListener('focusout',this.focusOut);}
    }
    toggle(){const list=this.container.querySelector('.select-items');const opened=list.style.display!=='block';list.style.display=opened?'block':'none';this.container.querySelector('.select-selected').setAttribute('aria-expanded',String(opened));}
    close(){this.container.querySelector('.select-items').style.display='none';this.container.querySelector('.select-selected').setAttribute('aria-expanded','false');}
    sync(){
        const selected=this.options.find(o=>String(o.value)===String(this.selectedValue));const control=this.container.querySelector('.select-selected');control.querySelector('span').textContent=selected?.text ?? '';
        this.container.querySelectorAll('[role=option]').forEach(item=>{const active=item.dataset.value===String(this.selectedValue);item.classList.toggle('same-as-selected',active);item.setAttribute('aria-selected',String(active));if(active)control.setAttribute('aria-activedescendant',item.id);});
    }
    setValue(value){this.selectedValue=value;this.sync();if(this.onChange)this.onChange(value);}
    getValue(){return this.selectedValue;}
}

// Native controls remain the source of truth and the no-JavaScript fallback.
function enhanceNativeSelects(){
 document.querySelectorAll('select:not([multiple])').forEach(select=>{
  if(select.dataset.enhanced)return;
  const wrapper=document.createElement('div');wrapper.dataset.label=select.getAttribute('aria-label') || Array.from(select.labels?.[0]?.childNodes||[]).filter(n=>n.nodeType===3).map(n=>n.textContent).join('').trim() || 'Selecionar opção';select.after(wrapper);
  wrapper.dataset.descriptionId=select.getAttribute('aria-describedby')||'';
  const options=()=>Array.from(select.options,o=>({value:o.value,text:o.text,disabled:o.disabled}));
  const component=new CustomSelect(wrapper,options(),value=>{if(select.disabled)return;select.value=value;select.dispatchEvent(new Event('change',{bubbles:true}));},select.value);
  wrapper.querySelector('button').disabled=select.disabled;
  select.dataset.enhanced='true';select.hidden=true;
  for(const property of ['value','selectedIndex']){
   const descriptor=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,property);
   Object.defineProperty(select,property,{configurable:true,get(){return descriptor.get.call(this);},set(value){descriptor.set.call(this,value);component.selectedValue=this.value;component.sync();}});
  }

  select.addEventListener('change',()=>{component.selectedValue=select.value;component.sync();});
  select.addEventListener('invalid',()=>wrapper.querySelector('button').focus());
  new MutationObserver(()=>{component.options=options();component.selectedValue=select.value;component.render();wrapper.querySelector('button').disabled=select.disabled;}).observe(select,{childList:true,subtree:true,attributes:true,attributeFilter:['disabled','selected']});
  select.form?.addEventListener('reset',()=>setTimeout(()=>{component.selectedValue=select.value;component.sync();}));
 });
}
document.addEventListener('DOMContentLoaded',()=>{
 enhanceNativeSelects();
 new MutationObserver(records=>{if(records.some(r=>Array.from(r.addedNodes).some(n=>n.nodeType===1&&(n.matches('select')||n.querySelector('select')))))enhanceNativeSelects();}).observe(document.body,{childList:true,subtree:true});
});


function initCustomSelects() {
    const periodoAgendaContainer = document.getElementById('custom-select-periodo-agenda');
    if (periodoAgendaContainer) {
        periodoAgendaSelect = new CustomSelect(periodoAgendaContainer, [
            {value: 'Manhã', text: 'Manhã'},
            {value: 'Tarde', text: 'Tarde'},
            {value: 'Noite', text: 'Noite'}
        ], (val) => {
            document.getElementById('agenda-periodo').value = val;
            periodoAtual = val;
            carregarAgenda();
        }, 'Manhã');
    }
    const catManualContainer = document.getElementById('custom-select-categoria-manual');
    if (catManualContainer) {
        categoriaManualSelect = new CustomSelect(catManualContainer, [
            {value: 'Ficção', text: 'Ficção'},
            {value: 'Não-ficção', text: 'Não-ficção'},
            {value: 'Poesia', text: 'Poesia'},
            {value: 'Quadrinhos', text: 'Quadrinhos'}
        ], (val) => {
            document.getElementById('manual-categoria').value = val;
        }, 'Ficção');
    }
    const catEditContainer = document.getElementById('custom-select-categoria-edit');
    if (catEditContainer) {
        categoriaEditSelect = new CustomSelect(catEditContainer, [
            {value: 'Ficção', text: 'Ficção'},
            {value: 'Não-ficção', text: 'Não-ficção'},
            {value: 'Poesia', text: 'Poesia'},
            {value: 'Quadrinhos', text: 'Quadrinhos'}
        ], (val) => {
            document.getElementById('edit-categoria').value = val;
        }, 'Ficção');
    }
    const tipoLeitorModalContainer = document.getElementById('custom-select-tipo-leitor');
    if (tipoLeitorModalContainer) {
        tipoLeitorModalSelect = new CustomSelect(tipoLeitorModalContainer, [
            {value: 'estudante', text: 'Estudante'},
            {value: 'professor', text: 'Professor'}
        ], (val) => {
            document.getElementById('leitor-tipo').value = val;
            toggleLeitorTipo();
        }, 'estudante');
    }
    const tipoRapidoContainer = document.getElementById('custom-select-tipo-rapido');
    if (tipoRapidoContainer) {
        tipoRapidoSelect = new CustomSelect(tipoRapidoContainer, [
            {value: 'estudante', text: 'Estudante'},
            {value: 'professor', text: 'Professor'}
        ], (val) => {
            document.getElementById('rapido-tipo').value = val;
            leitorSelecionadoEmprestimo = null;
            document.getElementById('rapido-aluno').style.display = val === 'estudante' ? 'block' : 'none';
            document.getElementById('rapido-professor').style.display = val === 'professor' ? 'block' : 'none';
            aplicarVisibilidadeCamposEmprestimo();
        }, 'estudante');
    }
    const prazoRapidoContainer = document.getElementById('custom-select-prazo-rapido');
    if (prazoRapidoContainer) {
        prazoRapidoSelect = new CustomSelect(prazoRapidoContainer, [
            {value: '7', text: '7 dias'},
            {value: '14', text: '14 dias'},
            {value: '21', text: '21 dias'},
            {value: '28', text: '28 dias'}
        ], (val) => {
            document.getElementById('rapido-prazo').value = val;
        }, '7');
    }
    const periodoRapidoContainer = document.getElementById('custom-select-periodo-rapido');
    if (periodoRapidoContainer) {
        periodoRapidoSelect = new CustomSelect(periodoRapidoContainer, [
            {value: 'Manhã', text: 'Manhã'},
            {value: 'Tarde', text: 'Tarde'},
            {value: 'Noite', text: 'Noite'}
        ], (val) => {
            document.getElementById('rapido-periodo').value = val;
        }, 'Manhã');
    }
}


function getOpenModalId() {
    if (modalStack.length) return modalStack[modalStack.length - 1];
    const modals = ['modalAddLivro', 'modalManualLivro', 'modalEditarLivro', 'modalAgendamento',
                   'modalLeitor', 'modalEmprestimoRapido', 'modalConfirmacao',
                   'modalAtrasos', 'modalDevolucoesHoje', 'modalSenhaConfig', 'modalDetalhesAgendamento'];
    for (const id of modals) {
        const el = document.getElementById(id);
        if (el && el.style.display === 'flex') return id;
    }
    return null;
}


function triggerModalAction(modalId) {
    switch (modalId) {
        case 'modalAddLivro': document.getElementById('btn-buscar-salvar').click(); break;
        case 'modalManualLivro': document.getElementById('btn-salvar-manual').click(); break;
        case 'modalEditarLivro': document.getElementById('btn-salvar-edicao').click(); break;
        case 'modalAgendamento':
            if (document.getElementById('agenda-form').style.display !== 'none') document.getElementById('btn-agendar').click();
            break;
        case 'modalLeitor': document.getElementById('btn-salvar-leitor').click(); break;
        case 'modalEmprestimoRapido': document.getElementById('btn-confirmar-emprestimo').click(); break;
        case 'modalConfirmacao': document.getElementById('confirm-btn-sim').click(); break;
        case 'modalSenhaConfig': document.getElementById('btn-senha').click(); break;
        default: break;
    }
}


function tab(id) {
    if (!isAdminGlobal && id !== 'acervo') return;
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-menu li').forEach(l => l.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    document.getElementById('m-'+id).classList.add('active');
    document.querySelectorAll('.nav-menu li').forEach(item => item.setAttribute('aria-current', item.id === `m-${id}` ? 'page' : 'false'));
    document.querySelector('.content-area').scrollTop = 0;
    if(id === 'acervo') carregarAcervo();
    if(id === 'dash' && isAdminGlobal) carregarDashboard();
    if(id === 'lei' && isAdminGlobal) carregarLeitores();
    if(id === 'age') {
        const hiddenInput = document.getElementById('agenda-data');
        if (!hiddenInput.value && flatpickrInstance) {
            const today = new Date();
            flatpickrInstance.setDate(today);
        }
        carregarAgenda();
    }
    if(id === 'emp' && isAdminGlobal) {
        if (filtroEmprestimosAtual) {
            filtrarEmprestimos(filtroEmprestimosAtual);
        } else {
            carregarEmprestimosAtivos();
        }
    }
}


class ApiError extends Error {}

async function apiFetch(url, options) {
    options = {...options, headers: new Headers(options?.headers || {})};
    options.headers.set('X-CSRF-Token', document.querySelector('meta[name=csrf-token]')?.content || '');
    try {
        const response = await window.fetch(url, options);
        let payload;
        try { payload = await response.clone().json(); }
        catch { throw new ApiError('O servidor retornou uma resposta inválida. Tente novamente.'); }
        if (!response.ok) throw new ApiError(payload.erro || 'Não foi possível concluir a operação.');
        return response;
    } catch (error) {
        const failure = error instanceof ApiError ? error : new ApiError('Não foi possível conectar ao servidor. Verifique a conexão e tente novamente.');
        showToast(failure.message, 'error');
        throw failure;
    }
}

// Esperas de eventos do DOM não consomem promises. Erros HTTP já têm feedback.
window.addEventListener('unhandledrejection', event => {
    if (event.reason instanceof ApiError) event.preventDefault();
});

const pendingActions = new Set();
async function runAction(key, buttonId, action) {
    if (pendingActions.has(key)) return false;
    pendingActions.add(key);
    const button = buttonId.startsWith('#') ? document.querySelector(buttonId) : document.getElementById(buttonId);
    const disabled = button?.disabled;
    if (button) button.disabled = true;
    try {
        return await action();
    } catch (error) {
        if (!(error instanceof ApiError)) {
            console.error('Falha na operação', error);
            showToast('Não foi possível concluir a operação. Tente novamente.', 'error');
        }
        return false;
    } finally {
        pendingActions.delete(key);
        if (button) button.disabled = disabled;
    }
}

function textElement(tag, value, className = '') {
    const element = document.createElement(tag);
    element.textContent = value ?? '';
    if (className) element.className = className;
    return element;
}

function tornarAcionavel(element) {
    element.tabIndex = 0;
    element.setAttribute('role', 'button');
    element.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault(); event.stopPropagation(); element.click();
        }
    });
}

function coverBackground(element, value) {
    const url = String(value || '/static/images/placeholder.png');
    element.style.backgroundImage = 'url(' + JSON.stringify(url) + ')';
}
