async function carregarAgenda() {
    const hiddenInput = document.getElementById('agenda-data');
    const dataSelecionada = hiddenInput.value;
    periodoAtual = document.getElementById('agenda-periodo').value;
    let url = '/api/agendamentos?periodo=' + encodeURIComponent(periodoAtual);
    if (dataSelecionada) url += '&data=' + encodeURIComponent(dataSelecionada);
    const res = await apiFetch(url);
    const agendamentos = await res.json();
    const tabela = document.getElementById('tabela-agenda');
    tabela.innerHTML = '';
    const config = carregarConfig();
    const mostrarColunaAula = config.mostrarColunaAula;
    const qtdAulas = configAgenda.aulas;
    const head = document.createElement('thead');
    const header = document.createElement('tr');
    if (mostrarColunaAula) header.appendChild(textElement('th', 'Aula'));
    header.appendChild(textElement('th', 'Agendamento'));
    head.appendChild(header);
    const body = document.createElement('tbody');
    for (let aula = 1; aula <= qtdAulas; aula++) {
        const ag = agendamentos.find(a => a.aula === aula);
        const row = document.createElement('tr');
        if (mostrarColunaAula) row.appendChild(textElement('td', `${aula}ª Aula`));
        const cell = textElement('td', ag ? `${ag.professor} - ${ag.materia}` : '-');
        cell.className = ag ? 'ocupado' : '';
        Object.assign(cell.dataset, {id: ag?.id ?? '', professor: ag?.professor ?? '', materia: ag?.materia ?? '', uso: ag?.uso ?? '', aula});
        cell.onclick = () => celulaAgendaClick(cell);
        row.appendChild(cell);
        body.appendChild(row);
    }
    tabela.replaceChildren(head, body);
    carregarProximosAgendamentos();
    carregarAgendamentosPassados();
}


function celulaAgendaClick(cell) {
    const professor = cell.getAttribute('data-professor');
    const materia = cell.getAttribute('data-materia');
    const uso = cell.getAttribute('data-uso');
    const aula = parseInt(cell.getAttribute('data-aula'));
    const dataSelecionada = document.getElementById('agenda-data').value;
    const periodo = document.getElementById('agenda-periodo').value;
    if (!dataSelecionada) {
        showToast("Selecione uma data primeiro.", "warning");
        return;
    }
    if (professor && materia && uso) {
        agendamentoDetalhesId = cell.getAttribute('data-id');
        document.getElementById('detalhe-professor').innerText = professor;
        document.getElementById('detalhe-materia').innerText = materia;
        document.getElementById('detalhe-uso').innerText = uso;
        const btnExcluir = document.getElementById('btn-excluir-agendamento-detalhes');
        if (isAdminGlobal) {
            apiFetch('/api/config/bloquear_excluir_agendamento/status')
                .then(res => res.json())
                .then(data => {
                    if (data.ativo) btnExcluir.style.display = 'none';
                    else btnExcluir.style.display = 'block';
                });
        } else {
            btnExcluir.style.display = 'none';
        }
        openModal('modalDetalhesAgendamento');
    } else {
        if (!isAdminGlobal) {
            showToast("Apenas administradores podem criar agendamentos.", "warning");
            return;
        }
        const hoje = new Date().toISOString().split('T')[0];
        if (dataSelecionada < hoje) {
            showToast("Não é possível criar agendamentos em datas passadas.", "warning");
            return;
        }
        document.getElementById('agenda-dia').value = new Date(dataSelecionada + 'T00:00:00').getDay();
        document.getElementById('agenda-aula').value = aula;
        document.getElementById('agenda-periodo-modal').value = periodo;
        document.getElementById('agenda-data-modal').value = dataSelecionada;
        agendamentoAtualId = null;
        limparFormAgenda();
        verificarExigirSenhaAgendamento(() => { openModal('modalAgendamento'); });
    }
}


async function excluirAgendamentoDetalhes() {
    if (!isAdminGlobal) return;
    if (!agendamentoDetalhesId) return;
    confirmAction("Excluir Agendamento", "Tem certeza que deseja excluir este agendamento?", async () => {
        const res = await apiFetch(`/api/agendamentos/${agendamentoDetalhesId}`, {method: 'DELETE'});
        if (res.ok) {
            showToast("Agendamento excluído.", "success");
            closeModal('modalDetalhesAgendamento');
            carregarAgenda();
        } else {
            const err = await res.json();
            showToast(err.erro || "Erro ao excluir agendamento.", "error");
        }
    });
}


async function verificarExigirSenhaAgendamento(callback) {
    if (!isAdminGlobal) { callback(); return; }
    const res = await apiFetch('/api/config/exigir_senha_agendamento/status');
    const data = await res.json();
    if (!data.ativo) { callback(); return; }
    const modal = document.getElementById('modalSenhaConfig');
    document.getElementById('senha-titulo').innerText = 'Senha de Administrador';
    document.getElementById('senha-mensagem').innerHTML = 'Digite a senha para criar um agendamento:';
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
            window.senhaAgendamentoGlobal = senha;
            callback();
        } else {
            showToast("Senha incorreta", "error");
        }
        btnOk.onclick = originalOnclick;
    };
    openModal('modalSenhaConfig');
}


function navegarParaAgendamento(ag) {
    if (!ag || !ag.data || !ag.periodo) return;

    // 1. Atualiza periodoAtual e o select visual correspondente
    periodoAtual = ag.periodo;
    const periodoInput = document.getElementById('agenda-periodo');
    if (periodoInput) periodoInput.value = ag.periodo;
    if (periodoAgendaSelect) {
        periodoAgendaSelect.selectedValue = ag.periodo;
        const opt = periodoAgendaSelect.options.find(o => o.value === ag.periodo);
        const selectedSpan = periodoAgendaSelect.container.querySelector('.select-selected span');
        if (selectedSpan && opt) selectedSpan.textContent = opt.text;
        periodoAgendaSelect.container.querySelectorAll('.select-items div').forEach(div => {
            div.classList.remove('same-as-selected');
            if (opt && div.textContent === opt.text) div.classList.add('same-as-selected');
        });
    }

    // Atualiza a data (sem disparar o onChange do flatpickr, para evitar
    // uma segunda chamada concorrente de carregarAgenda())
    if (flatpickrInstance) flatpickrInstance.setDate(ag.data, false);
    const dataInput = document.getElementById('agenda-data');
    if (dataInput) dataInput.value = ag.data;

    // 2. Renderiza a tabela correta e, 3. após o carregamento, destaca a célula
    carregarAgenda().then(() => {
        if (!ag.aula) return;
        const celula = document.querySelector(`#tabela-agenda td[data-aula="${ag.aula}"]`);
        if (celula) {
            celula.classList.add('agendamento-destaque');
            setTimeout(() => celula.classList.remove('agendamento-destaque'), 2500);
        }
    });
}


async function carregarProximosAgendamentos() {
    const res = await apiFetch('/api/agendamentos/datas-com-agendamentos');
    const proximos = await res.json();
    const container = document.getElementById('lista-proximos');
    container.innerHTML = '';
    if (proximos.length === 0) {
        container.innerHTML = '<p style="color:var(--light); font-style:italic;">Nenhum agendamento futuro.</p>';
        return;
    }
    proximos.slice(0, 5).forEach(ag => {
        const span = document.createElement('span');
        span.className = 'proximo-dia';
        const dataFormatada = new Date(ag.data + 'T00:00:00').toLocaleDateString('pt-BR');
        span.textContent = dataFormatada;
        span.title = `${ag.professor} - ${ag.materia}`;
        span.addEventListener('click', () => navegarParaAgendamento(ag));
        container.appendChild(span);
    });
}


async function carregarAgendamentosPassados() {
    const res = await apiFetch('/api/agendamentos/passados');
    const datas = await res.json();
    const container = document.getElementById('lista-passados');
    container.innerHTML = '';
    if (datas.length === 0) {
        container.innerHTML = '<p style="color:var(--light); font-style:italic;">Nenhum agendamento passado.</p>';
        return;
    }
    datas.forEach(ag => {
        const span = document.createElement('span');
        span.className = 'passado-dia';
        const dataFormatada = new Date(ag.data + 'T00:00:00').toLocaleDateString('pt-BR');
        span.textContent = dataFormatada;
        span.title = `${ag.professor} - ${ag.materia}`;
        span.addEventListener('click', () => navegarParaAgendamento(ag));
        container.appendChild(span);
    });
}


function limparFormAgenda() {
    document.getElementById('agenda-titulo').innerText = 'Novo Agendamento';
    document.getElementById('agenda-existente').style.display = 'none';
    document.getElementById('agenda-form').style.display = 'block';
    document.getElementById('agenda-prof').value = '';
    document.getElementById('agenda-mat').value = '';
    document.getElementById('agenda-uso').value = '';
}


async function salvarAgendamento() {
    return runAction('salvarAgendamento', 'btn-agendar', async () => {
        if (!isAdminGlobal) return;
        const prof = document.getElementById('agenda-prof').value;
        const mat = document.getElementById('agenda-mat').value;
        const uso = document.getElementById('agenda-uso').value;
        if(!prof || !mat || !uso) return showToast("Preencha todos os campos.", "warning");
        const dia = parseInt(document.getElementById('agenda-dia').value);
        const aula = parseInt(document.getElementById('agenda-aula').value);
        const periodo = document.getElementById('agenda-periodo-modal').value;
        const data = document.getElementById('agenda-data-modal').value;
        let payload = {data, periodo, dia, aula, professor: prof, materia: mat, uso};
        if (window.senhaAgendamentoGlobal) {
            payload.senha = window.senhaAgendamentoGlobal;
            window.senhaAgendamentoGlobal = null;
        }
        const res = await apiFetch('/api/agendamentos', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        if (res.status === 400) {
            const err = await res.json();
            showToast(err.erro || "Erro ao agendar.", "error");
            return;
        }
        if (res.ok) {
            showToast("Agendamento salvo!", "success");
            closeModal('modalAgendamento');
            carregarAgenda();
        } else {
            showToast("Erro ao agendar.", "error");
        }
    });
}


async function excluirAgendamentoAtual() {
    if (!isAdminGlobal) return;
    if(!agendamentoAtualId) return;
    confirmAction("Excluir Agendamento", "Tem certeza que deseja excluir este agendamento?", async () => {
        const res = await apiFetch(`/api/agendamentos/${agendamentoAtualId}`, {method: 'DELETE'});
        if (res.ok) {
            showToast("Agendamento excluído.", "success");
            closeModal('modalAgendamento');
            agendamentoAtualId = null;
            carregarAgenda();
        } else {
            const err = await res.json();
            showToast(err.erro || "Erro ao excluir agendamento.", "error");
        }
    });
}


function initFlatpickr() {
    const currentYear = new Date().getFullYear();
    const meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
    const years = [currentYear];
    flatpickrInstance = flatpickr("#agenda-data-alt", {
        locale: "pt",
        dateFormat: "Y-m-d",
        altInput: true,
        altFormat: "d/m/Y",
        defaultDate: new Date(),
        minDate: new Date(currentYear, 0, 1),
        maxDate: new Date(currentYear, 11, 31),
        disableMobile: true,
        onChange: function(selectedDates, dateStr, instance) {
            document.getElementById('agenda-data').value = dateStr;
            carregarAgenda();
        },
        onReady: function(selectedDates, dateStr, instance) {
            document.getElementById('agenda-data').value = dateStr;
            const navigation = instance.calendarContainer.querySelector('.flatpickr-months');
            if (navigation) navigation.style.display = 'none';
            const header = document.createElement('div');
            header.className = 'custom-fp-header';
            const monthSelectHtml = `<div class="fake-select" id="month-trigger"><span id="month-label">${meses[new Date().getMonth()]}</span><div class="fake-options" id="month-list">${meses.map((m, i) => `<div data-val="${i}">${m}</div>`).join('')}</div></div>`;
            const yearSelectHtml = `<div class="fake-select" id="year-trigger"><span id="year-label">${currentYear}</span><div class="fake-options" id="year-list">${years.map(y => `<div data-val="${y}">${y}</div>`).join('')}</div></div>`;
            header.innerHTML = monthSelectHtml + yearSelectHtml;
            instance.calendarContainer.prepend(header);
            document.querySelectorAll('.fake-select').forEach(select => {
                select.addEventListener('click', function(e) { e.stopPropagation(); this.classList.toggle('active'); });
            });
            header.querySelectorAll('#month-list div').forEach(opt => {
                opt.addEventListener('click', (e) => { const val = parseInt(e.target.dataset.val); instance.changeMonth(val, false); document.getElementById('month-label').innerText = meses[val]; });
            });
            header.querySelectorAll('#year-list div').forEach(opt => {
                opt.addEventListener('click', (e) => { const val = parseInt(e.target.dataset.val); if (val === currentYear) { instance.changeYear(val); document.getElementById('year-label').innerText = val; } });
            });
            document.addEventListener('click', () => { document.querySelectorAll('.fake-select').forEach(s => s.classList.remove('active')); });
        }
    });
}
