let leitorSelecionadoEmprestimo = null;
document.getElementById('rapido-nome-prof')?.addEventListener('input',()=>{leitorSelecionadoEmprestimo=null;});
async function verificarExigirSenhaEmprestimo() {
    const res = await apiFetch('/api/config/exigir_senha_emprestimo/status');
    const data = await res.json();
    if (!data.ativo) return null;

    return new Promise((resolve) => {
        const modal = document.getElementById('modalSenhaConfig');
        document.getElementById('senha-titulo').innerText = 'Senha de Administrador';
        document.getElementById('senha-mensagem').innerHTML = 'Digite a senha para realizar o empréstimo:';
        document.getElementById('senha-confirm').style.display = 'none';
        document.getElementById('senha-input').value = '';
        const btnOk = document.getElementById('btn-senha');
        const originalOnclick = btnOk.onclick;
        btnOk.onclick = async () => {
            const senha = document.getElementById('senha-input').value;
            const resCheck = await apiFetch('/api/config/senha/verificar', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({senha})
            });
            const dataCheck = await resCheck.json();
            if (dataCheck.valido) {
                closeModal('modalSenhaConfig');
                resolve(senha);
            } else {
                showToast("Senha incorreta", "error");
                resolve(null);
            }
            btnOk.onclick = originalOnclick;
        };
        openModal('modalSenhaConfig');
    });
}


function emprestarSelecionado() {
    if (!isAdminGlobal) return;
    if(!livroSelecionado) return;
    if(livroSelecionado.disponivel <= 0) showToast("Sem exemplares livres. Só será possível confirmar se houver exemplar separado para o leitor selecionado.", "warning");
    leitorSelecionadoEmprestimo = null;
    verificarExigirSenhaEmprestimo().then(senha => {
        if (senha === null && (document.getElementById('modalSenhaConfig').style.display === 'flex')) return;
        window.senhaEmprestimoGlobal = senha;
        document.getElementById('emprestimo-rapido-livro-id').value = livroSelecionado.id;
        document.getElementById('rapido-nome').value = '';
        document.getElementById('rapido-sala').value = '';
        document.getElementById('rapido-periodo').value = 'Manhã';
        periodoRapidoSelect.setValue('Manhã');
        document.getElementById('rapido-email').value = '';
        document.getElementById('rapido-nome-prof').value = '';
        document.getElementById('rapido-materia').value = '';
        document.getElementById('rapido-telefone').value = '';
        tipoRapidoSelect.setValue('estudante');
        prazoRapidoSelect.setValue('7');
        document.getElementById('rapido-aluno').style.display = 'block';
        document.getElementById('rapido-professor').style.display = 'none';
        document.getElementById('rapido-nome-suggestions').style.display = 'none';
        aplicarVisibilidadeCamposEmprestimo();
        openModal('modalEmprestimoRapido');
    });
}


async function confirmarEmprestimoRapido() {
    return runAction('confirmarEmprestimoRapido', 'btn-confirmar-emprestimo', async () => {
        if (!isAdminGlobal) return;
        const tipo = document.getElementById('rapido-tipo').value;
        const livroId = parseInt(document.getElementById('emprestimo-rapido-livro-id').value);
        let payload = {tipo, livros: [{id: livroId, quantidade: 1}]};

        if (tipo === 'estudante') {
            payload.nome = document.getElementById('rapido-nome').value;
            payload.sala = document.getElementById('rapido-sala').value;
            payload.periodo = document.getElementById('rapido-periodo').value;
            payload.email = document.getElementById('rapido-email').value;
            payload.prazo = document.getElementById('rapido-prazo').value;
            const telefone = document.getElementById('rapido-telefone').value;
            if (telefone) payload.telefone = telefone;
            if (!leitorSelecionadoEmprestimo && (!payload.nome || !payload.sala || !payload.periodo)) {
                return showToast("Preencha todos os campos do estudante.", "warning");
            }
            const config = carregarConfig();
            if (config.campoNumeroUsuario && !payload.telefone) {
                return showToast("Telefone do aluno é obrigatório conforme configuração.", "warning");
            }
        } else {
            payload.nome = document.getElementById('rapido-nome-prof').value;
            payload.materia = document.getElementById('rapido-materia').value;
            if (!payload.nome || !payload.materia) {
                return showToast("Preencha nome e matéria do professor.", "warning");
            }
            payload.prazo = 0;
        }

        if (leitorSelecionadoEmprestimo) payload.leitor_id = leitorSelecionadoEmprestimo;
        if (window.senhaEmprestimoGlobal) {
            payload.senha = window.senhaEmprestimoGlobal;
            window.senhaEmprestimoGlobal = null;
        }

        const res = await apiFetch('/api/emprestimos', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            const data = await res.json();
            showToast("Empréstimo realizado!", "success");
            if (data.email_enviado) {
                showToast("E-mail de confirmação enviado com sucesso.", "success");
            }
            closeModal('modalEmprestimoRapido');
            if (data.leitor_id) oferecerAcessoLeitor(data.leitor_id);
            carregarAcervo();
            if (isAdminGlobal) carregarDashboard();
            if (document.getElementById('emp').classList.contains('active')) {
                filtrarEmprestimos(filtroEmprestimosAtual);
            }
        } else {
            const err = await res.json();
            showToast("Erro: " + err.erro, "error");
        }
    });
}


let emprestimosDoFiltro = [];
let requisicaoEmprestimos = 0;

// Busca local: não faz uma requisição a cada tecla e ignora acentos/maiúsculas.
function normalizarNomeEmprestimo(nome) {
    return String(nome || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR');
}

document.getElementById('busca-emprestimos')?.addEventListener('input', renderizarEmprestimos);

async function filtrarEmprestimos(filtro) {
    if (!isAdminGlobal) return;
    filtroEmprestimosAtual = filtro;
    const requisicao = ++requisicaoEmprestimos;
    emprestimosDoFiltro = [];
    document.getElementById('lista-ativos').replaceChildren();
    document.getElementById('resultado-busca-emprestimos').textContent = 'Carregando empréstimos...';
    document.querySelectorAll('.btn-filtro').forEach(b => b.classList.remove('active-filtro'));
    let btnId = 'btn-filtro-todos';
    if (filtro === 'ativos') btnId = 'btn-filtro-ativos';
    else if (filtro === 'atrasados') btnId = 'btn-filtro-atrasados';
    else if (filtro === 'hoje') btnId = 'btn-filtro-hoje';
    else if (filtro === 'devolvidos') btnId = 'btn-filtro-devolvidos';
    document.getElementById(btnId).classList.add('active-filtro');

    let url;
    if (filtro === 'atrasados') url = '/api/emprestimos/atrasos';
    else if (filtro === 'hoje') url = '/api/emprestimos/devolucoes-hoje';
    else if (filtro === 'ativos') url = '/api/emprestimos/ativos';
    else if (filtro === 'devolvidos') url = '/api/emprestimos/devolvidos';
    else url = '/api/emprestimos/todos';

    const res = await apiFetch(url);
    const dados = await res.json();
    // Uma resposta anterior não deve sobrescrever o filtro escolhido mais recentemente.
    if (requisicao !== requisicaoEmprestimos) return;
    emprestimosDoFiltro = dados;
    renderizarEmprestimos();
}

function renderizarEmprestimos() {
    if (!isAdminGlobal) return;
    const filtro = filtroEmprestimosAtual;
    const termos = normalizarNomeEmprestimo(document.getElementById('busca-emprestimos').value).trim().split(/\s+/).filter(Boolean);
    const dados = emprestimosDoFiltro.filter(e => termos.every(termo => normalizarNomeEmprestimo([e.leitor,e.livro,e.serie,e.status].join(' ')).includes(termo)));
    document.getElementById('resultado-busca-emprestimos').textContent = `${dados.length} ${dados.length === 1 ? 'empréstimo encontrado' : 'empréstimos encontrados'} no filtro selecionado.`;
    const div = document.getElementById('lista-ativos');

    if (dados.length === 0) {
        div.replaceChildren(textElement('p', termos.length
            ? 'Nenhum empréstimo encontrado para esse nome neste filtro. Confira o nome ou selecione Todos.'
            : 'Nenhum empréstimo encontrado para este filtro.'));
        return;
    }

    const table = textElement('table', '', 'tabela-emprestimos');
    const head = document.createElement('thead');
    const header = document.createElement('tr');
    ['Capa', 'Livro', 'Leitor', 'Telefone', 'Série', 'Data Empréstimo', 'Data Devolução', 'Ações'].forEach(label => header.appendChild(textElement('th', label)));
    head.appendChild(header);
    const body = document.createElement('tbody');
    dados.forEach(e => {
        const row = document.createElement('tr');
        const coverCell = document.createElement('td');
        const cover = textElement('div', '', 'capa-mini');
        coverBackground(cover, e.capa);
        coverCell.appendChild(cover);
        row.appendChild(coverCell);
        [e.livro, e.leitor, e.telefone || '-', e.serie || '-', e.data_emprestimo || '-', e.data_vencimento || e.vencimento || '-'].forEach(value => row.appendChild(textElement('td', value)));
        // O td precisa continuar sendo uma célula de tabela; flex pertence ao filho.
        const actionCell = document.createElement('td');
        const actions = textElement('div', '', 'acoes-botoes');
        actionCell.appendChild(actions);
        if (e.status === 'Devolvido' || filtro === 'devolvidos') actions.appendChild(textElement('span', e.data_devolucao ? `Devolvido em ${e.data_devolucao}` : 'Devolvido'));
        else if (e.encerramento || e.status === 'Perdido') actions.appendChild(textElement('span',e.encerramento || e.status));
        else if (isAdminGlobal) {
            const devolver = textElement('button', 'Devolver', 'btn-primary btn-small');
            devolver.onclick = () => devolverEmprestimo(e.id);
            const renovar = textElement('button', 'Renovar', 'btn-primary btn-small');
            renovar.onclick = () => renovarEmprestimo(e.id);
            actions.append(devolver, renovar);
        } else actions.appendChild(textElement('span', 'Sem permissão'));
        row.appendChild(actionCell);
        body.appendChild(row);
    });
    table.append(head, body);
    div.replaceChildren(table);
}


async function devolverEmprestimo(id) {
    if (!isAdminGlobal) return;
    confirmAction("Devolução", "Confirmar devolução do livro?", async () => {
        const res = await apiFetch(`/api/emprestimos/${id}/devolver`, {method: 'POST'});
        if(res.ok) {
            showToast("Livro devolvido com sucesso!", "success");
            filtrarEmprestimos(filtroEmprestimosAtual);
            if (isAdminGlobal) carregarDashboard();
            carregarAcervo();
        } else {
            showToast("Erro na devolução", "error");
        }
    });
}


async function renovarEmprestimo(id) {
    if (!isAdminGlobal) return;
    confirmAction("Renovar Empréstimo", "Deseja renovar este empréstimo por mais um período?", async () => {
        const res = await apiFetch(`/api/emprestimos/${id}/renovar`, {method: 'POST'});
        if(res.ok) {
            showToast("Empréstimo renovado!", "success");
            filtrarEmprestimos(filtroEmprestimosAtual);
            if (isAdminGlobal) carregarDashboard();
        } else {
            showToast("Erro ao renovar", "error");
        }
    });
}


function aplicarVisibilidadeCamposEmprestimo() {
    const config = carregarConfig();
    const campoTelefone = document.querySelector('.campo-telefone-aluno');
    if (campoTelefone) campoTelefone.style.display = config.campoNumeroUsuario ? 'block' : 'none';
}
