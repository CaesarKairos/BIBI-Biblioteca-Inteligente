"""Run with python tests/browser_loan_search.py (Playwright Chromium required).

Exercises the real loan markup and renderer with deterministic API responses.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
template = (ROOT / 'templates/app.html').read_text(encoding='utf-8')
section = template.split('<div id="emp" class="section">', 1)[1].split('<div id="age"', 1)[0]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content(section)
    page.add_script_tag(content="""
        let isAdminGlobal = true, filtroEmprestimosAtual = 'todos';
        const rows = [
            {id: 1, leitor: 'João da Silva', livro: 'Livro A'},
            {id: 2, leitor: 'Maria Souza', livro: 'Livro B'},
            {id: 3, leitor: 'João da Silva', livro: 'Livro C'}
        ];
        let requests = 0, selected = null;
        async function apiFetch(url) {
            requests++;
            return {json: async () => url.endsWith('/ativos') ? rows.slice(0, 2) : rows};
        }
        function textElement(tag, text, className) {
            const e = document.createElement(tag);
            e.textContent = text;
            if (className) e.className = className;
            return e;
        }
        function coverBackground() {}
    """)
    page.add_script_tag(path=str(ROOT / 'static/js/emprestimos.js'))
    page.evaluate("filtrarEmprestimos('todos')")
    assert page.locator('tbody tr').count() == 3
    search = page.locator('#busca-emprestimos')
    search.fill('  SILVA joao  ')
    assert page.locator('tbody tr').count() == 2
    assert page.evaluate('requests') == 1
    page.evaluate("filtrarEmprestimos('ativos')")
    assert page.locator('tbody tr').count() == 1
    assert search.input_value() == '  SILVA joao  '
    # Verify the filtered row still targets the correct loan for return/renewal.
    page.evaluate('devolverEmprestimo = id => { selected = id; }; renovarEmprestimo = id => { selected = id; }')
    page.get_by_role('button', name='Devolver', exact=True).click()
    assert page.evaluate('selected') == 1
    page.get_by_role('button', name='Renovar', exact=True).click()
    assert page.evaluate('selected') == 1
    page.evaluate("rows.splice(0, 1); filtrarEmprestimos('ativos')")
    assert search.input_value() == '  SILVA joao  '
    assert page.locator('tbody tr').count() == 1
    assert page.locator('tbody').inner_text().find('Livro C') >= 0
    search.fill('inexistente')
    assert page.locator('tbody tr').count() == 0
    assert 'Nenhum empréstimo' in page.locator('#lista-ativos').inner_text()
    search.fill('')
    assert page.locator('tbody tr').count() == 2
    page.evaluate("filtrarEmprestimos('devolvidos')")
    assert page.get_by_role('button', name='Devolver', exact=True).count() == 0
    # An older, slower response must not replace the newest status filter.
    page.evaluate("""async () => {
        let release;
        apiFetch = async url => ({json: () => url.endsWith('/todos')
            ? new Promise(resolve => { release = resolve; }) : Promise.resolve([rows[0]])});
        const older = filtrarEmprestimos('todos');
        await Promise.resolve();
        await filtrarEmprestimos('ativos');
        release(rows);
        await older;
    }""")
    assert page.locator('tbody tr').count() == 1
    browser.close()
print('Loan search passed: partial names, accents, case, filters, actions, refresh, empty/clear and response order.')
