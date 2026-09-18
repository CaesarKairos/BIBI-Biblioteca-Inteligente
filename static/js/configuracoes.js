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


async function abrirConfiguracoes() {
    if (!isAdminGlobal) return;
    const statusRes = await apiFetch('/api/config/senha/status');
    const data = await statusRes.json();
    if (!data.set) {
        document.getElementById('senha-confirm').style.display = 'block';
        document.getElementById('senha-titulo').innerText = 'Criar Senha de Administrador';
        document.getElementById('senha-mensagem').innerText = 'Defina uma senha de 4 dígitos para proteger as configurações:';
        document.getElementById('senha-input').value = '';
        document.getElementById('senha-confirm').value = '';
        document.getElementById('btn-senha').onclick = async () => {
            const senha = document.getElementById('senha-input').value;
            const confirm = document.getElementById('senha-confirm').value;
            if (!senha || senha.length !== 4) { showToast("A senha deve ter 4 caracteres", "warning"); return; }
            if (senha !== confirm) { showToast("As senhas não conferem", "warning"); return; }
            const res = await apiFetch('/api/config/senha/definir', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({senha})
            });
            if (res.ok) {
                showToast("Senha criada com sucesso!", "success");
                closeModal('modalSenhaConfig');
                abrirModalConfiguracoes();
            } else {
                const err = await res.json();
                showToast("Erro: " + err.erro, "error");
            }
        };
        openModal('modalSenhaConfig');
    } else {
        document.getElementById('senha-confirm').style.display = 'none';
        document.getElementById('senha-titulo').innerText = 'Senha de Administrador';
        document.getElementById('senha-mensagem').innerText = 'Digite a senha para acessar as configurações:';
        document.getElementById('senha-input').value = '';
        document.getElementById('btn-senha').onclick = async () => {
            const senha = document.getElementById('senha-input').value;
            if (!senha) { showToast("Digite a senha", "warning"); return; }
            const res = await apiFetch('/api/config/senha/verificar', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({senha})
            });
            const data = await res.json();
            if (data.valido) {
                closeModal('modalSenhaConfig');
                abrirModalConfiguracoes();
            } else {
                showToast("Senha incorreta", "error");
            }
        };
        openModal('modalSenhaConfig');
    }
}


async function abrirModalConfiguracoes() {
    const config = carregarConfig();
    const container = document.getElementById('lista-config-toggles');
    container.innerHTML = '';

    const respExigirSenhaEmprestimo = await apiFetch('/api/config/exigir_senha_emprestimo/status');
    const exigirSenhaEmprestimo = (await respExigirSenhaEmprestimo.json()).ativo;
    const respObrigarLocalizacao = await apiFetch('/api/config/obrigar_localizacao_livro/status');
    const obrigarLocalizacao = (await respObrigarLocalizacao.json()).ativo;
    const respExigirSenhaAgendamento = await apiFetch('/api/config/exigir_senha_agendamento/status');
    const exigirSenhaAgendamento = (await respExigirSenhaAgendamento.json()).ativo;
    const respBloqEmail = await apiFetch('/api/config/bloquear_email/status');
    const bloqueioEmail = (await respBloqEmail.json()).bloqueado;
    const respBloqExcluirAgenda = await apiFetch('/api/config/bloquear_excluir_agendamento/status');
    const bloquearExcluirAgenda = (await respBloqExcluirAgenda.json()).ativo;
    const respQtdAulas = await apiFetch('/api/config/quantidade_aulas/status');
    const quantidadeAulas = (await respQtdAulas.json()).quantidade;
    const respEmailStatus = await apiFetch('/api/config/email/status');
    const emailOrganizacaoAtual = (await respEmailStatus.json()).email || '';

    // Categorias visuais do modal de configurações (Tarefa 3)
    const categorias = [
        {
            titulo: 'Cadastro de Livros',
            toggles: [
                { label: 'Campo "Descrição" no cadastro de livros', key: 'campoDescricaoVisivel', checked: config.campoDescricaoVisivel, desc: 'Mostra ou oculta o campo de descrição ao adicionar/editar livros.' },
                { label: 'Campo "Temas" no cadastro de livros', key: 'campoTemasVisivel', checked: config.campoTemasVisivel, desc: 'Mostra ou oculta o campo de temas ao adicionar/editar livros.' },
                { label: 'Campo "Ano" no cadastro de livros', key: 'campoAnoVisivel', checked: config.campoAnoVisivel, desc: 'Mostra ou oculta o campo de ano de publicação.' },
                { label: 'Campo "Categoria" no cadastro de livros', key: 'campoCategoriaVisivel', checked: config.campoCategoriaVisivel, desc: 'Mostra ou oculta o campo de categoria.' },
                { label: 'Obrigar preenchimento da localização física/prateleira ao cadastrar livros', key: 'obrigarLocalizacao', checked: obrigarLocalizacao, desc: 'Torna o campo de localização (prateleira) obrigatório ao adicionar/editar livros.' },
                { label: 'Bloquear botão "Excluir Livro"', key: 'bloquearExcluirLivro', checked: config.bloquearExcluirLivro, desc: 'Remove o botão de excluir livro da interface.' }
            ]
        },
        {
            titulo: 'Agenda e Agendamentos',
            toggles: [
                { label: 'Mostrar coluna "Aula" na agenda', key: 'mostrarColunaAula', checked: config.mostrarColunaAula, desc: 'Exibe ou oculta a coluna de numeração das aulas na tabela de agenda.' },
                { label: 'Exigir senha de administrador para agendamentos de salas', key: 'exigirSenhaAgendamento', checked: exigirSenhaAgendamento, desc: 'Solicita a senha de 4 dígitos antes de criar um agendamento.' },
                { label: 'Bloquear botão "Excluir Agendamento"', key: 'bloquearExcluirAgendamento', checked: bloquearExcluirAgenda, desc: 'Remove ou desabilita o botão de excluir agendamento na interface.' }
            ],
            extra: 'aulas'
        },
        {
            titulo: 'Empréstimos',
            toggles: [
                { label: 'Campo "Telefone do Aluno" no empréstimo', key: 'campoNumeroUsuario', checked: config.campoNumeroUsuario, desc: 'Exibe o campo para registrar o telefone do estudante durante o empréstimo.' },
                { label: 'Exigir senha de administrador ao realizar empréstimos', key: 'exigirSenhaEmprestimo', checked: exigirSenhaEmprestimo, desc: 'Solicita a senha de 4 dígitos antes de confirmar um empréstimo.' }
            ]
        },
        {
            titulo: 'E-mails',
            toggles: [
                { label: 'Bloquear envio de e-mails', key: 'bloquearEmail', checked: bloqueioEmail, desc: 'Impede o sistema de enviar qualquer e-mail de notificação ou confirmação.' }
            ],
            extra: 'email'
        }
    ];

    categorias.forEach(cat => {
        const painel = document.createElement('div');
        painel.className = 'config-panel';

        const subtitulo = document.createElement('h4');
        subtitulo.className = 'config-subtitulo';
        subtitulo.innerText = cat.titulo;
        painel.appendChild(subtitulo);

        cat.toggles.forEach(tgl => {
            const row = document.createElement('div');
            row.className = 'config-toggle-row';
            row.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span>${tgl.label}</span>
                    <label class="switch">
                        <input type="checkbox" id="cfg-${tgl.key}" ${tgl.checked ? 'checked' : ''} onchange="if('${tgl.key}'==='bloquearEmail') atualizarBloqueioEmail(this.checked); else if('${tgl.key}'==='exigirSenhaEmprestimo') atualizarExigirSenhaEmprestimo(this.checked); else if('${tgl.key}'==='obrigarLocalizacao') atualizarObrigarLocalizacao(this.checked); else if('${tgl.key}'==='exigirSenhaAgendamento') atualizarExigirSenhaAgendamento(this.checked); else if('${tgl.key}'==='bloquearExcluirAgendamento') atualizarBloquearExcluirAgendamento(this.checked);">
                        <span class="slider"></span>
                    </label>
                </div>
                <small style="color:var(--light); font-size:11px; margin-top:5px;">${tgl.desc}</small>
            `;
            painel.appendChild(row);
        });

        if (cat.extra === 'aulas') {
            const aulaRow = document.createElement('div');
            aulaRow.style.marginTop = '15px';
            aulaRow.innerHTML = `
                <label>Quantidade de aulas diárias:</label>
                <input type="number" id="cfg-quantidade-aulas" min="1" max="20" value="${Number(quantidadeAulas)}" style="width:100%; margin-top:5px;">
                <small style="color:var(--light); font-size:11px;">Define quantas linhas (horários) serão exibidas na tabela de agenda.</small>
            `;
            painel.appendChild(aulaRow);
        }

        if (cat.extra === 'email') {
            const emailRow = document.createElement('div');
            emailRow.style.marginTop = '15px';
            emailRow.innerHTML = `
                <label>E-mail da Organização:</label>
                <input type="email" id="cfg-email-organizacao" placeholder="biblioteca@escola.com" value="" style="width:100%; margin-top:5px;">
                <label style="margin-top:10px; display:block;">Chave de App (senha de aplicativo):</label>
                <input type="password" id="cfg-email-app-password" placeholder="Deixe em branco para não alterar" style="width:100%; margin-top:5px;" autocomplete="new-password">
                <small style="color:var(--light); font-size:11px;">Credenciais usadas para o envio de e-mails de notificação. A chave de app não é reexibida por segurança.</small>
            `;
            emailRow.querySelector('#cfg-email-organizacao').value = emailOrganizacaoAtual;
            painel.appendChild(emailRow);
        }

        container.appendChild(painel);
    });

    openModal('modalConfiguracoes');
}


async function atualizarBloqueioEmail(bloqueado) {
    await apiFetch('/api/config/bloquear_email/set', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({bloqueado}) });
}

async function atualizarExigirSenhaEmprestimo(ativo) {
    await apiFetch('/api/config/exigir_senha_emprestimo/set', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ativo}) });
}

async function atualizarObrigarLocalizacao(ativo) {
    await apiFetch('/api/config/obrigar_localizacao_livro/set', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ativo}) });
    verificarObrigarLocalizacao();
}

async function atualizarExigirSenhaAgendamento(ativo) {
    await apiFetch('/api/config/exigir_senha_agendamento/set', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ativo}) });
}

async function atualizarBloquearExcluirAgendamento(ativo) {
    await apiFetch('/api/config/bloquear_excluir_agendamento/set', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ativo}) });
}


async function salvarConfigGerais() {
    return runAction('salvarConfigGerais', '#modalConfiguracoes .btn-primary', async () => {
        if (!isAdminGlobal) return;
        const config = carregarConfig();
        config.mostrarColunaAula = document.getElementById('cfg-mostrarColunaAula')?.checked ?? config.mostrarColunaAula;
        config.campoDescricaoVisivel = document.getElementById('cfg-campoDescricaoVisivel')?.checked ?? config.campoDescricaoVisivel;
        config.campoTemasVisivel = document.getElementById('cfg-campoTemasVisivel')?.checked ?? config.campoTemasVisivel;
        config.campoAnoVisivel = document.getElementById('cfg-campoAnoVisivel')?.checked ?? config.campoAnoVisivel;
        config.campoCategoriaVisivel = document.getElementById('cfg-campoCategoriaVisivel')?.checked ?? config.campoCategoriaVisivel;
        config.campoNumeroUsuario = document.getElementById('cfg-campoNumeroUsuario')?.checked ?? config.campoNumeroUsuario;
        config.bloquearExcluirLivro = document.getElementById('cfg-bloquearExcluirLivro')?.checked ?? config.bloquearExcluirLivro;
        salvarConfig(config);

        const novaQtdAulas = parseInt(document.getElementById('cfg-quantidade-aulas')?.value);
        if (novaQtdAulas && novaQtdAulas >= 1 && novaQtdAulas <= 20) {
            await apiFetch('/api/config/quantidade_aulas/set', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({quantidade: novaQtdAulas})
            });
            configAgenda.aulas = novaQtdAulas;
            carregarAgenda();
        }

        const emailOrganizacaoInput = document.getElementById('cfg-email-organizacao');
        const emailAppPasswordInput = document.getElementById('cfg-email-app-password');
        if (emailOrganizacaoInput) {
            const emailOrganizacao = emailOrganizacaoInput.value.trim();
            const emailAppPassword = emailAppPasswordInput ? emailAppPasswordInput.value.trim() : '';
            const resEmail = await apiFetch('/api/config/email/set', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({email_organizacao: emailOrganizacao, email_app_password: emailAppPassword})
            });
            if (!resEmail.ok) {
                const errEmail = await resEmail.json();
                showToast(errEmail.erro || "Erro ao salvar configuração de e-mail.", "error");
            }
        }

        aplicarVisibilidadeCamposLivro(true);
        aplicarVisibilidadeCamposLivro(false);
        aplicarVisibilidadeCamposEmprestimo();
        if (livroSelecionado) verDetalhes(livroSelecionado);
        carregarGraficoGeneros();
        carregarGraficoHistorico();
        closeModal('modalConfiguracoes');
        showToast("Configurações aplicadas!", "success");
    });
}
