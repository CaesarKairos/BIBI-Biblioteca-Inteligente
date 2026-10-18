"""Chromium + HTTP real + serviços simulados, dados e credenciais descartáveis."""
import json
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from tests.support import AuthClient, authenticate, HASH
from services.ai.providers import Provider, ProviderError
from waitress import create_server
from playwright.sync_api import sync_playwright, expect

def main():
    expect.set_options(timeout=15000)
    with tempfile.TemporaryDirectory(prefix='bibi-browser-ia-') as directory:
        app=create_app({'TESTING':True,'DATA_DIR':directory});app.test_client_class=AuthClient
        with app.app_context(),app.extensions['database'].connection() as conn:
            conn.execute("INSERT INTO Contas(id,nome,email,senha_hash,papel,ativacao,onboarding_concluido_em) VALUES (1,'Admin','admin@example.test',?,'bibliotecario','inicial',CURRENT_TIMESTAMP)",(HASH,))
            for id in (2,3):
                conn.execute("INSERT INTO Usuarios(id,nome,email,tipo) VALUES (?,?,?,'estudante')",(id,'Leitor',f'reader{id}@example.test'))
                conn.execute("INSERT INTO Contas(id,leitor_id,nome,email,senha_hash,papel,ativacao,onboarding_concluido_em) VALUES (?,?,'Leitor',?,?,'leitor','presencial',CURRENT_TIMESTAMP)",(id,id,f'reader{id}@example.test',HASH))
            for id,title in ((1,'Livro de outra autoria'),(2,'Livro de autora brasileira'),(3,'Poesia para descobrir')):
                conn.execute('INSERT INTO Livros(id,nome,autor,estoque,quantidade_disponivel) VALUES (?,?,?,2,2)',(id,title,'Autoria documentada'))
            conn.execute("UPDATE Livros SET autoria_genero='feminina',autoria_pais='Brasil',autoria_fonte='Fonte sintética do teste' WHERE id=2")
            conn.commit()
        server=create_server(app,host='127.0.0.1',port=0,threads=8)
        thread=threading.Thread(target=server.run,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.effective_port}';errors=[];calls=[]
        def stream(model,system,messages,tokens):
            calls.append((system,messages))
            yield 'Vamos conversar '
            time.sleep(.3)
            yield 'sobre os temas desta leitura, sem spoilers.'
        try:
            with patch.object(Provider,'models',return_value=[{'id':'mock-literature','nome':'Modelo simulado','estado':'listado','precos':None}]),patch.object(Provider,'stream',side_effect=stream),patch('requests.request',side_effect=AssertionError('Rede externa proibida')),sync_playwright() as p:
                browser=p.chromium.launch()
                def context(id):
                    client=app.test_client()
                    with app.app_context():authenticate(app,client,id)
                    ctx=browser.new_context(viewport={'width':1366,'height':900})
                    cookie=client.get_cookie('session')
                    ctx.add_cookies([{'name':'session','value':cookie.value,'url':base}])
                    ctx.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
                    page=ctx.new_page();page.on('pageerror',lambda error:(errors.append(str(error)),print('JS ERROR:',error,flush=True)))
                    return ctx,page
                admin,page=context(1);reader,student=context(2);other,second=context(3)
                page.goto(base+'/app');print('admin app',flush=True)
                page.locator('#config-open').click();page.locator('[data-settings-section=inteligencia-artificial]').click()
                form=page.locator('#ai-config-form');expect(form).to_be_visible()
                expect(page.locator('#ai-config-state')).to_contain_text('IA desativada')
                form.locator('[name=chave]').fill('temporary-secret');form.locator('[name=ativa]').check();form.locator('[name=privacidade_revisada]').check();form.locator('[name=senha_atual]').fill('senha forte de teste')
                form.get_by_role('button',name='Salvar configuração',exact=True).click()
                expect(page.locator('#ai-config-state')).to_contain_text('IA ativa')
                expect(form.locator('[name=chave]')).to_have_value('')
                page.locator('#ai-models').click();expect(form.locator('[name=modelo] option[value=mock-literature]')).to_have_count(1)
                form.locator('[name=modelo]').select_option('mock-literature',force=True);form.locator('[name=senha_atual]').fill('senha forte de teste')
                form.get_by_role('button',name='Salvar configuração',exact=True).click();expect(page.locator('#ai-config-state')).to_contain_text('mock-literature')
                page.locator('#ai-test').click();expect(page.locator('#ai-config-state')).to_contain_text('funcionaram neste teste')
                print('config, models, connection mock',flush=True)
                page.locator('#settings-close').click()
                page.locator('#m-dash').click()
                expect(page.locator('.bibi-insights')).to_contain_text('sobre os temas desta leitura')
                page.locator('#config-open').click();page.locator('[data-settings-section=inteligencia-artificial]').click()
                student.goto(base+'/app');expect(student.locator('#prateleira-bibi .book').first).to_have_attribute('data-livro-id','2')
                expect(student.locator('.shelf')).to_have_count(5)
                student.locator('#prateleira-bibi .book').first.click()
                expect(student.locator('#info-livro')).to_be_visible()
                student.locator('#bibi-suggestions').get_by_role('button',name='Podemos discutir os personagens?',exact=True).click()
                expect(student.locator('#bibi-status')).to_contain_text('preparando')
                expect(student.locator('.bibi-answer')).to_contain_text('sem spoilers')
                expect(student.locator('#bibi-status')).to_contain_text('Resposta concluída')
                student.locator('#bibi-chat-form textarea').fill('Compare com outra leitura')
                student.locator('#bibi-chat-form').get_by_role('button',name='Enviar',exact=True).click()
                expect(student.locator('.bibi-answer')).to_have_count(2);expect(student.locator('#bibi-status')).to_contain_text('Resposta concluída')
                assert len(calls[-1][1])==3
                second.goto(base+'/app');expect(second.locator('.bibi-answer')).to_have_count(0)
                print('personalized shelf, suggestions, streaming, context, isolation',flush=True)
                review=student.locator('#reader-book-actions form');review.locator('select').select_option('5',force=True);review.locator('textarea').fill('Uma leitura acolhedora.')
                print('review filled',flush=True)
                review.get_by_role('button',name='Salvar avaliação',exact=True).click()
                print('review saved',flush=True)
                student.locator('#fechar-detalhes').click();student.locator('#prateleira-bibi .book').first.click()
                print('review reopened',flush=True)
                expect(student.locator('#reader-book-actions')).to_contain_text('Uma leitura acolhedora.')
                second.locator('#prateleira-bibi .book').first.click();expect(second.locator('#reader-book-actions')).to_contain_text('Uma leitura acolhedora.')
                student.locator('#reader-book-actions textarea').fill('Minha reflexão editada sobre o livro.')
                student.locator('#reader-book-actions').get_by_role('button',name='Salvar avaliação',exact=True).click()
                second.locator('#fechar-detalhes').click();second.locator('#prateleira-bibi .book').first.click()
                expect(second.locator('#reader-book-actions')).to_contain_text('Minha reflexão editada sobre o livro.')
                student.locator('#reader-book-actions textarea').fill('idiota')
                student.locator('#reader-book-actions').get_by_role('button',name='Salvar avaliação',exact=True).click()
                expect(student.locator('#reader-book-actions').get_by_role('button',name='Salvar avaliação',exact=True)).to_be_enabled()
                page.goto(base+'/app?config=moderacao')
                page.wait_for_function('Boolean(window.settingsManagementReady)')
                page.evaluate('async()=>await window.settingsManagementReady')
                moderation=page.locator('#moderation-list article').filter(has_text='idiota')
                expect(moderation).to_contain_text('revisao')
                moderation.get_by_role('textbox',name='Motivo da moderação',exact=True).fill('Comentário inadequado ao ambiente escolar.')
                moderation.get_by_role('button',name='Ocultar',exact=True).click()
                expect(moderation).to_contain_text('oculto')
                notifications=student.evaluate("() => accountApi('/api/minha-conta/notificacoes')")
                assert any('moderada' in item['mensagem'] for item in notifications)
                second.locator('#fechar-detalhes').click();second.locator('#prateleira-bibi .book').first.click()
                expect(second.locator('#reader-book-actions')).not_to_contain_text('idiota')
                page.locator('[data-settings-section=inteligencia-artificial]').click()
                student.locator('#reader-book-actions').get_by_role('button',name='Excluir minha avaliação',exact=True).click()
                expect(student.locator('#reader-book-actions')).not_to_contain_text('Uma leitura acolhedora.')
                for width in (1366,390):
                    student.set_viewport_size({'width':width,'height':844})
                    for dark in (False,True):
                        student.evaluate('(dark)=>document.body.classList.toggle("dark-mode",dark)',dark)
                        assert student.evaluate('document.documentElement.scrollWidth<=innerWidth')
                student.emulate_media(reduced_motion='reduce')
                student.locator('#bibi-chat-form textarea').fill('Quero conversar sobre literatura')
                student.locator('#bibi-chat-form').get_by_role('button',name='Enviar',exact=True).click()
                student.locator('#bibi-cancel').click();expect(student.locator('#bibi-status')).to_contain_text('interrompida')
                print('cancel confirmed; settings visible:',page.locator('#ai-disable').is_visible(),flush=True)
                page.locator('#ai-disable').click();expect(page.locator('#ai-config-state')).to_contain_text('IA desativada')
                count=len(calls)
                student.locator('#bibi-chat-form textarea').fill('Recomende um livro')
                student.locator('#bibi-chat-form').get_by_role('button',name='Enviar',exact=True).click()
                expect(student.locator('#bibi-status')).to_contain_text('desativada');assert len(calls)==count
                print('disable confirmed',flush=True)
                assert not errors,errors
                browser.close()
                print('PASS: AI settings, model list, dashboard insights, stream, contexts, review editing/moderation/notification, cancellation, mobile/themes, global disable. Cloud mocked.',flush=True)
        finally:
            server.close();thread.join(timeout=3)

if __name__=='__main__':main()
