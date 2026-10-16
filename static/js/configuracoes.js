function carregarConfig() {
    const str = localStorage.getItem(CONFIG_STORAGE_KEY);
    if (str) {
        try { return JSON.parse(str); } catch(e) {}
    }
    return {
        darkMode: false,
        mostrarColunaAula: true,
        campoDescricaoVisivel: true,
        campoTemasVisivel: true,
        campoAnoVisivel: true,
        campoCategoriaVisivel: true,
        campoNumeroUsuario: false,
        bloquearExcluirLivro: false
    };
}

function salvarConfig(config) {
    localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(config));
}


async function carregarConfigAgenda() {
    configAgenda.aulas = quantidadeAulasGlobal;
    if(isAdminGlobal){try{configAgenda.aulas=(await accountApi('/api/config/quantidade_aulas/status')).quantidade;}catch(error){showToast(error.message,'error');}}
}
function abrirConfiguracoes(){return window.abrirConfiguracoesCompartilhadas();}
function abrirModalConfiguracoes(){return window.abrirConfiguracoesCompartilhadas();}
