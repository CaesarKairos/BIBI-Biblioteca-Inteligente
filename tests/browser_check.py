"""Compare DOM, computed styles and interactions using a real Chromium browser.
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
                if url in cache:
                    body,content_type=cache[url]; route.fulfill(body=body,content_type=content_type)
                else:
                    # Fonts are the same deterministic fallback in both variants.
                    route.fulfill(body='',content_type='text/css')
            page.route('**/*',external)
            page.route('http://bibi.test/**',serve)
            def settle():
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(550)
            def snapshot():
                return page.evaluate("""() => Array.from(document.querySelectorAll('body *')).filter(e => !['SCRIPT','LINK','STYLE'].includes(e.tagName) && !e.closest('.flatpickr-calendar')).map(e => {
                    const s=getComputedStyle(e), r=e.getBoundingClientRect();
                    return [e.tagName,e.id,e.className.baseVal ?? e.className,s.display,s.color,s.backgroundColor,s.fontSize,s.position,Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height),e.style.cssText];
                })""")
            views={}
            with patch('random.choice',side_effect=lambda values:values[0]):
                page.goto('http://bibi.test/'); settle(); views['landing']=snapshot()
                page.evaluate("showSection('about')"); settle(); views['about']=snapshot()
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
                    page.locator('#btn-salvar-manual').click(); settle()
                    assert page.locator('#modalManualLivro').evaluate("e => e.style.display")=='none'
                    books=module.app.test_client().get('/api/livros').get_json()
                    assert any(book['titulo']=='Livro de teste' for book in books)
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
        assert left[1]==right[1],('New browser errors',left[1],right[1])
        for view in left[0]:
            if left[0][view]!=right[0][view]:
                pairs=[(i,a,b) for i,(a,b) in enumerate(zip(left[0][view],right[0][view])) if a!=b]
                raise AssertionError((admin,view,'DOM/style difference',pairs[:4],len(left[0][view]),len(right[0][view])))
    browser.close()
print(json.dumps(results,ensure_ascii=False,indent=2))
print('Browser parity passed: DOM, computed styles, layout, navigation, theme and forms.')
