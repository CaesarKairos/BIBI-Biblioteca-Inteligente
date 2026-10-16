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
    // Para administradores, buscamos a configuração atualizada via API.
    // Para não administradores, usamos o valor injetado globalmente.
    if (isAdminGlobal) {
        try {
            const res = await apiFetch('/api/config/quantidade_aulas/status');
            const data = await res.json();
            document.getElementById('cfg-qtd-aulas').value = data.quantidade;
            configAgenda.aulas = data.quantidade;
        } catch(e) {
            console.error("Erro ao carregar quantidade de aulas:", e);
            document.getElementById('cfg-qtd-aulas').value = 6;
            configAgenda.aulas = 6;
        }
    } else {
        configAgenda.aulas = quantidadeAulasGlobal;
    }
}

async function salvarConfigAgenda() {
    return runAction('salvarConfigAgenda', 'btn-salvar-config', async () => {
        if (!isAdminGlobal) return;
        const qtd = parseInt(document.getElementById('cfg-qtd-aulas').value);
        const res = await apiFetch('/api/config/quantidade_aulas/set', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({quantidade: qtd})
        });
        if (res.ok) {
            configAgenda.aulas = qtd;
            showToast("Configurações salvas!", "success");
            closeModal('modalConfigAgenda');
            carregarAgenda();
        } else {
            showToast("Erro ao salvar quantidade de aulas.", "error");
        }
    });
}


function abrirConfiguracoes(){location.assign('/configuracoes');}
function abrirModalConfiguracoes(){location.assign('/configuracoes');}
