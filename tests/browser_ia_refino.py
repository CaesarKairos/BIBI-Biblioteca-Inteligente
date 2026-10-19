"""Cenários visuais do refinamento; chamados pelo servidor sintético browser_ia."""
from pathlib import Path
import tempfile
from playwright.sync_api import expect

def run_loading_scenario(page,base,browser):
    held=[]
    page.route('**/api/minha-conta/ia/estado',lambda route:held.append(route))
    page.goto(base+'/app')
    expect(page.locator('#bibi-chat')).to_be_hidden()
    expect(page.locator('.shelf')).to_have_count(4)
    expect(page.locator('.bibi-insights')).to_have_count(0)
    assert page.locator('#bibi-chat').get_attribute('hidden') is not None
    assert held,'A resposta de disponibilidade precisa estar pendente nesta verificação.'
    for route in held:route.continue_()
    page.unroute('**/api/minha-conta/ia/estado')
    page.wait_for_function("window.bibiAIState?.estado==='nao_configurada'")
    expect(page.locator('#bibi-chat')).to_be_hidden()
    browser.close()
    print('PASS: disponibilidade pendente e depois não configurada, sem flash do chat ou da quinta prateleira.',flush=True)

def run_scenarios(*args):
    # Compatibility entry point for the current automatic-routing UI.
    from tests.browser_ai_routing import run_scenarios as current
    return current(*args)
