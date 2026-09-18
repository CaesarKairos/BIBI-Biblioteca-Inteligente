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


function openModal(id) { document.getElementById(id).style.display='flex'; }

function closeModal(id) { document.getElementById(id).style.display='none'; }

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
    const config = carregarConfig();
    config.darkMode = ativar;
    salvarConfig(config);
    carregarGraficoGeneros();
    carregarGraficoHistorico();
    verificarObrigarLocalizacao();
}


class CustomSelect {
    constructor(container, options, onChange, defaultValue = null) {
        this.container = container;
        this.options = options;
        this.onChange = onChange;
        this.selectedValue = defaultValue || (options.length > 0 ? options[0].value : '');
        this.render();
    }
    render() {
        this.container.innerHTML = '';
        this.container.className = 'custom-select';
        const selectedDiv = document.createElement('div');
        selectedDiv.className = 'select-selected';
        const selectedOption = this.options.find(opt => opt.value == this.selectedValue) || this.options[0];
        selectedDiv.appendChild(textElement('span', selectedOption ? selectedOption.text : ''));
        this.container.appendChild(selectedDiv);

        const itemsDiv = document.createElement('div');
        itemsDiv.className = 'select-items';
        this.options.forEach(opt => {
            const optDiv = document.createElement('div');
            optDiv.textContent = opt.text;
            if (opt.value == this.selectedValue) {
                optDiv.classList.add('same-as-selected');
            }
            optDiv.addEventListener('click', () => {
                this.setValue(opt.value);
                this.close();
            });
            itemsDiv.appendChild(optDiv);
        });
        this.container.appendChild(itemsDiv);

        selectedDiv.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle();
        });
        document.addEventListener('click', () => this.close());
    }
    toggle() {
        const items = this.container.querySelector('.select-items');
        items.style.display = items.style.display === 'block' ? 'none' : 'block';
    }
    close() {
        const items = this.container.querySelector('.select-items');
        if (items) items.style.display = 'none';
    }
    setValue(value) {
        this.selectedValue = value;
        const selectedOption = this.options.find(opt => opt.value == value);
        this.container.querySelector('.select-selected span').textContent = selectedOption ? selectedOption.text : '';
        this.container.querySelectorAll('.select-items div').forEach(div => {
            div.classList.remove('same-as-selected');
            if (div.textContent === (selectedOption ? selectedOption.text : '')) {
                div.classList.add('same-as-selected');
            }
        });
        if (this.onChange) this.onChange(value);
    }
    getValue() {
        return this.selectedValue;
    }
}


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
    const modals = ['modalAddLivro', 'modalManualLivro', 'modalEditarLivro', 'modalAgendamento',
                   'modalLeitor', 'modalEmprestimoRapido', 'modalConfigAgenda', 'modalConfirmacao',
                   'modalAtrasos', 'modalDevolucoesHoje', 'modalSenhaConfig', 'modalConfiguracoes', 'modalDetalhesAgendamento'];
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
        case 'modalConfigAgenda': document.getElementById('btn-salvar-config').click(); break;
        case 'modalConfirmacao': document.getElementById('confirm-btn-sim').click(); break;
        case 'modalSenhaConfig': document.getElementById('btn-senha').click(); break;
        case 'modalConfiguracoes': salvarConfigGerais(); break;
        default: break;
    }
}


function tab(id) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-menu li').forEach(l => l.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    document.getElementById('m-'+id).classList.add('active');
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

function coverBackground(element, value) {
    const url = String(value || '/static/images/placeholder.png');
    element.style.backgroundImage = 'url(' + JSON.stringify(url) + ')';
}
