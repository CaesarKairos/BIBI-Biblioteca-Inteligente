"""Check preserved behaviors and editorial layout using a real Chromium browser.
Run separately: python tests/browser_check.py
Requires playwright and an installed Edge/Chrome; no real BIBI data is opened.
"""
import contextlib
import json
import os
from pathlib import Path
import re
import sys
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests.test_regression import original, modular, TEMP, ROOT
from playwright.sync_api import sync_playwright
import requests

BROWSER=next((str(p) for p in [Path(os.environ.get('PROGRAMFILES(X86)',''))/'Microsoft/Edge/Application/msedge.exe',Path(os.environ.get('PROGRAMFILES',''))/'Google/Chrome/Application/chrome.exe'] if p.is_file()),None)
if not BROWSER: raise SystemExit('Install Chromium with: python -m playwright install chromium')

# CDN files are cached only for this run. A failed CDN download fails validation.
cache={}
urls=['https://cdn.jsdelivr.net/npm/chart.js','https://cdn.jsdelivr.net/npm/flatpickr',
      'https://npmcdn.com/flatpickr/dist/l10n/pt.js','https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css']
for url in urls:
    response=requests.get(url,timeout=45)
    response.raise_for_status()
    cache[url]=(response.content,response.headers.get('content-type','text/javascript'))

results=[]
with sync_playwright() as playwright:
    browser=playwright.chromium.launch(executable_path=BROWSER,headless=True)
    for admin in [True,False]:
        variants=[]
        for name,module in [('original',original),('modular',modular)]:
            with contextlib.closing(module.db_manager.get_connection()) as conn, conn:
                conn.execute("INSERT OR REPLACE INTO Configuracoes VALUES('bloquear_email','true')")
            context=browser.new_context(viewport={'width':1200,'height':700},locale='pt-BR',timezone_id='America/Sao_Paulo')
            page=context.new_page(); errors=[]
            page.on('pageerror',lambda error: errors.append(str(error)))
            def serve(route):
                request=route.request
                from urllib.parse import urlsplit
                url=urlsplit(request.url)
                path=url.path+('?' + url.query if url.query else '')
                response=module.app.test_client().open(path,method=request.method,data=request.post_data_buffer,
                    content_type=request.headers.get('content-type'),environ_overrides={'REMOTE_ADDR':'127.0.0.1' if admin else '10.0.0.1'})
                route.fulfill(status=response.status_code,body=response.data,content_type=response.content_type)
                response.close()
            def external(route):
                url=route.request.url
                if url.startswith('https://covers.test/'):
                    # Capas sintéticas só para o teste: proporções variadas, sem rede.
                    index = int(url.rsplit('/',1)[-1])
                    colors = ['#755044','#48624f','#c49b62','#4e596e']
                    cover_width = 100 if index % 2 else 90
                    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{cover_width}" height="140" viewBox="0 0 {cover_width} 140"><rect width="100%" height="100%" fill="{colors[index % 4]}"/><path d="M8 0V140" stroke="#ffffff" opacity=".15"/><circle cx="50" cy="60" r="24" fill="none" stroke="#f8e9d0" opacity=".6"/><text x="15" y="28" fill="#f8e9d0" font-size="9">LEITURAS</text><text x="15" y="115" fill="#f8e9d0" font-size="11">Volume {index+1}</text></svg>'
                    route.fulfill(body=svg, content_type='image/svg+xml'); return
                if url in cache:
                    body,content_type=cache[url]; route.fulfill(body=body,content_type=content_type)
                else:
                    # Fonts are the same deterministic fallback in both variants.
                    route.fulfill(body='',content_type='text/css')
            page.route('**/*',external)
            page.route('http://bibi.test/**',serve)
            def settle():
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(150)
            def snapshot():
                return page.evaluate("""() => Array.from(document.querySelectorAll('body *')).filter(e => !['SCRIPT','LINK','STYLE'].includes(e.tagName) && !e.closest('.flatpickr-calendar')).map(e => {
                    const s=getComputedStyle(e), r=e.getBoundingClientRect();
                    return [e.tagName,e.id,e.className.baseVal ?? e.className,s.display,s.color,s.backgroundColor,s.fontSize,s.position,Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height),e.style.cssText];
                })""")
            views={}
            with patch('random.choice',side_effect=lambda values:values[0]):
                page.goto('http://bibi.test/'); settle(); views['landing']=snapshot()
                landing_box = page.locator('.container').bounding_box()
                page.evaluate("showSection('about')"); settle(); views['about']=snapshot()
                if name == 'modular':
                    assert page.locator('.container').bounding_box() == landing_box
                    assert page.locator('#about-section').evaluate('e => e.scrollHeight > e.clientHeight')
                    assert page.evaluate('document.documentElement.scrollHeight <= innerHeight')
                page.goto('http://bibi.test/app'); settle(); views['initial']=snapshot()
                for tab in (['acervo','emp','age','lei','dash'] if admin else ['acervo','age']):
                    page.evaluate('(id) => tab(id)',tab); settle(); views[tab]=snapshot()
                page.evaluate('toggleTheme(true)'); settle(); views['dark']=snapshot()
                page.evaluate('toggleTheme(false)'); settle()
                if admin:
                    page.evaluate("tab('acervo')"); settle()
                    page.locator('#acervo button',has_text='+ Adicionar Livro').click()
                    views['modalAddLivro']=snapshot()
                    page.get_by_role('button',name='Adicionar Manualmente').click()
                    page.locator('#manual-titulo').fill('Livro de teste')
                    page.locator('#manual-autor').fill('Autora')
                    page.locator('#manual-qtd').fill('3')
                    if name == 'modular': page.locator('#manual-paginas').fill('250')
                    page.locator('#btn-salvar-manual').click(); settle()
                    assert page.locator('#modalManualLivro').evaluate("e => e.style.display")=='none'
                    books=module.app.test_client().get('/api/livros').get_json()
                    assert any(book['titulo']=='Livro de teste' for book in books)
                    if name == 'modular':
                        created = next(book for book in books if book['titulo']=='Livro de teste')
                        assert created['numero_paginas'] == 250
                        page.locator('.book').first.click(); settle()
                        assert page.locator('#det-paginas').inner_text() == '250 páginas'
                        page.evaluate('editarLivroSelecionado()'); settle()
                        assert page.locator('#edit-paginas').input_value() == '250'
                        page.locator('#edit-paginas').fill('0')
                        page.locator('#btn-salvar-edicao').click(); settle()
                        assert page.locator('#modalEditarLivro').is_visible()
                        assert module.app.test_client().get('/api/livros').json[0]['numero_paginas'] == 250
                        page.locator('#edit-paginas').fill('410')
                        page.locator('#btn-salvar-edicao').click(); settle()
                        assert not page.locator('#modalEditarLivro').is_visible()
                        assert page.locator('#det-paginas').inner_text() == '410 páginas'
                        page.locator('#fechar-detalhes').click()
                    # This generated book has a random manual ISBN; compare UI after hiding toast text.
                    page.evaluate("document.querySelectorAll('.toast').forEach(e => e.remove())")
                    views['created']=snapshot()
                    page.evaluate("tab('lei')"); settle()
                    page.evaluate("openModal('modalLeitor')")
                    views['modalLeitor']=snapshot()
                    page.evaluate("closeModal('modalLeitor')")
                    page.evaluate("openModal('modalConfiguracoes')")
                    views['modalConfiguracoes']=snapshot()
                    page.evaluate("closeModal('modalConfiguracoes')")
            variants.append((views,errors)); results.append({'version':name,'admin':admin,'views':len(views),'errors':errors})
            context.close()
        left,right=variants
        assert right[1]==[], ('Unexpected browser errors', right[1])
        if admin: assert left[1]==[], ('Baseline admin errors',left[1])
        # O layout de ambas as páginas evoluiu; verificamos comportamento e geometria.
    # Dedicated behavior checks for corrected flows, independent of the baseline.
    admin=True; module=modular
    context=browser.new_context(viewport={'width':1200,'height':700},locale='pt-BR',timezone_id='America/Sao_Paulo')
    page=context.new_page(); failures=[]
    page.on('pageerror',lambda error: failures.append(str(error)))
    page.route('**/*',external); page.route('http://bibi.test/**',serve)
    page.goto('http://bibi.test/app'); settle()
    page.evaluate("tab('acervo'); openModalManual()")
    page.locator('#manual-titulo').fill('Retry book')
    page.locator('#manual-autor').fill('Autora')
    page.locator('#manual-qtd').fill('1')
    attempts=[]
    def fail_post(route):
        if route.request.method=='POST':
            attempts.append(route.request.url); route.abort('failed')
        else: route.fallback()
    page.route('**/api/livros',fail_post)
    page.evaluate('async () => { await Promise.all([salvarLivroManual(), salvarLivroManual()]); }')
    assert len(attempts)==1, attempts
    assert not page.locator('#btn-salvar-manual').is_disabled()
    assert page.locator('#manual-titulo').input_value()=='Retry book'
    assert page.locator('#modalManualLivro').evaluate("e => e.style.display")=='flex'
    assert page.locator('.toast.error').count()>=1
    assert page.locator('.toast.success').count()==0
    page.unroute('**/api/livros',fail_post)
    page.locator('#btn-salvar-manual').click(); settle()
    assert page.locator('#modalManualLivro').evaluate("e => e.style.display")=='none'
    assert page.locator('.toast.success').count()>=1
    page.evaluate("document.querySelectorAll('.toast').forEach(e => e.remove())")
    def reject_delete(route): route.fulfill(status=409,json={'erro':'Conflito de teste'})
    page.route('**/api/leitores/99',reject_delete)
    page.evaluate('excluirLeitor(99)')
    page.locator('#confirm-btn-sim').click(); settle()
    assert page.locator('#modalConfirmacao').evaluate("e => e.style.display")=='flex'
    assert not page.locator('#confirm-btn-sim').is_disabled()
    assert page.locator('.toast.success').count()==0
    assert 'Conflito de teste' in page.locator('.toast.error').last.inner_text()
    page.evaluate("closeModal('modalConfirmacao')")
    danger='<img src=x onerror="window.__injected=true">'
    page.evaluate("""danger => {
        window.__injected=false;
        exibirListaLeitores([{id:99,nome:danger,tipo:'estudante',sala:danger,periodo:danger,telefone:danger}]);
        verDetalhes({id:1,titulo:danger,autor:danger,temas:danger,descricao:danger,disponivel:1});
    }""",danger)
    assert page.locator('#lista-leitores img').count()==0
    assert page.locator('#det-temas img').count()==0
    assert danger in page.locator('#lista-leitores').inner_text()
    def loan_data(route): route.fulfill(json=[{'id':1,'livro':danger,'leitor':danger,'telefone':danger,'serie':danger,'capa':"x'); color:red; /*"}])
    def agenda_data(route): route.fulfill(json=[{'id':1,'aula':1,'professor':danger,'materia':danger,'uso':danger}])
    def ranking_data(route): route.fulfill(json=[{'nome':danger,'tipo':'estudante','sala':danger,'total':1}])
    def top_data(route): route.fulfill(json=[{'id':1,'titulo':danger,'autor':danger,'capa':danger,'total_emprestimos':1}])
    page.route('**/api/emprestimos/todos',loan_data)
    page.route('**/api/agendamentos?*',agenda_data)
    page.route('**/api/emprestimos/ranking-leitores',ranking_data)
    page.route('**/api/emprestimos/mais-emprestados',top_data)
    page.evaluate("async () => { await filtrarEmprestimos('todos'); await carregarAgenda(); await carregarRankingLeitores(); await carregarTopLivros(); }")
    assert page.locator('#lista-ativos img, #tabela-agenda img, #ranking-leitores img, #top-livros img').count()==0
    assert not page.evaluate('window.__injected')
    assert page.locator('#tabela-agenda td.ocupado').get_attribute('data-professor')==danger
    assert failures==[], failures
    context.close()
    screenshots = Path(os.environ.get('BIBI_SCREENSHOTS', str(Path(TEMP.name) / 'screenshots')))
    screenshots.mkdir(parents=True, exist_ok=True)
    # Populate every shelf, including unavailable books and varied page counts.
    categories = ['Ficção', 'Não-ficção', 'Poesia', 'Quadrinhos']
    for index in range(16):
        module.app.test_client().post('/api/livros', json={
            'manual': True, 'titulo': f'Leituras da biblioteca {index + 1}', 'autor': 'Autora da biblioteca',
            'quantidade': 2, 'categoria': categories[index % 4],
            'numero_paginas': [80, 400, 720, None][index % 4],
            'capa': f'https://covers.test/{index}',
            'descricao': 'Uma história para descobrir entre as prateleiras. ' * 12,
            'localizacao': 'Prateleira A',
        })
    with module.db_manager.connection() as conn:
        conn.execute('UPDATE Livros SET quantidade_disponivel=0 WHERE id % 4=0')
        conn.execute("INSERT INTO Usuarios(nome,tipo,email,sala,periodo) VALUES ('Ana Leitora','estudante','ana@example.test','9A','Manhã')")
        conn.execute("INSERT INTO Emprestimo(usuarios_id,livros_id,data_emprestimo,data_vencimento,quantidade,status) VALUES (1,1,date('now'),date('now','+7 days'),1,'Aprovado')")
        conn.execute('UPDATE Livros SET quantidade_disponivel=quantidade_disponivel-1 WHERE id=1')
        for user_id, book_id, reader in [(2,3,'Leitora com nome completo para verificar alinhamento'),(3,4,'Leitor da biblioteca')]:
            conn.execute("INSERT INTO Usuarios(id,nome,tipo,email,sala,periodo) VALUES (?,?,'estudante',?,'8B','Tarde')", (user_id,reader,f'leitor{user_id}@example.test'))
            conn.execute("INSERT INTO Emprestimo(usuarios_id,livros_id,data_emprestimo,data_vencimento,quantidade,status) VALUES (?,?,date('now'),date('now','+7 days'),1,'Aprovado')", (user_id,book_id))
        conn.execute("UPDATE Livros SET nome='Um título longo para conferir a relação entre as colunas e os botões de cada empréstimo' WHERE id=3")
        conn.commit()
    for admin in [True, False]:
        for width, height in [(1366,768),(1920,1080),(800,900),(390,844)]:
            context = browser.new_context(viewport={'width':width,'height':height}, locale='pt-BR', reduced_motion='reduce')
            page = context.new_page(); failures = []
            page.on('pageerror', lambda error: failures.append(str(error)))
            page.route('**/*', external); page.route('http://bibi.test/**', serve)
            page.goto('http://bibi.test/app'); settle()
            if width > 700:
                left_before = page.locator('.sidebar').bounding_box()['width']
                right_before = page.locator('.right-bar').bounding_box()['width']
                for handle_id, delta in [('resize-sidebar',40), ('resize-details',-32)]:
                    handle = page.locator('#' + handle_id)
                    box = handle.bounding_box()
                    page.mouse.move(box['x'] + 4, 100)
                    page.mouse.down(); page.mouse.move(box['x'] + 4 + delta, 100, steps=6); page.mouse.up()
                assert page.locator('.sidebar').bounding_box()['width'] == left_before + 40
                assert page.locator('.right-bar').bounding_box()['width'] == right_before + 32
                page.reload(); settle()
                assert page.locator('.sidebar').bounding_box()['width'] == left_before + 40
                for selector in ['#resize-sidebar','#resize-details']:
                    page.locator(selector).focus(); page.keyboard.press('End')
                assert page.locator('.sidebar').bounding_box()['width'] <= 320
                assert page.locator('.right-bar').bounding_box()['width'] <= 420
                assert page.locator('.content-area').bounding_box()['width'] >= 320
                page.set_viewport_size({'width':701,'height':height}); settle()
                assert page.locator('.content-area').bounding_box()['width'] >= 317
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.set_viewport_size({'width':width,'height':height}); settle()
                page.locator('#resize-sidebar').dblclick(position={'x':4,'y':100})
                page.locator('#resize-details').dblclick(position={'x':4,'y':100})
            else:
                assert not page.locator('#resize-sidebar').is_visible()
            assert page.locator('.shelf').count() == 5
            assert page.locator('.shelf h3').all_text_contents() == ['Recomendações da BIBI', *categories]
            for icon in page.locator('.bibi-cat-icon').all():
                assert 'cat-svgrepo-com.svg' in icon.evaluate('e => getComputedStyle(e).maskImage')
            assert page.locator('.right-bar').inner_text().strip() == ''
            assert page.locator('#prateleira-bibi').get_attribute('data-content-source') == 'placeholder'
            assert page.locator('.book').evaluate_all("books => books.every(book => getComputedStyle(book).width === '80px' && getComputedStyle(book).height === '110px')")
            assert page.locator('.book.unavailable').count() > 0
            assert page.locator('.book').first.evaluate("e => getComputedStyle(e).backgroundSize") == 'cover'
            unavailable = page.locator('.book.unavailable').first
            assert 'Não existem exemplares disponíveis' in unavailable.get_attribute('title')
            unavailable.click(); settle()
            assert page.locator('#info-livro').is_visible()
            assert page.locator('#det-estoque').inner_text() == '0'
            if admin: assert page.locator('#btn-emprestar').is_disabled()
            cover = page.locator('#det-capa').bounding_box()
            assert (cover['width'], cover['height']) == (140,200)
            assert page.locator('#det-capa').evaluate("e => getComputedStyle(e).backgroundSize") == 'contain'
            page.locator('#fechar-detalhes').click()
            assert not page.locator('#info-livro').is_visible()
            assert page.evaluate('livroSelecionado') is None
            assert page.locator('.book[aria-pressed="true"]').count() == 0
            another = page.locator('.book:not(.unavailable)').first
            another.focus(); page.keyboard.press('Enter'); settle()
            assert page.locator('#info-livro').is_visible()
            if admin: assert not page.locator('#btn-emprestar').is_disabled()
            assert page.locator('.cat-waving').evaluate('e => e.paused')
            for dark in [False, True]:
                page.evaluate('(dark) => toggleTheme(dark)', dark); settle()
                for section in (['acervo','dash','emp','lei','age'] if admin else ['acervo','age']):
                    page.evaluate('(section) => tab(section)', section); settle()
                    geometry = page.evaluate('''() => {
                        const shell=document.querySelector('.app-container').getBoundingClientRect();
                        const main=document.querySelector('.content-area');
                        return {width:innerWidth, overflow:document.documentElement.scrollWidth>innerWidth,
                            shellWidth:shell.width, shellX:shell.x, shellY:shell.y,
                            mainOverflow:main.scrollWidth>main.clientWidth,
                            bodyHeight:document.documentElement.scrollHeight};
                    }''')
                    assert not geometry['overflow'], (width,section,geometry)
                    assert not geometry['mainOverflow'], (width,section,geometry)
                    assert geometry['shellWidth'] == width and geometry['shellX'] == 0
                    if width > 700:
                        assert geometry['shellY'] == 0 and geometry['bodyHeight'] == height, geometry
                        assert page.locator('.sidebar').is_visible() and page.locator('.right-bar').is_visible()
                    if admin and width in (1366,1920) and section in ('acervo','dash','age'):
                        page.screenshot(path=str(screenshots / f'{width}-{section}-{"dark" if dark else "light"}.png'))
                    if admin and section == 'emp':
                        assert page.locator('#btn-filtro-todos').evaluate('e => getComputedStyle(e).backgroundColor') != page.locator('#btn-filtro-ativos').evaluate('e => getComputedStyle(e).backgroundColor')
                        assert page.locator('.tabela-emprestimos tbody tr').evaluate_all('''rows => rows.every(row => {
                            const cells=[...row.cells].map(cell => cell.getBoundingClientRect());
                            return cells.every(cell => Math.abs(cell.y-cells[0].y)<1 && Math.abs(cell.height-cells[0].height)<1);
                        })''')
                        page.screenshot(path=str(screenshots / f'{width}-loans-{"dark" if dark else "light"}.png'))
                if admin:
                    page.evaluate("tab('acervo'); editarLivroSelecionado()"); settle()
                    assert page.locator('#edit-paginas').is_visible()
                    assert page.locator('#modalEditarLivro .modal-content').evaluate("e => getComputedStyle(e).backgroundColor") == page.locator('.sidebar').evaluate("e => getComputedStyle(e).backgroundColor")
                    page.screenshot(path=str(screenshots / f'{width}-form-{"dark" if dark else "light"}.png'))
                    page.keyboard.press('Escape')
                    assert not page.locator('#modalEditarLivro').is_visible()
            page.evaluate("tab('acervo'); definirRecomendacoesBibi([todosLivros[1].id])"); settle()
            assert page.locator('#prateleira-bibi .book').count() == 1
            page.evaluate('definirRecomendacoesBibi([])')
            assert page.locator('#prateleira-bibi .book').count() == 0
            assert page.locator('.shelf').count() == 5
            page.locator('#busca-acervo').fill('nenhum-titulo-compativel'); settle()
            assert page.locator('.book').count() == 0 and page.locator('.shelf').count() == 5
            if not admin:
                assert page.locator('#m-dash, #m-emp, #m-lei, #btn-emprestar').count() == 0
                page.keyboard.press('Control+2'); settle()
                assert page.locator('#age').is_visible()
                page.keyboard.press('Control+1'); settle()
                assert page.locator('#acervo').is_visible()
            assert failures == [], (width, admin, failures)
            if admin:
                for dark in [False,True]:
                    page.evaluate('(dark) => toggleTheme(dark)',dark); settle()
                    page.goto('http://bibi.test/'); settle()
                    assert page.locator('body').evaluate("(e) => e.classList.contains('dark-mode')") == dark
                    home_box = page.locator('.container').bounding_box()
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth && document.documentElement.scrollHeight <= innerHeight')
                    page.screenshot(path=str(screenshots / f'{width}-hero-{"dark" if dark else "light"}.png'))
                    page.evaluate("showSection('about')"); settle()
                    assert page.locator('.container').bounding_box() == home_box
                    page.locator('#about-section').evaluate('e => e.scrollTop=e.scrollHeight')
                    assert page.locator('.social-footer').is_visible()
                    page.screenshot(path=str(screenshots / f'{width}-about-{"dark" if dark else "light"}.png'))
                    page.goto('http://bibi.test/app'); settle()
            assert failures == [], (width, admin, failures)
            context.close()
    print('Editorial UI passed: 2 roles, 4 viewports, light/dark, 5 shelves, selection, close, keyboard, pages, availability, filters and layout.')
    print(f'Screenshots: {screenshots}')
    browser.close()
    print('Corrected UI: public access, retry, duplicate submit guard, HTTP failure and safe text passed.')
print(json.dumps(results,ensure_ascii=False,indent=2))
print('Browser checks passed: bounded landing, resizable panels, aligned loan rows and preserved interactions.')
