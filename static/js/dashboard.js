async function carregarGraficoGeneros() {
    if (!isAdminGlobal) return;
    const res = await apiFetch('/api/emprestimos/ativos-por-genero');
    const dados = await res.json();
    const ctx = document.getElementById('grafico-generos').getContext('2d');
    estadoVazioGrafico(ctx.canvas, dados);
    if (graficoGenerosInstance) graficoGenerosInstance.destroy();
    const isDark = document.body.classList.contains('dark-mode');
    const textColor = isDark ? '#f0e7de' : '#3e332a';
    const labels = dados.map(d => d.categoria);
    const valores = dados.map(d => d.total);
    const cores = ['#bc8a5f', '#8c8279', '#d4b59e', '#7d9b5e', '#CD853F', '#a3968c'];
    graficoGenerosInstance = new Chart(ctx, {
        type: 'pie',
        data: { labels, datasets: [{ data: valores, backgroundColor: cores.slice(0, labels.length), borderColor: isDark ? '#3c332c' : '#ffffff', borderWidth: 2 }] },
        options: { animation: {duration: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 220}, responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom', labels: { color: textColor, font: { family: 'Nunito', size: 12 }, padding: 15 } }, tooltip: { callbacks: { label: function(context) { const total = context.dataset.data.reduce((a,b)=>a+b,0); const value = context.raw; const percent = total > 0 ? Math.round((value/total)*100) : 0; return ` ${context.label}: ${value} (${percent}%)`; } } } } }
    });
}


async function carregarGraficoHistorico() {
    if (!isAdminGlobal) return;
    const res = await apiFetch('/api/emprestimos/historico-por-genero');
    const dados = await res.json();
    const ctx = document.getElementById('grafico-historico').getContext('2d');
    estadoVazioGrafico(ctx.canvas, dados);
    if (graficoHistoricoInstance) graficoHistoricoInstance.destroy();
    const isDark = document.body.classList.contains('dark-mode');
    const textColor = isDark ? '#f0e7de' : '#3e332a';
    const labels = dados.map(d => d.categoria);
    const valores = dados.map(d => d.total);
    const cores = ['#bc8a5f', '#8c8279', '#d4b59e', '#7d9b5e', '#CD853F', '#a3968c'];
    graficoHistoricoInstance = new Chart(ctx, {
        type: 'pie',
        data: { labels, datasets: [{ data: valores, backgroundColor: cores.slice(0, labels.length), borderColor: isDark ? '#3c332c' : '#ffffff', borderWidth: 2 }] },
        options: { animation: {duration: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 220}, responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom', labels: { color: textColor, font: { family: 'Nunito', size: 12 }, padding: 15 } }, tooltip: { callbacks: { label: function(context) { const total = context.dataset.data.reduce((a,b)=>a+b,0); const value = context.raw; const percent = total > 0 ? Math.round((value/total)*100) : 0; return ` ${context.label}: ${value} (${percent}%)`; } } } } }
    });
}


async function carregarRankingLeitores() {
    if (!isAdminGlobal) return;
    const res = await apiFetch('/api/emprestimos/ranking-leitores');
    const ranking = await res.json();
    const container = document.getElementById('ranking-leitores');
    container.innerHTML = '';
    if (ranking.length === 0) {
        container.innerHTML = '<li style="color:var(--light);">Nenhum empréstimo no trimestre.</li>';
        return;
    }
    ranking.forEach((r, index) => {
        const extra = r.tipo === 'estudante' ? ` - ${r.sala}` : ` (Prof.)`;
        const li = document.createElement('li');
        const total = textElement('span', `${r.total} empréstimos`);
        total.style.color = 'var(--green-earth)';
        li.append(textElement('strong', r.nome), document.createTextNode(extra + ' — '), total);
        container.appendChild(li);
    });
}


async function carregarTopLivros() {
    const res = await apiFetch('/api/emprestimos/mais-emprestados');
    const destaques = await res.json();
    const container = document.getElementById('top-livros');
    container.innerHTML = '';
    if (destaques.length === 0) {
        container.innerHTML = '<p style="color:var(--light); font-style:italic;">Nenhum empréstimo registrado ainda.</p>';
        return;
    }
    const top3 = destaques.slice(0, 3);
    top3.forEach((l, index) => {
        const item = document.createElement('div');
        item.className = 'top-livro-item';
        tornarAcionavel(item);
        item.onclick = () => { 
            const livroCompleto = todosLivros.find(tl => tl.id === l.id);
            if (livroCompleto) { verDetalhes(livroCompleto); tab('acervo'); }
        };
        const cover = textElement('div', '', 'top-livro-capa');
        coverBackground(cover, l.capa);
        const info = textElement('div', '', 'top-livro-info');
        info.append(textElement('h4', l.titulo), textElement('p', l.autor || 'Autor desconhecido'));
        item.append(cover, info, textElement('div', `${l.total_emprestimos}x`, 'top-livro-badge'));
        container.appendChild(item);
    });
}


async function carregarLivrosAdormecidos() {
    const res = await apiFetch('/api/livros/adormecidos');
    const adormecidos = await res.json();
    const container = document.getElementById('lista-adormecidos');
    container.innerHTML = '';
    if (adormecidos.length === 0) {
        container.innerHTML = '<p style="color:var(--light); font-style:italic;">Todos os livros tiveram empréstimos nos últimos 6 meses.</p>';
        return;
    }
    adormecidos.forEach(l => {
        const tag = document.createElement('span');
        tag.className = 'adormecido-tag';
        tornarAcionavel(tag);
        tag.textContent = l.titulo;
        tag.title = `${l.autor || 'Autor desconhecido'}`;
        tag.onclick = () => {
            const livroCompleto = todosLivros.find(tl => tl.id === l.id);
            if (livroCompleto) { verDetalhes(livroCompleto); tab('acervo'); }
        };
        container.appendChild(tag);
    });
}


async function carregarDashboard() {
    if (!isAdminGlobal) return;
    const resLivros = await apiFetch('/api/livros');
    const livros = await resLivros.json();
    todosLivros = livros;
    document.getElementById('stat-total').innerText = livros.length;
    const totalExemplares = livros.reduce((acc, l) => acc + (l.estoque || 0), 0);
    document.getElementById('stat-exemplares').innerText = totalExemplares;
    const resAtivos = await apiFetch('/api/emprestimos/ativos/count');
    const ativosData = await resAtivos.json();
    document.getElementById('stat-emp').innerText = ativosData.count;
    const resAtrasos = await apiFetch('/api/emprestimos/atrasos');
    const atrasos = await resAtrasos.json();
    document.getElementById('stat-atraso').innerText = atrasos.length;
    const resHoje = await apiFetch('/api/emprestimos/devolucoes-hoje');
    const hojeList = await resHoje.json();
    document.getElementById('stat-hoje').innerText = hojeList.length;
    const resLeitores = await apiFetch('/api/leitores');
    const leitores = await resLeitores.json();
    document.getElementById('stat-leitores').innerText = leitores.length;
    const hojeStr = new Date().toISOString().split('T')[0];
    const resAgenda = await apiFetch('/api/agendamentos?periodo=' + periodoAtual);
    const agenda = await resAgenda.json();
    const agendaFutura = agenda.filter(a => a.data >= hojeStr);
    document.getElementById('stat-agenda').innerText = agendaFutura.length;
    // Resumo local determinístico. Futuramente o mesmo renderizador pode receber
    // dados de um endpoint; não há geração, chatbot ou chamada de IA nesta versão.
    const hora = new Date().getHours();
    atualizarMensagemBibi({
        saudacao: hora < 12 ? 'Bom dia.' : hora < 18 ? 'Boa tarde.' : 'Boa noite.',
        texto: `A biblioteca reúne ${livros.length} títulos. Hoje, há ${hojeList.length} devoluções previstas. Boa leitura!`
    });
    carregarGraficoGeneros();
    carregarGraficoHistorico();
    carregarRankingLeitores();
    carregarTopLivros();
    carregarLivrosAdormecidos();
}

function atualizarMensagemBibi({saudacao, texto}) {
    document.getElementById('bibi-greeting').textContent = saudacao;
    document.getElementById('bibi-message-text').textContent = texto;
}

function estadoVazioGrafico(canvas, dados) {
    const id = `${canvas.id}-vazio`;
    let message = document.getElementById(id);
    if (!message) {
        message = textElement('p', 'Os gêneros aparecerão aqui quando houver empréstimos.', 'chart-empty');
        message.id = id;
        canvas.after(message);
    }
    const vazio = !dados.some(item => item.total > 0);
    message.hidden = !vazio;
    canvas.hidden = vazio;
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', dados.map(item => `${item.categoria}: ${item.total}`).join('; ') || 'Sem empréstimos');
}
