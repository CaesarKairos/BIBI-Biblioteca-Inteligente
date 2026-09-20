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
    const res = await apiFetch('/api/upload', {method: 'POST', body: formData});
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
    const res = await apiFetch('/api/upload', {method: 'POST', body: formData});
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
    const res = await apiFetch('/api/livros');
    todosLivros = await res.json();
    aplicarFiltroAcervo();
    if (livroSelecionado) {
        const atualizado = todosLivros.find(l => l.id === livroSelecionado.id);
        if (atualizado) verDetalhes(atualizado);
        else fecharDetalhes();
    }
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


// Contrato futuro: uma lista de IDs ordenados. null ativa apenas o fallback visual
// determinístico; [] representa uma seleção explicitamente vazia. Não há IA aqui.
let idsRecomendacoesBibi = null;
function definirRecomendacoesBibi(ids) {
    idsRecomendacoesBibi = Array.isArray(ids) ? [...new Set(ids)] : null;
    aplicarFiltroAcervo();
}

function criarLivroPrateleira(l) {
    const book = document.createElement('button');
    book.type = 'button';
    book.className = 'book';
    book.dataset.livroId = l.id;
    const indisponivel = Number(l.disponivel) <= 0;
    book.classList.toggle('unavailable', indisponivel);
    book.title = `${l.titulo} — ${l.autor || 'Autor desconhecido'}${indisponivel ? ' — Não existem exemplares disponíveis' : ''}`;
    book.setAttribute('aria-label', book.title);
    book.setAttribute('aria-pressed', String(livroSelecionado?.id === l.id));
    coverBackground(book, l.capa);
    book.onclick = () => {
        verDetalhes(l);
        if (window.matchMedia('(max-width: 700px)').matches) {
            document.querySelector('.right-bar').scrollIntoView({block: 'start'});
        }
    };
    return book;
}

function exibirPrateleiras(livros) {
    const container = document.getElementById('acervo-prateleiras');
    container.innerHTML = '';
    const especial = document.createElement('section');
    especial.className = 'shelf shelf-bibi';
    especial.id = 'prateleira-bibi';
    especial.setAttribute('aria-labelledby', 'recomendacoes-titulo');
    especial.dataset.contentSource = idsRecomendacoesBibi === null ? 'placeholder' : 'ids';
    especial.innerHTML = '<div class="shelf-heading"><h3 id="recomendacoes-titulo"><span class="bibi-cat-icon" aria-hidden="true"></span>Recomendações da BIBI</h3><span class="preview-badge">Em preparação</span></div><p class="shelf-note">Uma amostra do acervo. Recomendações inteligentes chegam no futuro.</p><div class="books-grid"></div><div class="shelf-base"></div>';
    const demonstracao = idsRecomendacoesBibi === null
        ? [...livros].sort((a, b) => a.id - b.id).slice(0, 8)
        : idsRecomendacoesBibi.map(id => livros.find(l => l.id === id)).filter(Boolean);
    const especialGrid = especial.querySelector('.books-grid');
    demonstracao.forEach(l => especialGrid.appendChild(criarLivroPrateleira(l)));
    if (!demonstracao.length) especialGrid.appendChild(textElement('p', 'Nenhum livro para exibir nesta seleção.', 'shelf-empty'));
    container.appendChild(especial);
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
                grid.appendChild(criarLivroPrateleira(l));
            });
        } else {
            const emptyMsg = document.createElement('p');
            emptyMsg.className = 'shelf-empty';
            emptyMsg.style.color = 'var(--light)';
            emptyMsg.style.fontStyle = 'italic';
            emptyMsg.innerText = 'Nenhum livro nesta prateleira.';
            grid.appendChild(emptyMsg);
        }
    });
}


function verDetalhes(l) {
    const mudouLivro = livroSelecionado?.id !== l.id;
    livroSelecionado = l;
    document.getElementById('info-vazio').style.display = 'none';
    document.getElementById('info-livro').style.display = 'block';
    document.querySelectorAll('.book[data-livro-id]').forEach(book => {
        book.setAttribute('aria-pressed', String(book.dataset.livroId === String(l.id)));
    });
    const details = document.getElementById('info-livro');
    if (mudouLivro) document.querySelector('.right-bar').scrollTop = 0;
    if (mudouLivro && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        details.getAnimations().forEach(animation => animation.cancel());
        details.animate([{opacity: 0, transform: 'translateY(5px)'}, {opacity: 1, transform: 'translateY(0)'}], {duration: 200});
    }
    coverBackground(document.getElementById('det-capa'), l.capa);
    document.getElementById('det-titulo').innerText = l.titulo;
    document.getElementById('det-autor').innerText = l.autor || 'Autor desconhecido';
    document.getElementById('det-ano').innerText = l.ano ? `Ano: ${l.ano}` : '';
    for (const [id, value] of [['det-paginas', l.numero_paginas ? `${l.numero_paginas} páginas` : ''], ['det-isbn', l.isbn && !l.isbn.startsWith('MANUAL_') ? `ISBN: ${l.isbn}` : ''], ['det-localizacao', l.localizacao ? `Localização: ${l.localizacao}` : '']]) {
        const field = document.getElementById(id);
        field.textContent = value;
        field.hidden = !value;
    }
    document.getElementById('det-temas').replaceChildren(textElement('strong', 'Temas:'), document.createTextNode(' ' + (l.temas || 'Não informado')));
    document.getElementById('det-desc').innerText = l.descricao || 'Sem descrição.';
    document.getElementById('det-estoque').innerText = l.disponivel;
    document.querySelector('.availability').classList.toggle('unavailable', Number(l.disponivel) <= 0);

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


function fecharDetalhes() {
    const id = livroSelecionado?.id;
    const devolverFoco = document.getElementById('info-livro').contains(document.activeElement);
    livroSelecionado = null;
    document.getElementById('info-livro').style.display = 'none';
    document.getElementById('info-vazio').style.display = 'block';
    document.querySelectorAll('.book').forEach(book => book.setAttribute('aria-pressed', 'false'));
    if (devolverFoco) document.querySelector(`.book[data-livro-id="${id}"]`)?.focus({preventScroll: true});
}

function validarCampoPaginas(prefixo) {
    const input = document.getElementById(`${prefixo}-paginas`);
    if (!input.checkValidity() || (input.value && !Number.isSafeInteger(Number(input.value)))) {
        input.reportValidity();
        input.focus();
        showToast('Número de páginas deve ser um inteiro positivo válido.', 'warning');
        return false;
    }
    return true;
}

async function salvarLivro() {
    return runAction('salvarLivro', 'btn-buscar-salvar', async () => {
        if (!isAdminGlobal) return;
        const isbn = document.getElementById('add-isbn').value;
        const qtd = document.getElementById('add-qtd').value;
        if(!isbn || !qtd) return showToast("Preencha todos os campos", "warning");
        const btn = document.getElementById('btn-buscar-salvar');
        const originalHTML = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="pulsing-dots"><span></span><span></span><span></span></span>';
        try {
            const res = await apiFetch('/api/livros', {
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
    });
}


async function salvarLivroManual() {
    return runAction('salvarLivroManual', 'btn-salvar-manual', async () => {
        if (!isAdminGlobal) return;
        if (!validarCampoPaginas('manual')) return;
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
            numero_paginas: document.getElementById('manual-paginas').value ? Number(document.getElementById('manual-paginas').value) : null,
            descricao: document.getElementById('manual-descricao').value,
            temas: document.getElementById('manual-temas').value,
            categoria: document.getElementById('manual-categoria').value,
            quantidade: parseInt(qtd),
            capa: capaUrl,
            localizacao: localizacao
        };

        const res = await apiFetch('/api/livros', {
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
            document.getElementById('manual-paginas').value = '';
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
    });
}


function editarLivroSelecionado() {
    if (!isAdminGlobal) return;
    if(!livroSelecionado) return;
    document.getElementById('edit-id').value = livroSelecionado.id;
    document.getElementById('edit-titulo').value = livroSelecionado.titulo;
    document.getElementById('edit-autor').value = livroSelecionado.autor;
    document.getElementById('edit-ano').value = livroSelecionado.ano || '';
    document.getElementById('edit-paginas').value = livroSelecionado.numero_paginas || '';
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
    const modal = document.getElementById(isManual ? 'modalManualLivro' : 'modalEditarLivro');
    if (!modal) return;
    const config = carregarConfig();
    for (const [classe, key] of [['campo-ano', 'campoAnoVisivel'], ['campo-descricao', 'campoDescricaoVisivel'], ['campo-temas', 'campoTemasVisivel'], ['campo-categoria', 'campoCategoriaVisivel']]) {
        const field = modal.querySelector('.' + classe);
        if (field) field.style.display = config[key] ? '' : 'none';
    }
}


async function verificarObrigarLocalizacao() {
    if (!isAdminGlobal) return;
    const res = await apiFetch('/api/config/obrigar_localizacao_livro/status');
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
    return runAction('salvarEdicaoLivro', 'btn-salvar-edicao', async () => {
        if (!isAdminGlobal) return;
        if (!validarCampoPaginas('edit')) return;
        const id = document.getElementById('edit-id').value;
        const payload = {
            titulo: document.getElementById('edit-titulo').value,
            autor: document.getElementById('edit-autor').value,
            ano: document.getElementById('edit-ano').value,
            numero_paginas: document.getElementById('edit-paginas').value ? Number(document.getElementById('edit-paginas').value) : null,
            descricao: document.getElementById('edit-descricao').value,
            temas: document.getElementById('edit-temas').value,
            categoria: document.getElementById('edit-categoria').value,
            estoque: parseInt(document.getElementById('edit-estoque').value),
            disponivel: parseInt(document.getElementById('edit-disponivel').value),
            localizacao: document.getElementById('edit-localizacao') ? document.getElementById('edit-localizacao').value : ''
        };
        const novaCapa = document.getElementById('edit-capa-url').value;
        if (novaCapa) payload.capa = novaCapa;

        const res = await apiFetch(`/api/livros/${id}`, {
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
    });
}


function confirmarExclusaoLivro() {
    if (!isAdminGlobal) return;
    if(!livroSelecionado) return;
    confirmAction("Excluir Livro", `Deseja realmente excluir "${livroSelecionado.titulo}"?`, async () => {
        await apiFetch(`/api/livros/${livroSelecionado.id}`, {method: 'DELETE'});
        showToast("Livro excluído.", "success");
        fecharDetalhes();
        carregarAcervo();
        if (isAdminGlobal) carregarDashboard();
    });
}
