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

def run_scenarios(page,student,second,base,calls,errors,browser,failure):
    shots=Path(tempfile.gettempdir())/'bibi-ia-refino';shots.mkdir(exist_ok=True)
    def api(tab,path,method='GET',data=None):
        return tab.evaluate('async args=>{try{return {ok:true,data:await accountApi(args.path,args.method,args.method==="GET"?undefined:args.data)};}catch(error){return {ok:false,error:error.message};}}',{'path':path,'method':method,'data':data})
    page.goto(base+'/app');student.goto(base+'/app');second.goto(base+'/app')
    expect(page.locator('.shelf')).to_have_count(4);expect(page.locator('#bibi-chat')).to_be_hidden()
    expect(page.locator('.bibi-insights')).to_have_count(0)
    assert len(calls)==0
    page.locator('.book').first.click();expect(page.locator('#info-livro')).to_be_visible()
    page.locator('#fechar-detalhes').click();expect(page.locator('#bibi-chat')).to_be_hidden()
    print('PASS: sem chave, quatro prateleiras, painel convencional, nenhum insight ou chamada.',flush=True)
    page.locator('#config-open').click();page.locator('[data-settings-section=inteligencia-artificial]').click()
    form=page.locator('#ai-config-form')
    expect(page.locator('#ai-config-state')).to_contain_text('Configure um provedor')
    assert page.locator('#ai-metadata-form').count()==0
    form.locator('[name=chave]').fill('temporary-secret')
    page.locator('#ai-identity summary').click();form.locator('[name=senha_atual]').fill('senha forte de teste')
    page.locator('#ai-save-key').click();expect(page.locator('#ai-config-state')).to_contain_text('Chave salva')
    expect(form.locator('[name=chave]')).to_have_value('');expect(form.locator('[name=senha_atual]')).to_have_value('')
    expect(page.locator('#bibi-chat')).to_be_hidden();assert not api(page,'/api/ia/config')['data']['ativa']
    page.locator('#ai-models').click();expect(form.locator('[name=modelo] option[value=mock-literature]')).to_have_count(1)
    expect(page.locator('#ai-models')).to_be_enabled()
    form.locator('[name=modelo]').select_option('mock-literature',force=True)
    expect(page.locator('#ai-config-state')).to_contain_text('Teste a conexão')
    assert not api(student,'/api/minha-conta/ia/chat','POST',{'mensagem':'Literatura'})['ok']
    assert len(calls)==0
    page.locator('#ai-test').click();expect(page.locator('#ai-config-state')).to_contain_text('Conexão verificada')
    assert len(calls)==1
    expect(page.locator('#bibi-chat')).to_be_hidden();expect(page.locator('.shelf')).to_have_count(4)
    page.screenshot(path=str(shots/'configurada-desativada.png'),full_page=True)
    form.locator('[name=privacidade_revisada]').check();form.locator('[name=ativa]').check()
    form.get_by_role('button',name='Confirmar configuração',exact=True).click()
    expect(page.locator('#ai-config-state')).to_contain_text('IA ativa')
    expect(page.locator('#bibi-chat')).to_be_visible();expect(page.locator('.shelf')).to_have_count(5)
    expect(student.locator('#bibi-chat')).to_be_visible(timeout=15000)
    expect(student.locator('#prateleira-bibi .book').first).to_have_attribute('data-livro-id','2')
    print('PASS: chave sem ativar, modelos e teste preparatórios, confirmação única, ativação imediata.',flush=True)
    student.locator('#prateleira-bibi .book').first.click()
    expect(student.locator('#bibi-context')).to_contain_text('Livro de autora brasileira')
    student.locator('#bibi-suggestions').get_by_role('button',name='Podemos discutir os personagens?',exact=True).click()
    expect(student.locator('#bibi-status')).to_contain_text('preparando')
    expect(student.locator('.bibi-answer').last).to_contain_text('sem spoilers')
    expect(student.locator('#bibi-status')).to_contain_text('Resposta concluída')
    student.locator('#bibi-input').fill('Compare com outra leitura')
    student.locator('#bibi-send').click();expect(student.locator('#bibi-status')).to_contain_text('Resposta concluída')
    assert len(calls[-1][1])==3
    student.screenshot(path=str(shots/'conversa-contextual.png'),full_page=True)
    expect(second.locator('.bibi-answer')).to_have_count(0)
    student.locator('#bibi-clear').click();expect(student.locator('.bibi-answer')).to_have_count(0)
    expect(student.locator('#bibi-suggestions')).to_be_visible()
    for width in (1366,800,390):
        student.set_viewport_size({'width':width,'height':900})
        for dark in (False,True):
            student.evaluate('(value)=>document.body.classList.toggle("dark-mode",value)',dark)
            student.locator('#bibi-input').fill('Quero conversar sobre literatura')
            student.locator('#bibi-send').click()
            expect(student.locator('#bibi-cancel')).to_be_visible()
            boxes=[student.locator(selector).bounding_box() for selector in ('#bibi-send','#bibi-cancel','#bibi-clear')]
            def overlap(a,b):return a['x']<b['x']+b['width'] and b['x']<a['x']+a['width'] and a['y']<b['y']+b['height'] and b['y']<a['y']+a['height']
            assert all(not overlap(boxes[i],boxes[j]) for i in range(3) for j in range(i+1,3))
            student.locator('#bibi-cancel').click();expect(student.locator('#bibi-status')).to_contain_text('interrompida')
            expect(student.locator('#bibi-clear')).to_be_enabled()
            assert student.evaluate('document.documentElement.scrollWidth<=innerWidth')
            student.screenshot(path=str(shots/f'chat-{width}-{dark}.png'),full_page=True)
            student.locator('#bibi-clear').click()
    student.emulate_media(reduced_motion='reduce')
    print('PASS: sugestões contextuais, streaming, histórico isolado, nova conversa, cancelamento e controles sem sobreposição em três larguras e dois temas.',flush=True)
    expect(page.locator('.bibi-insights')).to_contain_text('sobre os temas desta leitura')
    # Uma preparação ruim não substitui a integração em uso.
    form.locator('[name=provedor]').select_option('groq',force=True)
    form.locator('[name=chave]').fill('another-temporary-secret');page.locator('#ai-save-key').click()
    expect(page.locator('#ai-config-state')).to_contain_text('Chave salva')
    page.locator('#ai-models').click();expect(page.locator('#ai-models')).to_be_enabled();form.locator('[name=modelo]').select_option('mock-literature',force=True)
    expect(page.locator('#ai-config-state')).to_contain_text('Teste a conexão')
    failure['active']=True;page.locator('#ai-test').click()
    expect(page.locator('#ai-feedback')).to_contain_text('Chave inválida')
    assert api(page,'/api/ia/config')['data']['em_uso']['provedor']=='openai'
    expect(student.locator('#bibi-chat')).to_be_visible()
    failure['active']=False;page.locator('#ai-discard').click()
    expect(form.locator('[name=provedor]')).to_have_value('openai')
    # Falha da configuração realmente em uso retira os recursos para todos.
    failure['active']=True;page.locator('#ai-test').click()
    expect(page.locator('#ai-feedback')).to_contain_text('Chave inválida')
    expect(page.locator('#bibi-chat')).to_be_hidden()
    expect(student.locator('#bibi-chat')).to_be_hidden(timeout=15000)
    expect(student.locator('.shelf')).to_have_count(4)
    expect(student.locator('#info-livro')).to_be_visible()
    failure['active']=False;page.locator('#ai-test').click()
    expect(page.locator('#bibi-chat')).to_be_visible()
    form.locator('[name=ativa]').uncheck()
    expect(page.locator('#bibi-chat')).to_be_hidden();expect(page.locator('.shelf')).to_have_count(4)
    count=len(calls);assert not api(student,'/api/minha-conta/ia/chat','POST',{'mensagem':'Literatura'})['ok'];assert count==len(calls)
    print('PASS: troca preserva configuração em uso, chave inválida oculta IA, reteste e desligamento em funcionamento.',flush=True)
    # Metadados no livro: nenhuma configuração de provedor necessária.
    page.locator('#settings-close').click()
    if page.locator('#settings-discard-confirm').is_visible():page.locator('#settings-discard-confirm').click()
    page.locator('.book[data-livro-id="2"]').first.click()
    page.locator('#info-livro').get_by_role('button',name='Editar',exact=True).click()
    expect(page.locator('#modalEditarLivro')).to_be_visible()
    page.locator('#modalEditarLivro .authorship-fields summary').click()
    expect(page.locator('#edit-autoria-genero')).to_have_value('feminina')
    page.locator('#edit-autoria-fonte').fill('Referência bibliográfica revisada')
    page.locator('#btn-salvar-edicao').click();expect(page.locator('#modalEditarLivro')).to_be_hidden()
    assert api(page,'/api/ia/livros/2/autoria')['data']['fonte']=='Referência bibliográfica revisada'
    assert not errors,errors
    browser.close()
    print('PASS: metadados no editor do livro; console limpo. Capturas:',shots,flush=True)
