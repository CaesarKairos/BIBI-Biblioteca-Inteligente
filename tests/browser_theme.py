"""Exercise actual custom-select clicks, keyboard and preference handlers offline."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page()
    state={'tema':'claro','writes':[],'fail':False}
    def respond(route):
        if route.request.url.endswith('/api/minha-conta/preferencias'):
            if route.request.method=='PUT':
                if state['fail']:
                    route.fulfill(status=503,content_type='application/json',body=json.dumps({'erro':'Falha simulada.'}));return
                state['tema']=route.request.post_data_json['tema'];state['writes'].append(state['tema'])
            route.fulfill(content_type='application/json',body=json.dumps({'tema':state['tema']}))
        else:
            route.fulfill(content_type='text/html',body='''<meta name="csrf-token" content="synthetic"><body data-page="perfil">
            <label>Tema<select id="settings-theme"><option value="claro">Claro</option><option value="escuro">Escuro</option></select></label>
            <button id="theme-toggle-btn"></button><p id="settings-status"></p></body>''')
    page.route('http://bibi.test/**',respond)
    page.goto('http://bibi.test/')
    page.add_style_tag(content='.select-items{display:none}.select-selected,.select-items div{padding:12px}')
    for script in ['ui.js','conta_comum.js','preferencias.js']:
        page.add_script_tag(path=str(ROOT/'static/js'/script))
    page.evaluate('enhanceNativeSelects()')
    control=page.locator('#settings-theme + .custom-select button')
    for label,value in [('Escuro','escuro'),('Claro','claro')]:
        control.click();page.get_by_role('option',name=label,exact=True).click()
        expect(control).to_be_enabled()
        expect(page.locator('#settings-theme')).to_have_value(value)
        page.wait_for_function('(dark)=>document.body.classList.contains("dark-mode")===dark',arg=value=='escuro')
        assert state['tema']==value
        assert page.evaluate("JSON.parse(localStorage.getItem('bibiConfig')).darkMode")== (value=='escuro')
    for key,value in [('ArrowDown','escuro'),('ArrowUp','claro')]:
        control.focus();page.keyboard.press(key)
        page.wait_for_function('(dark)=>document.body.classList.contains("dark-mode")===dark',arg=value=='escuro')
        expect(control).to_be_enabled()
        assert state['tema']==value
    assert state['writes']==['escuro','claro','escuro','claro']
    state['fail']=True
    control.click();page.get_by_role('option',name='Escuro',exact=True).click()
    expect(page.locator('#settings-status')).to_have_text('Falha simulada.')
    expect(page.locator('#settings-theme')).to_have_value('claro')
    assert not page.evaluate('document.body.classList.contains("dark-mode")')
    browser.close()
print('PASS: theme changes by actual mouse clicks and keyboard, persists, and rolls back on failure.')
