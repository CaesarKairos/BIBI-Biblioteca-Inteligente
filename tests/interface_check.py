"""Real Chromium review with synthetic SQLite, local assets and SMTP disabled."""
from pathlib import Path
import sys
import tempfile
import threading
import subprocess
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from waitress import create_server
from playwright.sync_api import sync_playwright, expect
from flask import render_template_string, Response

ROOT=Path(__file__).resolve().parents[1]
screens=ROOT/'docs'/'capturas-interface'
screens.mkdir(exist_ok=True)
work=tempfile.TemporaryDirectory(prefix='bibi-interface-')
app=create_app({'DATA_DIR':work.name,'TESTING':True})
old_html=subprocess.check_output(['git','show','d262282:templates/app.html'],cwd=ROOT).decode('utf-8')
old_js=subprocess.check_output(['git','show','d262282:static/js/configuracoes.js'],cwd=ROOT).decode('utf-8')
old_css=subprocess.check_output(['git','show','d262282:static/css/app.css'],cwd=ROOT).decode('utf-8')
old_css=old_css.replace(old_css.splitlines()[0],Path(ROOT/'static/css/app.css').read_text('utf-8').splitlines()[0])
old_panel=old_html[old_html.index('<div id="modalConfiguracoes"'):old_html.index('<div id="modalConfigAgenda"')]
old_panel=old_panel[:old_panel.rfind('{% endif %}')] if '{% endif %}' in old_panel else old_panel

@app.get('/referencia-interface')
def reference():
    return render_template_string('<html lang="pt-BR"><meta charset="utf-8"><link rel="stylesheet" href="/referencia-estilos"><body>'+old_panel+'''<script>const CONFIG_STORAGE_KEY='bibiConfig';const isAdminGlobal=true;const apiFetch=(path,opts)=>{if(opts?.method&&opts.method!=='GET')throw Error('Reference is read-only');return fetch(path);};function openModal(id){document.getElementById(id).style.display='flex';}</script><script src='/referencia-script'></script></body></html>''',admin=True)

@app.get('/referencia-estilos')
def reference_css():
    return Response(old_css,mimetype='text/css')

@app.get('/referencia-script')
def reference_js():
    return Response(old_js,mimetype='application/javascript')

server=create_server(app,host='127.0.0.1',port=0,threads=8)
threading.Thread(target=server.run,daemon=True).start()
base=f'http://127.0.0.1:{server.effective_port}'

def api(page,path,method='GET',data=None,expected=200):
    result=page.evaluate('''async ({path,method,data})=>{
      const token=(await (await fetch('/api/acesso/csrf')).json()).csrf;
      const response=await fetch(path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:method==='GET'?undefined:JSON.stringify(data||{})});
      return {status:response.status,data:await response.json()};
    }''',dict(path=path,method=method,data=data))
    assert (200<=result['status']<300 if expected==200 else result['status']==expected),result
    return result['data']

def settle(page):
    page.wait_for_load_state('networkidle')

def open_settings(page,key='minha-conta'):
    page.locator('#config-open').click()
    expect(page.locator('[data-settings-section="minha-conta"]')).to_be_visible(timeout=30000)
    page.wait_for_function("document.querySelector('#settings-status').textContent!== 'Carregando…'")
    page.locator(f'[data-settings-section="{key}"]').click()

def check_ids(page):
    assert page.evaluate('''()=>{const ids=[...document.querySelectorAll('[id]')].map(e=>e.id);return ids.length===new Set(ids).size;}''')

def console_check(message, errors):
    if message.type=='error' and not any(f'status of {code}' in message.text for code in (401,403,503)):
        errors.append(message.text)

with patch('smtplib.SMTP',side_effect=AssertionError('No real SMTP')),patch('smtplib.SMTP_SSL',side_effect=AssertionError('No real SMTP')),sync_playwright() as p:
    browser=p.chromium.launch()
    admin=browser.new_context(viewport={'width':1366,'height':768},locale='pt-BR')
    admin.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
    page=admin.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m:console_check(m,errors))
    print('Setup and onboarding',flush=True)
    page.goto(base+'/app')
    page.locator('[name=biblioteca]').fill('Biblioteca de teste');page.locator('[name=nome]').fill('Bibliotecária')
    page.locator('[name=email]').fill('admin@example.test');page.locator('[name=senha]').fill('senha forte de teste');page.locator('[name=confirmacao]').fill('senha forte de teste');page.locator('[name=aceite]').check();page.locator('#access-submit').click()
    page.wait_for_url('**/boas-vindas');settle(page)
    expect(page.locator('#avatar-editor')).to_be_visible();expect(page.locator('.profile-hero')).to_be_hidden()
    expect(page.locator('.avatar-choice[aria-busy=true]')).to_have_count(0,timeout=60000)
    page.screenshot(path=str(screens/'avatar-primeiro-acesso.png'))
    page.locator('#suggested-avatar').click();page.wait_for_url('**/app');settle(page)
    open_settings(page,'gestao-convites');expect(page.locator('#invite-state')).to_have_text('Nenhum leitor cadastrado.');page.keyboard.press('Escape')
    book=api(page,'/api/livros','POST',{'manual':True,'titulo':'Memórias da biblioteca','autor':'Autora de teste','quantidade':3,'categoria':'Ficção'})
    reader=api(page,'/api/leitores','POST',{'nome':'Ana Silva','tipo':'estudante','email':'ana@example.test','sala':'8 A'})['id']
    api(page,'/api/emprestimos','POST',{'leitor_id':reader,'livros':[{'id':book['id']}]})
    invite=api(page,f'/api/contas/leitores/{reader}/codigo','POST',{})['codigo']
    page.reload();settle(page);page.locator('#busca-acervo').fill('Memórias');settle(page)
    page.locator('.book').first.click();expect(page.locator('#info-livro')).to_be_visible()
    initial=page.evaluate("({scroll:document.querySelector('.content-area').scrollTop,selected:document.querySelector('#info-livro').textContent})")
    open_settings(page,'gestao-config');check_ids(page)
    page.locator('[name=biblioteca_nome]').fill('Valor para descartar')
    page.keyboard.press('Escape');expect(page.locator('#settings-discard')).to_be_visible()
    page.locator('#settings-continue').click();expect(page.locator('#settings-dialog')).to_be_visible()
    page.locator('#settings-close').click();page.locator('#settings-discard-confirm').click()
    expect(page.locator('#busca-acervo')).to_have_value('Memórias');expect(page.locator('#info-livro')).to_be_visible()
    assert page.evaluate("document.querySelector('.content-area').scrollTop")==initial['scroll']
    assert page.locator('#config-open').evaluate('e=>e===document.activeElement')
    open_settings(page,'gestao-config');expect(page.locator('[name=biblioteca_nome]')).to_have_value('Biblioteca de teste')
    page.locator('[name=biblioteca_nome]').fill('Biblioteca refinada');page.locator('#institution-form .btn-primary').click();expect(page.locator('#settings-status')).to_have_text('Configurações salvas.');expect(page.locator('#settings-close')).to_be_enabled()
    page.locator('#settings-close').click();expect(page.locator('#settings-dialog')).to_be_hidden()
    open_settings(page,'aparencia')
    pending_preferences=[]
    page.route('**/api/minha-conta/preferencias',lambda route:pending_preferences.append(route) if route.request.method=='PUT' else route.continue_())
    page.locator('#settings-theme').select_option('escuro',force=True)
    expect(page.locator('#settings-close')).to_be_disabled()
    expect(page.locator('#settings-theme + .custom-select button')).to_be_disabled()
    page.keyboard.press('Escape');expect(page.locator('#settings-dialog')).to_be_visible()
    assert len(pending_preferences)==1
    pending_preferences.pop().continue_()
    expect(page.locator('#settings-close')).to_be_enabled();page.keyboard.press('Escape')
    page.unroute('**/api/minha-conta/preferencias')
    fragments=[]
    page.on('request',lambda request:fragments.append(request.url) if 'fragmento=1' in request.url else None)
    print('Settings save, discard and navigation',flush=True)
    for tab in ['dash','acervo','emp','age','lei']:
        page.locator('#m-'+tab).click();settle(page);open_settings(page);page.keyboard.press('Escape');expect(page.locator('#settings-dialog')).to_be_hidden()
    assert not fragments,'Reopening settings should reuse the loaded fragment'
    page.goto(base+f'/leitores/contas?leitor={reader}');settle(page)
    expect(page.locator('#invite-reader')).to_have_value(str(reader));expect(page.locator('#invite-form')).to_be_visible();check_ids(page)
    page.locator('[data-settings-section=circulacao]').click();expect(page.locator('#occurrence-form')).to_be_visible()
    page.locator('#occurrence-form [name=observacao]').fill('Observação sintética');page.locator('#occurrence-form .btn-primary').click();settle(page)
    page.locator('[data-settings-section=dados]').click()
    page.locator('#csv-file').set_input_files({'name':'livros.csv','mimeType':'text/csv','buffer':b'isbn;titulo;autor;quantidade\n;Livro importado;Autor;1\n'})
    page.locator('#csv-form .btn-primary').click();settle(page);expect(page.locator('#csv-preview')).not_to_be_empty()
    # Preview is not a write. Cancel the pending file selection before closing.
    page.locator('#settings-close').click();expect(page.locator('#settings-discard')).to_be_visible();page.locator('#settings-continue').click()
    expect(page.locator('#csv-confirm')).to_be_enabled();page.once('dialog',lambda d:d.accept());page.locator('#csv-confirm').click();expect(page.locator('#settings-status')).to_contain_text('registros importados');expect(page.locator('#settings-close')).to_be_enabled();page.locator('#settings-close').click();expect(page.locator('#settings-dialog')).to_be_hidden()
    open_settings(page,'dados');page.locator('#csv-kind').select_option('leitores',force=True)
    page.locator('#csv-file').set_input_files({'name':'leitores.csv','mimeType':'text/csv','buffer':b'nome;tipo;email;sala\nBruno;estudante;;7 A\n'})
    page.locator('#csv-form .btn-primary').click();expect(page.locator('#csv-confirm')).to_be_enabled();page.once('dialog',lambda d:d.accept());page.locator('#csv-confirm').click();expect(page.locator('#settings-status')).to_contain_text('registros importados');expect(page.locator('#settings-close')).to_be_enabled();page.locator('#settings-close').click();expect(page.locator('#settings-dialog')).to_be_hidden()
    print('Import and circulation; responsive screenshots',flush=True)
    for width,height in [(1366,768),(1920,1080),(390,844)]:
        page.set_viewport_size(dict(width=width,height=height))
        for dark in [False,True]:
            page.evaluate('(dark)=>document.body.classList.toggle("dark-mode",dark)',dark)
            open_settings(page,'cadastro');settle(page)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            box=page.locator('#settings-dialog').bounding_box();assert box['x']>=0 and box['y']>=0 and box['height']<=height
            page.keyboard.press('Tab');assert page.evaluate("!!document.activeElement.closest('#settings-dialog')")
            page.screenshot(path=str(screens/(f'configuracoes-{width}-'+('escuro' if dark else 'claro')+'.png')))
            page.keyboard.press('Escape')
    print('Profile and avatar edit',flush=True)
    page.set_viewport_size(dict(width=1366,height=768));page.goto(base+'/perfil');settle(page)
    open_settings(page,'seguranca');expect(page.locator('.health-summary')).to_be_visible();page.screenshot(path=str(screens/'saude-instalacao.png'));page.keyboard.press('Escape')
    before_theme=page.evaluate("document.body.classList.contains('dark-mode')")
    page.locator('#theme-toggle-btn').focus();page.keyboard.press('Enter')
    assert page.evaluate("document.body.classList.contains('dark-mode')")!=before_theme
    open_settings(page);expect(page.locator('#password-form')).to_be_visible();page.keyboard.press('Escape')
    saved=api(page,'/api/minha-conta/avatar')['config'];page.locator('#edit-avatar').click();settle(page)
    page.locator('#random-avatar').click();page.locator('#cancel-avatar').click();assert api(page,'/api/minha-conta/avatar')['config']==saved
    page.locator('#edit-avatar').click();settle(page);page.locator('[data-avatar-field=eyesVariant][data-avatar-value=variant02]').click();settle(page);page.locator('#save-avatar').click();settle(page)
    assert api(page,'/api/minha-conta/avatar')['config']['opcoes']['eyesVariant']=='variant02'
    page.goto(base+'/referencia-interface');settle(page)
    page.evaluate('abrirModalConfiguracoes()');settle(page)
    page.screenshot(path=str(screens/'referencia-d262282.png'))
    print('Login, recovery and reader role',flush=True)
    guest=browser.new_context(viewport=dict(width=390,height=844),locale='pt-BR');guest.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
    rp=guest.new_page();rp.on('pageerror',lambda e:errors.append(str(e)));rp.goto(base+'/acesso');settle(rp)
    rp.on('console',lambda m:console_check(m,errors))
    rp.screenshot(path=str(screens/'login-mobile.png'))
    rp.get_by_role('button',name='Esqueci minha senha',exact=True).click();expect(rp.locator('#password-label')).to_be_hidden();rp.locator('[name=email]').fill('semconta@example.test');rp.locator('#access-submit').click();settle(rp);expect(rp.locator('#code-label')).to_be_visible()
    rp.locator('#back-login').click();rp.get_by_role('button',name='Esqueci minha senha',exact=True).click();rp.locator('#have-code').click();rp.screenshot(path=str(screens/'recuperacao-mobile.png'));rp.locator('#back-login').click()
    rp.get_by_role('button',name='Ativar convite',exact=True).click();rp.locator('[name=email]').fill('ana@example.test');rp.locator('[name=codigo]').fill(invite);rp.locator('[name=senha]').fill('senha forte do leitor');rp.locator('[name=confirmacao]').fill('senha forte do leitor');rp.locator('#access-submit').click();rp.wait_for_url('**/boas-vindas');settle(rp)
    rp.locator('#suggested-avatar').click();rp.wait_for_url('**/app');settle(rp)
    for path in ['/api/gestao/saude','/api/contas','/api/gestao/renovacoes']:
        api(rp,path,expected=403)
    for path in ['/app','/perfil']:
        rp.goto(base+path);settle(rp);open_settings(rp);check_ids(rp);expect(rp.locator('#smtp-form')).to_have_count(0);expect(rp.locator('#password-form')).to_be_visible()
        rp.screenshot(path=str(screens/'leitor-configuracoes-mobile.png'));rp.keyboard.press('Escape')
    expect(rp.locator('#profile-loans .profile-row')).to_have_count(1)
    for width,height in [(1366,768),(1920,1080),(390,844)]:
        rp.set_viewport_size(dict(width=width,height=height))
        for dark in (False,True):
            rp.evaluate('(dark)=>document.body.classList.toggle("dark-mode",dark)',dark)
            open_settings(rp,'aparencia');check_ids(rp)
            assert rp.evaluate('document.documentElement.scrollWidth<=innerWidth')
            rp.locator('#settings-close').focus();rp.keyboard.press('Shift+Tab');assert rp.evaluate("!!document.activeElement.closest('#settings-dialog')")
            if width==1920 and dark:rp.screenshot(path=str(screens/'leitor-configuracoes-desktop-escuro.png'))
            rp.keyboard.press('Escape')
    rp.evaluate("document.body.classList.remove('dark-mode')")
    rp.locator('#edit-avatar').click();expect(rp.locator('.avatar-choice[aria-busy=true]')).to_have_count(0,timeout=60000);expect(rp.locator('#avatar-status')).to_be_empty();rp.screenshot(path=str(screens/'avatar-mobile.png'));rp.locator('#cancel-avatar').click()
    rp.route('**/api/acesso/sair',lambda route:route.fulfill(status=503,content_type='application/json',body='{"erro":"Falha simulada ao sair."}'))
    rp.locator('#account-logout').click();expect(rp.locator('#account-status')).to_have_text('Falha simulada ao sair.');assert rp.url.endswith('/perfil');api(rp,'/api/minha-conta')
    rp.unroute('**/api/acesso/sair')
    rp.locator('#account-logout').click();rp.wait_for_url('**/acesso');api(rp,'/api/minha-conta',expected=401)
    page.goto(base+'/app?config=gestao-convites');expect(page.locator('#invite-reader')).to_have_value(str(reader));expect(page.locator('#settings-close')).to_be_enabled()
    page.locator('#invite-form [name=finalidade]').select_option('recuperacao',force=True);page.locator('#invite-form .btn-primary').click();expect(page.locator('#invite-code')).not_to_be_empty();code=page.locator('#invite-code').inner_text();expect(page.locator('#settings-close')).to_be_enabled();page.keyboard.press('Escape')
    rp.get_by_role('button',name='Esqueci minha senha',exact=True).click();rp.locator('#have-code').click();rp.locator('[name=email]').fill('ana@example.test');rp.locator('[name=codigo]').fill(code);rp.locator('[name=senha]').fill('nova senha do leitor');rp.locator('[name=confirmacao]').fill('nova senha do leitor');rp.locator('#access-submit').click();expect(rp.locator('#access-status')).to_contain_text('Senha definida')
    rp.locator('#back-login').click();rp.locator('[name=email]').fill('ana@example.test');rp.locator('[name=senha]').fill('nova senha do leitor');rp.locator('#access-submit').click();rp.wait_for_url('**/app');settle(rp)
    # Backup, validation and actual restore use only this temporary installation.
    open_settings(page,'dados')
    with page.expect_download() as download_info:page.locator('#download-backup').click()
    backup=Path(work.name)/'synthetic-backup.zip';download_info.value.save_as(str(backup))
    expect(page.locator('#settings-close')).to_be_enabled();page.locator('#restore-password').fill('senha forte de teste');page.locator('#restore-file').set_input_files(str(backup));page.locator('#restore-form button').first.click();expect(page.locator('#settings-status')).to_contain_text('Formato e hashes válidos')
    page.locator('#restore-confirm').check();page.locator('#restore-run').click();page.wait_for_url('**/acesso');settle(page)
    # Exercise the desktop capability through HTTP; no claim of native window validation.
    from services.recuperacao_local import RecuperacaoDesktop
    manager=RecuperacaoDesktop(app.extensions['secrets']);app.extensions['desktop_recovery']=manager;token=manager.abrir()
    page.goto(base+'/recuperacao-local#'+token);expect(page.locator('#access-submit')).to_be_enabled();assert '#' not in page.url
    page.locator('[name=email]').fill('admin@example.test');page.locator('[name=senha]').fill('nova senha bibliotecaria');page.locator('[name=confirmacao]').fill('nova senha bibliotecaria');page.locator('#access-submit').click();expect(page.locator('#access-status')).to_contain_text('Senha redefinida')
    assert not errors,errors
    browser.close()
server.close();work.cleanup()
print('Interface checks passed; screenshots:',screens)
