function aplicarMascaraTelefone(input) {
    let valor = input.value.replace(/\D/g, '');
    if (valor.length === 0) return;
    let comCodPais = false;
    if (valor.startsWith('55')) {
        comCodPais = true;
        valor = valor.substring(2);
    }
    let ddd = '';
    let numero = '';
    if (valor.length >= 2) {
        ddd = valor.substring(0, 2);
        numero = valor.substring(2);
    } else {
        ddd = valor;
    }
    let formatado = '';
    if (comCodPais) formatado = '+55 ';
    if (ddd) formatado += `(${ddd}) `;
    if (numero) {
        if (numero.length === 9) {
            formatado += `${numero.substring(0,5)}-${numero.substring(5)}`;
        } else if (numero.length === 8) {
            formatado += `${numero.substring(0,4)}-${numero.substring(4)}`;
        } else {
            formatado += numero;
        }
    }
    input.value = formatado;
}


async function buscarLeitoresAutocomplete() {
    const termo = document.getElementById('rapido-nome').value.trim();
    const suggestionsDiv = document.getElementById('rapido-nome-suggestions');
    if (termo.length < 2) {
        suggestionsDiv.style.display = 'none';
        return;
    }
    const res = await apiFetch(`/api/leitores/buscar?q=${encodeURIComponent(termo)}`);
    const leitores = await res.json();
    if (leitores.length === 0) {
        suggestionsDiv.style.display = 'none';
        return;
    }
    suggestionsDiv.innerHTML = '';
    leitores.forEach(leitor => {
        const div = document.createElement('div');
        div.textContent = `${leitor.nome} (${leitor.tipo === 'estudante' ? leitor.sala : leitor.materia})`;
        div.addEventListener('click', () => {
            document.getElementById('rapido-nome').value = leitor.nome;
            if (leitor.tipo === 'estudante') {
                document.getElementById('rapido-tipo').value = 'estudante';
                tipoRapidoSelect.setValue('estudante');
                document.getElementById('rapido-aluno').style.display = 'block';
                document.getElementById('rapido-professor').style.display = 'none';
                document.getElementById('rapido-sala').value = leitor.sala || '';
                document.getElementById('rapido-email').value = leitor.email || '';
                document.getElementById('rapido-periodo').value = leitor.periodo || 'Manhã';
                periodoRapidoSelect.setValue(leitor.periodo || 'Manhã');
                document.getElementById('rapido-telefone').value = leitor.telefone || '';
            } else {
                document.getElementById('rapido-tipo').value = 'professor';
                tipoRapidoSelect.setValue('professor');
                document.getElementById('rapido-aluno').style.display = 'none';
                document.getElementById('rapido-professor').style.display = 'block';
                document.getElementById('rapido-nome-prof').value = leitor.nome;
                document.getElementById('rapido-materia').value = leitor.materia || '';
            }
            suggestionsDiv.style.display = 'none';
        });
        suggestionsDiv.appendChild(div);
    });
    suggestionsDiv.style.display = 'block';
}


function formatarSala() {
    const input = document.getElementById('rapido-sala');
    let valor = input.value.trim();
    if (!valor) return;
    const matchNumero = valor.match(/^(\d+)\s*$/);
    if (matchNumero) {
        input.value = matchNumero[1] + '° ano';
        return;
    }
    const matchNumeroTexto = valor.match(/^(\d+)\s+(.+)$/);
    if (matchNumeroTexto) {
        input.value = matchNumeroTexto[1] + '° ' + matchNumeroTexto[2];
    }
}


async function carregarLeitores() {
    if (!isAdminGlobal) return;
    const res = await apiFetch('/api/leitores');
    todosLeitores = await res.json();
    aplicarFiltroLeitores();
}


function aplicarFiltroLeitores() {
    const termo = document.getElementById('busca-leitor').value.toLowerCase();
    const filtrados = todosLeitores.filter(l => l.nome.toLowerCase().includes(termo));
    exibirListaLeitores(filtrados);
}


function filtrarLeitores() { aplicarFiltroLeitores(); }

function exibirListaLeitores(leitores) {
    const container = document.getElementById('lista-leitores');
    container.replaceChildren();
    leitores.forEach(l => {
        const extra = l.tipo === 'estudante' ? `Sala: ${l.sala} - Período: ${l.periodo}` : `Matéria: ${l.materia}`;
        const item = textElement('div', '', 'livro-item');
        const info = textElement('span', '');
        info.append(textElement('strong', l.nome), document.createTextNode(` (${l.tipo}) - ${extra}`));
        if (l.telefone) info.append(document.createElement('br'), textElement('small', `Tel: ${l.telefone}`));
        const actions = textElement('span', '');
        actions.style.cssText = 'display:flex; gap:8px;';
        if (isAdminGlobal) {
            const edit = textElement('button', 'Editar', 'btn-primary btn-small');
            edit.onclick = () => editarLeitor(l.id);
            const remove = textElement('button', 'Excluir', 'btn-primary btn-small');
            remove.style.background = '#b33';
            remove.onclick = () => excluirLeitor(l.id);
            actions.append(edit, remove);
        }
        item.append(info, actions);
        container.appendChild(item);
    });
}



function toggleLeitorTipo() {
    const tipo = document.getElementById('leitor-tipo').value;
    document.getElementById('leitor-aluno').style.display = tipo === 'estudante' ? 'block' : 'none';
    document.getElementById('leitor-prof').style.display = tipo === 'professor' ? 'block' : 'none';
}


function editarLeitor(id) {
    if (!isAdminGlobal) return;
    const leitor = todosLeitores.find(l => l.id === id);
    if(!leitor) return;
    document.getElementById('leitor-id').value = leitor.id;
    document.getElementById('leitor-titulo').innerText = 'Editar Leitor';
    document.getElementById('leitor-tipo').value = leitor.tipo;
    tipoLeitorModalSelect.setValue(leitor.tipo);
    toggleLeitorTipo();
    if(leitor.tipo === 'estudante') {
        document.getElementById('leitor-nome').value = leitor.nome;
        document.getElementById('leitor-sala').value = leitor.sala || '';
        document.getElementById('leitor-periodo').value = leitor.periodo || '';
        document.getElementById('leitor-email').value = leitor.email || '';
        document.getElementById('leitor-telefone').value = leitor.telefone || '';
    } else {
        document.getElementById('leitor-nome-prof').value = leitor.nome;
        document.getElementById('leitor-materia').value = leitor.materia || '';
        document.getElementById('leitor-email-prof').value = leitor.email || '';
    }
    openModal('modalLeitor');
}


async function salvarLeitor() {
    return runAction('salvarLeitor', 'btn-salvar-leitor', async () => {
        if (!isAdminGlobal) return;
        const id = document.getElementById('leitor-id').value;
        const tipo = document.getElementById('leitor-tipo').value;
        let payload = {tipo};
        if(tipo === 'estudante') {
            payload.nome = document.getElementById('leitor-nome').value;
            payload.sala = document.getElementById('leitor-sala').value;
            payload.periodo = document.getElementById('leitor-periodo').value;
            payload.email = document.getElementById('leitor-email').value;
            payload.telefone = document.getElementById('leitor-telefone').value;
            if(!payload.nome || !payload.sala || !payload.periodo) return showToast("Preencha todos os campos.", "warning");
        } else {
            payload.nome = document.getElementById('leitor-nome-prof').value;
            payload.materia = document.getElementById('leitor-materia').value;
            payload.email = document.getElementById('leitor-email-prof').value;
            if(!payload.nome || !payload.materia) return showToast("Preencha todos os campos.", "warning");
        }
        const url = id ? `/api/leitores/${id}` : '/api/leitores';
        const method = id ? 'PUT' : 'POST';
        const res = await apiFetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        if(res.ok) {
            showToast(id ? "Leitor atualizado!" : "Leitor cadastrado!", "success");
            document.getElementById('leitor-id').value = '';
            document.getElementById('leitor-nome').value = '';
            document.getElementById('leitor-sala').value = '';
            document.getElementById('leitor-periodo').value = '';
            document.getElementById('leitor-email').value = '';
            document.getElementById('leitor-nome-prof').value = '';
            document.getElementById('leitor-materia').value = '';
            document.getElementById('leitor-email-prof').value = '';
            document.getElementById('leitor-telefone').value = '';
            tipoLeitorModalSelect.setValue('estudante');
            document.getElementById('leitor-aluno').style.display = 'block';
            document.getElementById('leitor-prof').style.display = 'none';
            closeModal('modalLeitor');
            carregarLeitores();
            document.getElementById('leitor-id').value = '';
            document.getElementById('leitor-titulo').innerText = 'Novo Leitor';
        } else {
            showToast("Erro ao salvar leitor", "error");
        }
    });
}


async function excluirLeitor(id) {
    if (!isAdminGlobal) return;
    confirmAction("Excluir Leitor", "Tem certeza que deseja excluir este leitor?", async () => {
        await apiFetch(`/api/leitores/${id}`, {method: 'DELETE'});
        showToast("Leitor excluído.", "success");
        carregarLeitores();
    });
}
