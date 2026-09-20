// Funções auxiliares
let isAdminGlobal = document.body.dataset.admin === 'true';
// Quantidade de aulas injetada do backend (valor salvo no banco de dados)
let quantidadeAulasGlobal = Number(document.body.dataset.quantidadeAulas);

let confirmCallback = null;

document.getElementById('confirm-btn-sim').addEventListener('click', async () => {
    const callback = confirmCallback;
    if (!callback) return;
    const result = await runAction('confirmation', 'confirm-btn-sim', callback);
    if (result !== false) {
        closeModal('modalConfirmacao');
        confirmCallback = null;
    }
});

const CONFIG_STORAGE_KEY = 'bibiConfig';

document.addEventListener('paste', handleClipboardPaste);

let periodoAgendaSelect;
let categoriaManualSelect, categoriaEditSelect, tipoLeitorModalSelect;
let tipoRapidoSelect, prazoRapidoSelect, periodoRapidoSelect;

document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key >= '1' && e.key <= '5') {
        e.preventDefault();
        if (!isAdminGlobal) {
            // Apenas Ctrl+1 (acervo) e Ctrl+2 (agenda) são permitidos
            if (e.key === '1') {
                tab('acervo');
            } else if (e.key === '2') {
                tab('age');
            }
            return;
        }
        const tabs = ['dash', 'acervo', 'emp', 'age', 'lei'];
        tab(tabs[parseInt(e.key) - 1]);
    }
    if (e.key === 'Enter' && !e.ctrlKey && !e.altKey && !e.metaKey) {
        const openModalId = getOpenModalId();
        if (openModalId && !e.defaultPrevented && !e.target.closest('button, [role="button"], textarea')) {
            e.preventDefault();
            e.stopPropagation();
            triggerModalAction(openModalId);
        }
    }
});

document.addEventListener('click', (e) => {
    const suggestionsDiv = document.getElementById('rapido-nome-suggestions');
    if (suggestionsDiv && !suggestionsDiv.contains(e.target) && e.target.id !== 'rapido-nome') {
        suggestionsDiv.style.display = 'none';
    }
});

let agendamentoDetalhesId = null;

let todosLivros = [];
let todosLeitores = [];
let livroSelecionado = null;
let agendamentoAtualId = null;
let periodoAtual = 'Manhã';
let configAgenda = { aulas: quantidadeAulasGlobal };
let flatpickrInstance = null;
let graficoGenerosInstance = null;
let graficoHistoricoInstance = null;
let filtroEmprestimosAtual = 'todos';
let senhaEmprestimoGlobal = null;
let senhaAgendamentoGlobal = null;

window.onload = () => {
    iniciarRedimensionamentoPaineis();
    prepararAcessibilidade();
    verificarAdmin();
    const config = carregarConfig();
    if (config.darkMode) toggleTheme(true);
    else toggleTheme(false);
    initCustomSelects();
    carregarConfigAgenda();
    initFlatpickr();
    carregarAcervo();
    if (isAdminGlobal) {
        carregarDashboard();
        carregarLeitores();
    }
    carregarAgenda();
    aplicarVisibilidadeCamposLivro(true);
    aplicarVisibilidadeCamposLivro(false);
    aplicarVisibilidadeCamposEmprestimo();
    setupDragAndDrop('manual-capa-preview', 'manual-capa-url');
    setupDragAndDrop('edit-capa-preview', 'edit-capa-url');
    verificarObrigarLocalizacao();
    setInterval(async () => { if (isAdminGlobal) await apiFetch('/api/emprestimos/ativos'); }, 30 * 60 * 1000);
};

function prepararAcessibilidade() {
    document.querySelectorAll('.nav-menu li, .logo, .theme-item, .config-item, .card[data-bibi-onclick]').forEach(element => {
        element.tabIndex = 0;
        element.setAttribute('role', 'button');
        if (element.title) element.setAttribute('aria-label', element.title);
        element.addEventListener('keydown', event => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault(); element.click();
            }
        });
    });
    document.querySelectorAll('label:not([for])').forEach(label => {
        const input = label.nextElementSibling;
        if (input?.matches('input[id], textarea[id], select[id]')) label.htmlFor = input.id;
    });
    document.querySelectorAll('input[placeholder]:not([aria-label])').forEach(input => {
        if (!input.labels?.length) input.setAttribute('aria-label', input.placeholder);
    });
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const updateMascot = () => {
        const video = document.querySelector('.cat-waving');
        if (reduceMotion.matches) video.pause();
        else video.play().catch(() => {});
    };
    reduceMotion.addEventListener('change', updateMascot);
    updateMascot();
}
