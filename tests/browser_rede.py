"""Valida a UI contra tests/manual_rede.py (dados descartáveis)."""
import json
from pathlib import Path
import tempfile
from playwright.sync_api import sync_playwright

info=json.loads((Path(tempfile.gettempdir())/'bibi-rede-manual.json').read_text(encoding='utf-8'))
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':1366,'height':768})
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(info['local']+'/acesso')
    page.locator('[name=email]').fill(info['email'])
    page.locator('[name=senha]').fill(info['senha'])
    page.locator('#access-submit').click()
    page.wait_for_url('**/app')
    page.locator('#config-open').click()
    page.wait_for_function("document.getElementById('network-address')?.value.includes('5443')")
    page.locator('[data-settings-section=gestao-config]').click()
    page.locator('#institution-form [name=biblioteca_nome]').fill('Biblioteca sintética de rede')
    page.locator('#institution-form button[type=submit], #institution-form .btn-primary').click()
    page.wait_for_function("document.getElementById('settings-status').textContent.includes('Configurações salvas') || document.getElementById('institution-form').textContent.includes('Configurações salvas')")
    page.locator('#diagnose-network').click()
    page.wait_for_function("document.getElementById('network-diagnostic').textContent.includes('Autoteste')")
    assert 'conexão segura estabelecida' in page.locator('#network-diagnostic').inner_text()
    page.locator('.network-settings details').evaluate('(e)=>e.open=true')
    output=Path(tempfile.gettempdir())/'bibi-rede-review'
    output.mkdir(exist_ok=True)
    for width,height in [(1366,768),(1920,1080),(390,844)]:
        page.set_viewport_size({'width':width,'height':height})
        page.screenshot(path=str(output/f'rede-{width}.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.evaluate("document.body.classList.add('dark-mode')")
    page.screenshot(path=str(output/'rede-390-escuro.png'),full_page=True)
    page.evaluate("document.body.classList.remove('dark-mode')")
    page.locator('#settings-close').click()
    assert not page.locator('#settings-dialog').evaluate('(e)=>e.open')
    page.locator('#config-open').click()
    page.locator('[data-settings-section=gestao-config]').click()
    assert page.locator('#network-address').input_value()==info['enderecos'][0]['url']
    ids=page.evaluate("[...document.querySelectorAll('[id]')].map(e=>e.id)")
    assert len(ids)==len(set(ids))
    assert not errors,errors
    print('PASS: rede, diagnóstico TLS, reabertura, três tamanhos, IDs e console. Capturas:',output)
    browser.close()
