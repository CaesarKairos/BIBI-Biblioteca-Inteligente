"""Integração real Flask/Waitress/Chromium, com banco sintético e sem SMTP."""
from pathlib import Path
import sys
import tempfile
import threading
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from waitress import create_server
from playwright.sync_api import sync_playwright, expect

work=tempfile.TemporaryDirectory(prefix='bibi-browser-')
screens=Path(tempfile.gettempdir())/'bibi-contas-review';screens.mkdir(exist_ok=True)
app=create_app({'DATA_DIR':work.name,'TESTING':True})
server=create_server(app,host='127.0.0.1',port=0,threads=8)
thread=threading.Thread(target=server.run,daemon=True);thread.start()
base=f'http://127.0.0.1:{server.effective_port}'


def api(page,path,method='GET',data=None):
    return page.evaluate('''async ({path,method,data})=>{
        const token=(await (await fetch('/api/acesso/csrf')).json()).csrf;
        const r=await fetch(path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:method==='GET'?undefined:JSON.stringify(data || {})});
        const result=await r.json(); if(!r.ok)throw new Error(JSON.stringify({path,status:r.status,result}));return result;
    }''',{'path':path,'method':method,'data':data})


with patch('smtplib.SMTP',side_effect=AssertionError('SMTP real proibido')),sync_playwright() as p:
    browser=p.chromium.launch()
    admin=browser.new_context(viewport={'width':1366,'height':768},locale='pt-BR')
    admin.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
    page=admin.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(base+'/app');page.wait_for_url('**/configuracao-inicial')
    page.locator('[name=biblioteca]').fill('Biblioteca de teste');page.locator('[name=nome]').fill('Bibliotecária de teste')
    page.locator('[name=email]').fill('admin@example.test');page.locator('[name=senha]').fill('senha forte de teste');page.locator('[name=confirmacao]').fill('senha forte de teste')
    for width,height in [(1366,768),(1920,1080),(390,844),(800,420)]:
        page.set_viewport_size({'width':width,'height':height})
        box=page.locator('.account-card').bounding_box()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        if height>box['height']+48: assert abs(box['y']+box['height']/2-height/2)<3,(width,height,box)
        else: assert box['y']>=0
        page.screenshot(path=str(screens/f'setup-{width}-{height}.png'),full_page=True)
    page.set_viewport_size({'width':1366,'height':768})
    page.get_by_role('link',name='Termos de Uso',exact=True).click()
    assert page.locator('#legal-dialog').is_visible()
    page.keyboard.press('Escape');assert not page.locator('#legal-dialog').is_visible()
    assert page.locator('[name=biblioteca]').input_value()=='Biblioteca de teste'
    assert page.get_by_role('link',name='Termos de Uso',exact=True).evaluate('e=>e===document.activeElement')
    page.locator('[name=aceite]').check();page.locator('#access-submit').click();page.wait_for_url('**/boas-vindas');page.wait_for_load_state('networkidle')
    assert page.locator('#offline-code').count()==0
    page.locator('#suggested-avatar').click();page.wait_for_url('**/app');page.wait_for_load_state('networkidle')
    books=[]
    for name,qty,category in [('Livro de teste',2,'Ficção'),('Memórias com um título longo para conferir a tabela e a busca',1,'Poesia'),('Quadrinhos',1,'Comics & Graphic Novels')]:
        books.append(api(page,'/api/livros','POST',{'manual':True,'titulo':name,'autor':'Autora de teste','quantidade':qty,'categoria':category,'numero_paginas':240}))
    reader=api(page,'/api/leitores','POST',{'nome':'João da Silva','tipo':'estudante','email':'joao@example.test','sala':'8 A'})['id']
    api(page,'/api/emprestimos','POST',{'leitor_id':reader,'livros':[{'id':books[1]['id']}]})
    invite=api(page,f'/api/contas/leitores/{reader}/codigo','POST',{})['codigo']
    page.goto(base+'/app');page.wait_for_load_state('networkidle')
    assert page.locator('.shelf').count()==5
    page.locator('#busca-acervo').fill('autora');page.wait_for_timeout(350);page.wait_for_load_state('networkidle')
    assert page.locator('.book').count()>=3
    assert page.locator('.book.unavailable').count()>=1
    page.locator('.book.unavailable').first.click();assert page.locator('#btn-emprestar').is_enabled()
    page.locator('#catalog-clear').click();page.wait_for_load_state('networkidle')
    page.locator('.book').first.click();assert page.locator('#info-livro').is_visible()
    page.locator('#fechar-detalhes').click();assert not page.locator('#info-livro').is_visible()
    page.locator('.book').last.click();assert page.locator('#info-livro').is_visible()
    page.locator('#m-emp').click();page.wait_for_load_state('networkidle');page.locator('#busca-emprestimos').fill('JOAO')
    page.wait_for_function("document.querySelectorAll('.tabela-emprestimos tbody tr').length === 1")
    assert page.locator('.tabela-emprestimos tbody td').evaluate_all('cells=>cells.every(c=>Math.abs(c.getBoundingClientRect().height-cells[0].getBoundingClientRect().height)<1)')
    page.goto(base+'/leitores/contas?leitor='+str(reader));page.wait_for_load_state('networkidle');assert page.locator('#invite-state').inner_text()
    page.goto(base+'/configuracoes');page.wait_for_load_state('networkidle');expect(page.locator('#health-result')).not_to_be_empty()
    page.screenshot(path=str(screens/'gestao-desktop.png'))
    page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(screens/'gestao-mobile.png'));page.set_viewport_size({'width':1366,'height':768})
    page.goto(base+'/perfil');page.wait_for_load_state('networkidle');assert page.locator('#saved-avatar').get_attribute('src').startswith('data:')
    saved=page.locator('#saved-avatar').get_attribute('src');page.locator('#edit-avatar').click();page.locator('#random-avatar').click();page.wait_for_load_state('networkidle');page.locator('#cancel-avatar').click();assert page.locator('#saved-avatar').get_attribute('src')==saved
    guest=browser.new_context(viewport={'width':390,'height':844},locale='pt-BR');guest.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
    reader_page=guest.new_page();reader_errors=[];reader_page.on('pageerror',lambda error:reader_errors.append(str(error)))
    reader_page.goto(base+'/acesso');reader_page.get_by_role('button',name='Ativar convite',exact=True).click()
    reader_page.locator('[name=email]').fill('joao@example.test');reader_page.locator('[name=codigo]').fill(invite);reader_page.locator('[name=senha]').fill('senha forte do leitor');reader_page.locator('[name=confirmacao]').fill('senha forte do leitor');reader_page.locator('#access-submit').click()
    reader_page.wait_for_url('**/boas-vindas');reader_page.wait_for_load_state('networkidle');reader_page.locator('#suggested-avatar').click();reader_page.wait_for_url('**/app');reader_page.wait_for_load_state('networkidle')
    assert reader_page.locator('#m-dash').count()==0
    assert not reader_page.locator('#m-age').is_visible()
    assert reader_page.evaluate("fetch('/api/leitores').then(r=>r.status)")==403
    reader_page.locator('.book').first.click();reader_page.get_by_role('button',name='Quero ler',exact=True).click();reader_page.wait_for_load_state('networkidle')
    reader_page.goto(base+'/perfil');reader_page.wait_for_load_state('networkidle');reader_page.locator('#config-open').click();expect(reader_page.locator('#email-state')).to_contain_text('não verificado');reader_page.keyboard.press('Escape');assert reader_page.locator('#profile-wishes .profile-row').count()==1
    reader_page.locator('#favorite-book').select_option(str(books[0]['id']),force=True);reader_page.locator('#favorite-form button').last.click();reader_page.wait_for_load_state('networkidle');expect(reader_page.locator('#profile-favorites article')).to_have_count(1)
    reader_page.locator('#edit-avatar').click();reader_page.wait_for_load_state('networkidle')
    reader_page.locator('[data-avatar-field=eyesVariant][data-avatar-value=variant02]').click();reader_page.wait_for_load_state('networkidle')
    reader_page.locator('#save-avatar').click();reader_page.wait_for_load_state('networkidle');reader_page.reload();reader_page.wait_for_load_state('networkidle')
    reader_page.locator('#edit-avatar').click();reader_page.wait_for_load_state('networkidle');expect(reader_page.locator('[data-avatar-field=eyesVariant][data-avatar-value=variant02]')).to_have_attribute('aria-pressed','true')
    reader_page.screenshot(path=str(screens/'perfil-avatar.png'));reader_page.locator('#cancel-avatar').click()
    for role,tab in [('admin',page),('leitor',reader_page)]:
        for width,height in [(1366,768),(1920,1080),(800,900),(390,844)]:
            tab.set_viewport_size({'width':width,'height':height});tab.goto(base+'/app');tab.wait_for_load_state('networkidle')
            for dark in [False,True]:
                tab.evaluate('(dark)=>toggleTheme(dark)',dark);tab.wait_for_timeout(250)
                assert tab.evaluate('document.documentElement.scrollWidth<=innerWidth'),(role,width,dark)
                assert tab.locator('.shelf').count()==5
                sizes=tab.locator('.book').evaluate_all('es=>es.map(e=>[e.offsetWidth,e.offsetHeight,getComputedStyle(e).backgroundSize])')
                assert all(size==[80,110,'cover'] for size in sizes),sizes
                tab.screenshot(path=str(screens/f'{role}-{width}-{"dark" if dark else "light"}.png'))
            if width>700:
                handle=tab.locator('#resize-sidebar');box=handle.bounding_box();tab.mouse.move(box['x']+box['width']/2,box['y']+30);tab.mouse.down();tab.mouse.move(box['x']+35,box['y']+30);tab.mouse.up()
                assert tab.locator('.content-area').bounding_box()['width']>=317
                assert tab.evaluate('document.documentElement.scrollWidth<=innerWidth')
    for role,tab in [('admin',page),('leitor',reader_page)]:
        for route in ['/perfil','/configuracoes']:
            for width,height in [(1366,768),(1920,1080),(390,844),(800,420)]:
                tab.set_viewport_size({'width':width,'height':height});tab.goto(base+route);tab.wait_for_load_state('networkidle')
                for dark in [False,True]:
                    tab.evaluate('(dark)=>document.body.classList.toggle("dark-mode",dark)',dark)
                    assert tab.evaluate('document.documentElement.scrollWidth<=innerWidth'),(role,route,width)
                    assert tab.locator('.right-bar').inner_text().strip()==''
                    tab.screenshot(path=str(screens/f'{role}-{route[1:]}-{width}-{dark}.png'),full_page=True)
                if role=='leitor':assert tab.locator('#smtp-form').count()==0
    page.goto(base+'/app');page.wait_for_load_state('networkidle')
    category=page.locator('#catalog-category + .custom-select button')
    category.focus();page.keyboard.press('ArrowDown');page.keyboard.press('Space');assert category.get_attribute('aria-expanded')=='true'
    page.keyboard.press('Escape');assert category.get_attribute('aria-expanded')=='false'
    assert page.locator('#catalog-category').input_value()!=''
    page.emulate_media(reduced_motion='reduce');page.reload();page.wait_for_load_state('networkidle');assert page.locator('.cat-waving').evaluate('e=>e.paused')
    assert not errors,errors
    assert not reader_errors,reader_errors
    guest.close();admin.close();browser.close()
server.close();thread.join(timeout=3)
work.cleanup()
print('Browser passed: setup, real login/invite, admin/reader, privacy, profile/avatar cancel, search, 5 shelves, details, fixed covers, 4 viewports, light/dark and resizing.')
print('Screenshots:',screens)
