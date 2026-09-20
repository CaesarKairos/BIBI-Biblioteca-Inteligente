// Restabelece os contratos originais de element.style e element.onclick.
// As declaracoes visuais vivem no CSS; os eventos vivem neste arquivo.
// Propriedades onclick continuam podendo ser substituidas pelos modais de senha.
(function initializeTemplate() {
    const handlers = {
        h1: function(event) { window.location='/' },
        h2: function(event) { this.style.display='none' },
        h3: function(event) { tab('dash') },
        h4: function(event) { tab('acervo') },
        h5: function(event) { tab('emp') },
        h6: function(event) { tab('age') },
        h7: function(event) { tab('lei') },
        h8: function(event) { toggleTheme() },
        h9: function(event) { abrirConfiguracoes() },
        h10: function(event) { tab('emp'); setTimeout(()=>filtrarEmprestimos('ativos'), 100); },
        h11: function(event) { tab('emp'); setTimeout(()=>filtrarEmprestimos('atrasados'), 100); },
        h12: function(event) { tab('emp'); setTimeout(()=>filtrarEmprestimos('hoje'), 100); },
        h13: function(event) { openModal('modalAddLivro') },
        h14: function(event) { filtrarAcervo() },
        h15: function(event) { filtrarEmprestimos('todos') },
        h16: function(event) { filtrarEmprestimos('ativos') },
        h17: function(event) { filtrarEmprestimos('atrasados') },
        h18: function(event) { filtrarEmprestimos('hoje') },
        h19: function(event) { filtrarEmprestimos('devolvidos') },
        h20: function(event) { filtrarLeitores() },
        h21: function(event) { openModal('modalLeitor') },
        h22: function(event) { emprestarSelecionado() },
        h23: function(event) { editarLivroSelecionado() },
        h24: function(event) { confirmarExclusaoLivro() },
        h25: function(event) { salvarLivro() },
        h26: function(event) { openModalManual() },
        h27: function(event) { closeModal('modalAddLivro') },
        h28: function(event) { previewCapaManual(event) },
        h29: function(event) { salvarLivroManual() },
        h30: function(event) { closeModal('modalManualLivro') },
        h31: function(event) { previewCapaEdit(event) },
        h32: function(event) { salvarEdicaoLivro() },
        h33: function(event) { closeModal('modalEditarLivro') },
        h34: function(event) { aplicarMascaraTelefone(this) },
        h35: function(event) { salvarLeitor() },
        h36: function(event) { closeModal('modalLeitor') },
        h37: function(event) { buscarLeitoresAutocomplete() },
        h38: function(event) { formatarSala() },
        h39: function(event) { confirmarEmprestimoRapido() },
        h40: function(event) { closeModal('modalEmprestimoRapido') },
        h41: function(event) { salvarConfigGerais() },
        h42: function(event) { closeModal('modalConfiguracoes') },
        h43: function(event) { salvarConfigAgenda() },
        h44: function(event) { closeModal('modalConfigAgenda') },
        h45: function(event) { verificarSenhaConfig() },
        h46: function(event) { closeModal('modalSenhaConfig') },
        h47: function(event) { closeModal('modalAtrasos') },
        h48: function(event) { closeModal('modalDevolucoesHoje') },
        h49: function(event) { excluirAgendamentoAtual() },
        h50: function(event) { closeModal('modalAgendamento') },
        h51: function(event) { salvarAgendamento() },
        h52: function(event) { closeModal('modalConfirmacao') },
        h53: function(event) { excluirAgendamentoDetalhes() },
        h54: function(event) { closeModal('modalDetalhesAgendamento') },
        h55: function(event) { showSection('home') },
        h56: function(event) { showSection('about') },
        h57: function(event) { window.location.href='/app' },
        h58: function(event) { fecharDetalhes() },
    };
    for (const eventName of ["onblur", "onchange", "onclick", "onerror", "oninput"]) {
        document.querySelectorAll('[data-bibi-' + eventName + ']').forEach(element => {
            element[eventName] = handlers[element.getAttribute('data-bibi-' + eventName)];
        });
    }
    // Manter style.display legivel e a precedencia inline, como no monolito.
    // Isso evita alterar os testes de visibilidade e os resets usados pela UI.
    for (const sheet of document.styleSheets) {
        if (!sheet.href || !new URL(sheet.href).pathname.startsWith('/static/css/')) continue;
        for (const rule of sheet.cssRules) {
            if (!rule.selectorText || !rule.selectorText.startsWith('[data-bibi-style=')) continue;
            document.querySelectorAll(rule.selectorText).forEach(element => {
                element.style.cssText = rule.style.cssText;
                element.removeAttribute('data-bibi-style');
            });
        }
    }
})();
