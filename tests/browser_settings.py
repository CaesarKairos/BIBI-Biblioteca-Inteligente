"""Chromium real com sessão de fixture e banco descartável; sem SMTP ou IA externa."""
from pathlib import Path
import sys
import threading
import tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests.support import AppTest
from waitress import create_server
from playwright.sync_api import sync_playwright,expect


fixture=AppTest();fixture.setUp()
server=create_server(fixture.app,host='127.0.0.1',port=0,threads=8)
threading.Thread(target=server.run,daemon=True).start()
base=f'http://127.0.0.1:{server.effective_port}'
screens=Path(tempfile.gettempdir())/'bibi-settings-audit';screens.mkdir(exist_ok=True)
try:
    book=fixture.book(4)
    with patch('smtplib.SMTP',side_effect=AssertionError('SMTP externo proibido')),sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(viewport={'width':1366,'height':900})
        context.add_cookies([dict(name='session',value=fixture.client.get_cookie('session').value,url=base)])
        context.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
        if '--cache-only' in sys.argv:
            context.add_init_script("localStorage.setItem('bibiConfig',JSON.stringify({campoNumeroUsuario:true,mostrarColunaAula:false}))")
        page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(base+'/app');expect(page.locator('.book')).to_have_count(1)
        page.wait_for_function('typeof tipoLeitorModalSelect!=="undefined" && tipoLeitorModalSelect')

        def settings(section):
            page.locator('#config-open').click()
            page.wait_for_function("document.getElementById('settings-content').getAttribute('aria-busy')==='false'")
            page.locator(f'[data-settings-section="{section}"]').click()
            expect(page.locator(f'#{section}')).to_be_visible()
            expect(page.locator('#settings-close')).to_be_enabled()

        def switch(key,value):
            control=page.locator(f'[data-setting="{key}"]')
            with page.expect_response(lambda r:'/api/config/' in r.url and r.request.method in ('PUT','POST')) as response:
                if control.is_checked()!=value:
                    control.press('Space')
                else:
                    raise AssertionError(f'O cenário precisa alterar {key}')
            assert response.value.ok,response.value.text()
            expect(control).to_be_enabled()
            expect(control).to_be_checked(checked=value)

        def close_settings():
            page.locator('#settings-close').click()
            expect(page.locator('#settings-dialog')).not_to_be_visible()

        if '--cache-only' in sys.argv:
            page.evaluate("openModal('modalLeitor')")
            expect(page.locator('#leitor-telefone')).to_be_hidden()
            page.evaluate("closeModal('modalLeitor'); tab('age')")
            expect(page.locator('#tabela-agenda th')).to_have_count(2)
            settings('cadastro')
            expect(page.locator('[data-setting=campoNumeroUsuario]')).not_to_be_checked()
            expect(page.locator('[data-setting=mostrarColunaAula]')).to_be_checked()
            close_settings()
            assert not errors,errors
            browser.close()
            print('PASS: valores do servidor e padrões substituem o cache antigo do navegador.',flush=True)
            raise SystemExit(0)

        if '--institution-only' in sys.argv:
            # Hold the last preparatory request to exercise the loading race.
            held=[]
            def hold_health(route):
                held.append(route)
                page.evaluate('window.settingsHealthHeld=true')
            page.route('**/api/gestao/saude',hold_health)
            page.locator('#config-open').click()
            page.wait_for_function('window.settingsHealthHeld===true')
            assert page.locator('#settings-content').evaluate('e=>e.inert')
            expect(page.locator('#settings-content')).to_have_attribute('aria-busy','true')
            for route in held:route.continue_()
            page.unroute('**/api/gestao/saude',hold_health)
            page.wait_for_function("document.getElementById('settings-content').getAttribute('aria-busy')==='false'")
            close_settings()
            settings('gestao-config')
            for name,value in [('biblioteca_nome','Biblioteca da auditoria'),('termos_uso','Termos atualizados da escola.'),('aviso_privacidade','Aviso atualizado da escola.')]:
                page.locator(f'#institution-form [name={name}]').fill(value)
            page.locator('#institution-form').get_by_role('button',name='Salvar instituição').click()
            expect(page.locator('#settings-status')).to_contain_text('Configurações salvas')
            page.locator('[data-settings-section=institucional]').click()
            expect(page.locator('#institucional .institution-text').nth(0)).to_have_text('Termos atualizados da escola.')
            expect(page.locator('#institucional .institution-text').nth(1)).to_have_text('Aviso atualizado da escola.')
            close_settings()
            page.goto(base+'/instituicao')
            expect(page.locator('body')).to_contain_text('Termos atualizados da escola.')
            expect(page.locator('body')).to_contain_text('Aviso atualizado da escola.')
            assert not errors,errors
            browser.close()
            print('PASS: textos institucionais atualizados imediatamente e persistidos na página pública.',flush=True)
            raise SystemExit(0)

        settings('cadastro');switch('campoNumeroUsuario',True);close_settings()
        page.evaluate("openModal('modalLeitor')")
        expect(page.locator('#leitor-telefone')).to_be_visible()
        assert page.locator('#leitor-telefone').evaluate('e=>e.required')
        page.evaluate("closeModal('modalLeitor')")
        settings('cadastro');switch('campoNumeroUsuario',False)
        for key in ['campoDescricaoVisivel','campoAnoVisivel','campoTemasVisivel','campoCategoriaVisivel']:
            switch(key,False)
        close_settings()
        page.evaluate("openModal('modalLeitor')")
        expect(page.locator('#leitor-telefone')).to_be_hidden()
        assert not page.locator('#leitor-telefone').evaluate('e=>e.required')
        page.evaluate("closeModal('modalLeitor'); openModal('modalManualLivro')")
        for field in ['ano','descricao','temas','categoria']:
            expect(page.locator(f'#modalManualLivro .campo-{field}')).to_be_hidden()
        expect(page.locator('#manual-localizacao')).to_be_visible()
        page.evaluate("closeModal('modalManualLivro')")
        print('PASS: telefone nos dois estados; quatro campos do cadastro ocultos; localização opcional visível.',flush=True)

        settings('cadastro')
        for key in ['campoDescricaoVisivel','campoAnoVisivel','campoTemasVisivel','campoCategoriaVisivel']:
            switch(key,True)
        switch('obrigar_localizacao_livro',True);close_settings()
        page.wait_for_function("document.getElementById('manual-localizacao').required")
        page.locator('.book').first.click()
        # Existing book-detail action opens the real edit workflow.
        page.locator('#info-livro').get_by_role('button',name='Editar',exact=True).click()
        expect(page.locator('#modalEditarLivro')).to_be_visible()
        for field in ['ano','descricao','temas','categoria']:
            expect(page.locator(f'#modalEditarLivro .campo-{field}')).to_be_visible()
        assert page.locator('#edit-localizacao').evaluate('e=>e.required')
        page.evaluate("closeModal('modalEditarLivro')")
        settings('cadastro');switch('bloquearExcluirLivro',True);close_settings()
        expect(page.locator('#btn-excluir-livro')).to_be_hidden()
        settings('cadastro');switch('bloquearExcluirLivro',False);switch('obrigar_localizacao_livro',False);close_settings()
        expect(page.locator('#btn-excluir-livro')).to_be_visible()
        page.wait_for_function("!document.getElementById('edit-localizacao').required")
        print('PASS: campos de edição, exigência de localização e ocultação da exclusão atualizados sem recarregar.',flush=True)

        settings('cadastro');switch('mostrarColunaAula',False);close_settings()
        page.evaluate("tab('age')")
        expect(page.locator('#tabela-agenda th')).to_have_count(1)
        settings('cadastro');switch('mostrarColunaAula',True)
        page.locator('#settings-lessons').fill('8')
        page.locator('#save-lessons').click()
        expect(page.locator('#settings-status')).to_contain_text('Quantidade de aulas salva')
        close_settings()
        expect(page.locator('#tabela-agenda th')).to_have_count(2)
        expect(page.locator('#tabela-agenda tbody tr')).to_have_count(8)
        for width in [1366,800,390]:
            page.set_viewport_size({'width':width,'height':900})
            for dark in [False,True]:
                page.evaluate('(value)=>toggleTheme(value)',dark)
                assert page.locator('#tabela-agenda th:nth-child(2)').evaluate('e=>getComputedStyle(e).borderLeftWidth')=='1px'
                assert page.locator('#tabela-agenda td:nth-child(2)').first.evaluate('e=>getComputedStyle(e).borderLeftWidth')=='1px'
                page.screenshot(path=str(screens/f'agenda-{width}-{dark}.png'))
        page.set_viewport_size({'width':1366,'height':900})
        settings('circulacao')
        for name,value in {'estudante_maximo':3,'estudante_prazo':10,'estudante_renovacoes':2,'professor_maximo':5,'professor_prazo':15,'professor_renovacoes':2,'retirada_horas':48}.items():
            page.locator(f'#rules-form [name={name}]').fill(str(value))
        page.locator('#rules-form').get_by_role('button',name='Salvar regras').click()
        expect(page.locator('#settings-status')).to_contain_text('Regras salvas')
        close_settings()
        page.evaluate("tab('acervo')")
        page.locator('.book').first.click()
        page.locator('#btn-emprestar').click()
        expect(page.locator('#modalEmprestimoRapido')).to_be_visible()
        expect(page.locator('#rapido-telefone')).to_be_hidden()
        expect(page.locator('#rapido-prazo')).to_have_value('10')
        expect(page.locator('#custom-select-prazo-rapido .select-selected')).to_contain_text('padrão da biblioteca')
        page.evaluate("tipoRapidoSelect.setValue('professor')")
        expect(page.locator('#rapido-professor p')).to_contain_text('15 dias')
        page.evaluate("closeModal('modalEmprestimoRapido')")
        print('PASS: regras salvas pela interface aplicadas ao prazo estudantil e à informação dos professores.',flush=True)
        page.reload();page.wait_for_function('typeof configAgenda!=="undefined" && configAgenda.aulas===8')
        page.evaluate("tab('age')")
        expect(page.locator('#tabela-agenda tbody tr')).to_have_count(8)
        print('PASS: coluna Aula, quantidade persistida, divisão vertical em três larguras e nos dois temas.',flush=True)
        assert not errors,errors
        browser.close()
        print('Chromium encerrado.',flush=True)
finally:
    server.task_dispatcher.shutdown(timeout=5)
    server.close()
    fixture.doCleanups()
    print('Servidor e banco temporário encerrados.',flush=True)
