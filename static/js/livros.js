function setupDragAndDrop(previewId, urlId) {
    const previewDiv = document.getElementById(previewId);
    if (!previewDiv) return;
    previewDiv.addEventListener('dragover', (e) => {
        e.preventDefault();
        previewDiv.style.opacity = '0.7';
    });
    previewDiv.addEventListener('dragleave', (e) => {
        e.preventDefault();
        previewDiv.style.opacity = '1';
    });
    previewDiv.addEventListener('drop', async (e) => {
        e.preventDefault();
        previewDiv.style.opacity = '1';
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) {
            await uploadImageFile(file, previewId, urlId);
        } else {
            showToast("Arraste apenas imagens", "warning");
        }
    });
}


async function uploadImageFile(file, previewId, urlId) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/upload', {method: 'POST', body: formData});
    if (res.ok) {
        const data = await res.json();
        document.getElementById(urlId).value = data.url;
        const previewDiv = document.getElementById(previewId);
        previewDiv.style.backgroundImage = `url(${data.url})`;
        previewDiv.classList.add('has-image');
        const textSpan = previewDiv.querySelector('.preview-text');
        if (textSpan) textSpan.style.display = 'none';
    } else {
        showToast("Erro no upload da capa", "error");
    }
}


async function handleClipboardPaste(e) {
    const items = e.clipboardData ? e.clipboardData.items : (e.originalEvent && e.originalEvent.clipboardData ? e.originalEvent.clipboardData.items : []);
    if (!items) return;
    for (let item of items) {
        if (item.type.indexOf('image') !== -1) {
            const blob = item.getAsFile();
            if (!blob) continue;
            let previewId, urlId;
            const manualModal = document.getElementById('modalManualLivro');
            const editModal = document.getElementById('modalEditarLivro');
            if (manualModal && manualModal.style.display === 'flex') {
                previewId = 'manual-capa-preview';
                urlId = 'manual-capa-url';
            } else if (editModal && editModal.style.display === 'flex') {
                previewId = 'edit-capa-preview';
                urlId = 'edit-capa-url';
            } else {
                continue;
            }
            e.preventDefault();
            await uploadImageFile(blob, previewId, urlId);
            break;
        }
    }
}

function previewCapaManual(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const previewDiv = document.getElementById('manual-capa-preview');
            previewDiv.style.backgroundImage = `url(${e.target.result})`;
            previewDiv.classList.add('has-image');
            const textSpan = previewDiv.querySelector('.preview-text');
            if (textSpan) textSpan.style.display = 'none';
        };
        reader.readAsDataURL(file);
        uploadCapa(file, 'manual-capa-url');
    }
}

function previewCapaEdit(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const previewDiv = document.getElementById('edit-capa-preview');
            previewDiv.style.backgroundImage = `url(${e.target.result})`;
            previewDiv.classList.add('has-image');
            const textSpan = previewDiv.querySelector('.preview-text');
            if (textSpan) textSpan.style.display = 'none';
        };
        reader.readAsDataURL(file);
        uploadCapa(file, 'edit-capa-url');
    }
}

async function uploadCapa(file, targetInputId) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/upload', {method: 'POST', body: formData});
    if (res.ok) {
        const data = await res.json();
        document.getElementById(targetInputId).value = data.url;
    } else {
        showToast("Erro no upload da capa", "error");
    }
}


function openModalManual() {
    closeModal('modalAddLivro');
    aplicarVisibilidadeCamposLivro(true);
    const previewDiv = document.getElementById('manual-capa-preview');
    previewDiv.style.backgroundImage = '';
    previewDiv.classList.remove('has-image');
    const textSpan = previewDiv.querySelector('.preview-text');
    if (textSpan) textSpan.style.display = 'flex';
    openModal('modalManualLivro');
}


async function carregarAcervo() {
    const res = await fetch('/api/livros');
    todosLivros = await res.json();
    aplicarFiltroAcervo();
}


function aplicarFiltroAcervo() {
    const termo = document.getElementById('busca-acervo').value.toLowerCase();
    const filtrados = todosLivros.filter(l => 
        l.titulo.toLowerCase().includes(termo) || (l.isbn && l.isbn.includes(termo))
    );
    exibirPrateleiras(filtrados);
}


function filtrarAcervo() {
    aplicarFiltroAcervo();
}


function exibirPrateleiras(livros) {
    const container = document.getElementById('acervo-prateleiras');
    container.innerHTML = '';
    const categorias = ['Ficção', 'Não-ficção', 'Poesia', 'Quadrinhos'];
    categorias.forEach(cat => {
        const livrosCat = livros.filter(l => l.categoria === cat);
        const shelfDiv = document.createElement('div');
        shelfDiv.className = 'shelf';
        shelfDiv.innerHTML = `<h3>${cat}</h3><div class="books-grid" id="grid-${cat.replace(/\s/g,'')}"></div><div class="shelf-base"></div>`;
        container.appendChild(shelfDiv);
        const grid = shelfDiv.querySelector('.books-grid');
        if (livrosCat.length > 0) {
            livrosCat.forEach(l => {
                const div = document.createElement('div');
                div.className = 'book';
                div.style.backgroundImage = `url(${l.capa})`;
                div.onclick = () => verDetalhes(l);
                grid.appendChild(div);
            });
        } else {
            const emptyMsg = document.createElement('p');
            emptyMsg.style.color = 'var(--light)';
            emptyMsg.style.fontStyle = 'italic';
            emptyMsg.innerText = 'Nenhum livro nesta prateleira.';
            grid.appendChild(emptyMsg);
        }
    });
}


function verDetalhes(l) {
    livroSelecionado = l;
    document.getElementById('info-vazio').style.display = 'none';
    document.getElementById('info-livro').style.display = 'block';
    document.getElementById('det-capa').style.backgroundImage = `url(${l.capa})`;
    document.getElementById('det-titulo').innerText = l.titulo;
    document.getElementById('det-autor').innerText = l.autor || 'Autor desconhecido';
    document.getElementById('det-ano').innerText = l.ano ? `Ano: ${l.ano}` : '';
    document.getElementById('det-temas').innerHTML = `<strong>Temas:</strong> ${l.temas || 'Não informado'}`;
    document.getElementById('det-desc').innerText = (l.descricao || 'Sem descrição.').substring(0, 250) + (l.descricao && l.descricao.length > 250 ? '...' : '');
    document.getElementById('det-estoque').innerText = l.disponivel;

    const btnEmprestar = document.getElementById('btn-emprestar');
    if (btnEmprestar) {
        if (l.disponivel <= 0) {
            btnEmprestar.disabled = true;
            btnEmprestar.title = "Não há exemplares disponíveis";
        } else {
            btnEmprestar.disabled = false;
            btnEmprestar.title = "";
        }
    }

    const config = carregarConfig();
    const btnExcluir = document.getElementById('btn-excluir-livro');
    if (btnExcluir) {
        btnExcluir.style.display = config.bloquearExcluirLivro ? 'none' : 'block';
    }
}


async function salvarLivro() {
    if (!isAdminGlobal) return;
    const isbn = document.getElementById('add-isbn').value;
    const qtd = document.getElementById('add-qtd').value;
    if(!isbn || !qtd) return showToast("Preencha todos os campos", "warning");
    const btn = document.getElementById('btn-buscar-salvar');
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="pulsing-dots"><span></span><span></span><span></span></span>';
    try {
        const res = await fetch('/api/livros', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({isbn, quantidade: qtd})
        });
        if(res.ok) {
            showToast("Livro adicionado!", "success");
            document.getElementById('add-isbn').value = '';
            document.getElementById('add-qtd').value = '';
            closeModal('modalAddLivro');
            carregarAcervo();
            if (isAdminGlobal) carregarDashboard();
        } else {
            const err = await res.json();
            showToast("Erro: " + err.erro, "error");
            document.getElementById('add-isbn').value = '';
            document.getElementById('add-qtd').value = '';
            closeModal('modalAddLivro');
        }
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    }
}


async function salvarLivroManual() {
    if (!isAdminGlobal) return;
    const titulo = document.getElementById('manual-titulo').value;
    const autor = document.getElementById('manual-autor').value;
    const qtd = document.getElementById('manual-qtd').value;
    if(!titulo || !autor || !qtd) return showToast("Preencha título, autor e quantidade.", "warning");

    let capaUrl = document.getElementById('manual-capa-url').value;
    if (!capaUrl) capaUrl = '/static/images/placeholder.png';

    const localizacao = document.getElementById('manual-localizacao') ? document.getElementById('manual-localizacao').value : '';
    const payload = {
        manual: true,
        isbn: document.getElementById('manual-isbn').value || null,
        titulo: titulo,
        autor: autor,
        ano: document.getElementById('manual-ano').value || null,
        descricao: document.getElementById('manual-descricao').value,
        temas: document.getElementById('manual-temas').value,
        categoria: document.getElementById('manual-categoria').value,
        quantidade: parseInt(qtd),
        capa: capaUrl,
        localizacao: localizacao
    };

    const res = await fetch('/api/livros', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    });
    if(res.ok) {
        showToast("Livro adicionado manualmente!", "success");
        document.getElementById('manual-isbn').value = '';
        document.getElementById('manual-titulo').value = '';
        document.getElementById('manual-autor').value = '';
        document.getElementById('manual-ano').value = '';
        document.getElementById('manual-descricao').value = '';
        document.getElementById('manual-temas').value = '';
        document.getElementById('manual-qtd').value = '1';
        document.getElementById('manual-capa-url').value = '';
        const previewDiv = document.getElementById('manual-capa-preview');
        previewDiv.style.backgroundImage = '';
        previewDiv.classList.remove('has-image');
        const textSpan = previewDiv.querySelector('.preview-text');
        if (textSpan) textSpan.style.display = 'flex';
        document.getElementById('manual-capa-file').value = '';
        categoriaManualSelect.setValue('Ficção');
        closeModal('modalManualLivro');
        carregarAcervo();
        if (isAdminGlobal) carregarDashboard();
    } else {
        const err = await res.json();
        showToast("Erro: " + err.erro, "error");
    }
}


function editarLivroSelecionado() {
    if (!isAdminGlobal) return;
    if(!livroSelecionado) return;
    document.getElementById('edit-id').value = livroSelecionado.id;
    document.getElementById('edit-titulo').value = livroSelecionado.titulo;
    document.getElementById('edit-autor').value = livroSelecionado.autor;
    document.getElementById('edit-ano').value = livroSelecionado.ano || '';
    document.getElementById('edit-descricao').value = livroSelecionado.descricao || '';
    document.getElementById('edit-temas').value = livroSelecionado.temas || '';
    document.getElementById('edit-categoria').value = livroSelecionado.categoria || 'Ficção';
    categoriaEditSelect.setValue(livroSelecionado.categoria || 'Ficção');
    document.getElementById('edit-estoque').value = livroSelecionado.estoque;
    document.getElementById('edit-disponivel').value = livroSelecionado.disponivel;
    if (document.getElementById('edit-localizacao')) {
        document.getElementById('edit-localizacao').value = livroSelecionado.localizacao || '';
    }
    const previewDiv = document.getElementById('edit-capa-preview');
    previewDiv.style.backgroundImage = `url(${livroSelecionado.capa})`;
    if (livroSelecionado.capa && livroSelecionado.capa !== '/static/images/placeholder.png') {
        previewDiv.classList.add('has-image');
        const textSpan = previewDiv.querySelector('.preview-text');
        if (textSpan) textSpan.style.display = 'none';
    } else {
        previewDiv.classList.remove('has-image');
        const textSpan = previewDiv.querySelector('.preview-text');
        if (textSpan) textSpan.style.display = 'flex';
    }
    document.getElementById('edit-capa-url').value = '';
    aplicarVisibilidadeCamposLivro(false);
    verificarObrigarLocalizacao();
    openModal('modalEditarLivro');
}


function aplicarVisibilidadeCamposLivro(isManual) {
    const config = carregarConfig();
    const prefixo = isManual ? 'manual' : 'edit';
    document.querySelector(`#modal${isManual ? 'ManualLivro' : 'EditarLivro'} .campo-ano`).style.display = config.campoAnoVisivel ? '' : 'none';
    document.querySelector(`#modal${isManual ? 'ManualLivro' : 'EditarLivro'} .campo-descricao`).style.display = config.campoDescricaoVisivel ? '' : 'none';
    document.querySelector(`#modal${isManual ? 'ManualLivro' : 'EditarLivro'} .campo-temas`).style.display = config.campoTemasVisivel ? '' : 'none';
    document.querySelector(`#modal${isManual ? 'ManualLivro' : 'EditarLivro'} .campo-categoria`).style.display = config.campoCategoriaVisivel ? '' : 'none';
}


async function verificarObrigarLocalizacao() {
    const res = await fetch('/api/config/obrigar_localizacao_livro/status');
    const data = await res.json();
    const obrigar = data.ativo;
    const manualField = document.getElementById('campo-localizacao-manual');
    const editField = document.getElementById('campo-localizacao-edit');
    if (manualField) manualField.style.display = obrigar ? 'block' : 'none';
    if (editField) editField.style.display = obrigar ? 'block' : 'none';
    if (obrigar) {
        if (manualField) manualField.querySelector('label').innerHTML = 'Localização (Prateleira) *';
        if (editField) editField.querySelector('label').innerHTML = 'Localização (Prateleira)';
    } else {
        if (manualField) manualField.querySelector('label').innerHTML = 'Localização (Prateleira)';
    }
}


async function salvarEdicaoLivro() {
    if (!isAdminGlobal) return;
    const id = document.getElementById('edit-id').value;
    const payload = {
        titulo: document.getElementById('edit-titulo').value,
        autor: document.getElementById('edit-autor').value,
        ano: document.getElementById('edit-ano').value,
        descricao: document.getElementById('edit-descricao').value,
        temas: document.getElementById('edit-temas').value,
        categoria: document.getElementById('edit-categoria').value,
        estoque: parseInt(document.getElementById('edit-estoque').value),
        disponivel: parseInt(document.getElementById('edit-disponivel').value),
        localizacao: document.getElementById('edit-localizacao') ? document.getElementById('edit-localizacao').value : ''
    };
    const novaCapa = document.getElementById('edit-capa-url').value;
    if (novaCapa) payload.capa = novaCapa;

    const res = await fetch(`/api/livros/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    });
    if(res.ok) {
        showToast("Livro atualizado!", "success");
        closeModal('modalEditarLivro');
        carregarAcervo();
        if(livroSelecionado && livroSelecionado.id == id) {
            livroSelecionado = {...livroSelecionado, ...payload};
            verDetalhes(livroSelecionado);
        }
    } else {
        showToast("Erro ao atualizar", "error");
    }
}


function confirmarExclusaoLivro() {
    if (!isAdminGlobal) return;
    if(!livroSelecionado) return;
    confirmAction("Excluir Livro", `Deseja realmente excluir "${livroSelecionado.titulo}"?`, async () => {
        await fetch(`/api/livros/${livroSelecionado.id}`, {method: 'DELETE'});
        showToast("Livro excluído.", "success");
        livroSelecionado = null;
        document.getElementById('info-livro').style.display = 'none';
        document.getElementById('info-vazio').style.display = 'block';
        carregarAcervo();
        if (isAdminGlobal) carregarDashboard();
    });
}
