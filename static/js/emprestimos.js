async function verificarExigirSenhaEmprestimo() {
    const res = await fetch('/api/config/exigir_senha_emprestimo/status');
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
            const resCheck = await fetch('/api/config/senha/verificar', {
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
    if(livroSelecionado.disponivel <= 0) {
        showToast("Não há exemplares disponíveis para este livro no momento.", "warning");
        return;
    }
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
        if (!payload.nome || !payload.sala || !payload.periodo || !payload.email) {
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

    if (window.senhaEmprestimoGlobal) {
        payload.senha = window.senhaEmprestimoGlobal;
        window.senhaEmprestimoGlobal = null;
    }

    const res = await fetch('/api/emprestimos', {
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
        carregarAcervo();
        if (isAdminGlobal) carregarDashboard();
        if (document.getElementById('emp').classList.contains('active')) {
            filtrarEmprestimos(filtroEmprestimosAtual);
        }
    } else {
        const err = await res.json();
        showToast("Erro: " + err.erro, "error");
    }
}


async function filtrarEmprestimos(filtro) {
    if (!isAdminGlobal) return;
    filtroEmprestimosAtual = filtro;
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

    const res = await fetch(url);
    const dados = await res.json();
    const div = document.getElementById('lista-ativos');

    if (dados.length === 0) {
        div.innerHTML = '<p>Nenhum empréstimo encontrado para este filtro.</p>';
        return;
    }

    let html = '<table class="tabela-emprestimos"><thead>';
    html += '<th>Capa</th><th>Livro</th><th>Leitor</th><th>Telefone</th><th>Série</th><th>Data Empréstimo</th><th>Data Devolução</th><th>Ações</th>';
    html += '</thead><tbody>';

    dados.forEach(e => {
        html += '<tr>';
        html += `<td><div class="capa-mini" style="background-image: url('${e.capa || '/static/images/placeholder.png'}');"></div></td>`;
        html += `<td>${e.livro}</td>`;
        html += `<td>${e.leitor}</td>`;
        html += `<td>${e.telefone || '-'}</td>`;
        html += `<td>${e.serie || '-'}</td>`;
        html += `<td>${e.data_emprestimo || '-'}</td>`;
        html += `<td>${e.data_vencimento || e.vencimento || '-'}</td>`;
        html += `<td class="acoes-botoes">`;
        if (filtro !== 'devolvidos') {
            if (isAdminGlobal) {
                html += `<button class="btn-primary btn-small" onclick="devolverEmprestimo(${e.id})">Devolver</button>`;
                html += `<button class="btn-primary btn-small" onclick="renovarEmprestimo(${e.id})">Renovar</button>`;
            } else {
                html += `<span>Sem permissão</span>`;
            }
        } else {
            html += `<span>Devolvido em ${e.data_devolucao}</span>`;
        }
        html += `<\/td></tr>`;
    });
    html += '</tbody></table>';
    div.innerHTML = html;
}


async function devolverEmprestimo(id) {
    if (!isAdminGlobal) return;
    confirmAction("Devolução", "Confirmar devolução do livro?", async () => {
        const res = await fetch(`/api/emprestimos/${id}/devolver`, {method: 'POST'});
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
        const res = await fetch(`/api/emprestimos/${id}/renovar`, {method: 'POST'});
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
