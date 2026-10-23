"""Validação convencional com catálogo legado, contas sintéticas e rede externa bloqueada.

Uso: python tests/browser_pre_apresentacao.py --zip CAMINHO_LOCAL
O arquivo legado não é copiado para as evidências.
"""
import argparse
import os
import json
import sys
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from services.importacao_acervo import import_catalog
from waitress import create_server
from playwright.sync_api import sync_playwright,expect


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--zip',required=True);parser.add_argument('--screens',type=Path);args=parser.parse_args()
    screens=args.screens or Path(__file__).resolve().parents[1]/'docs/validacao/final-pre-apresentacao'
    screens.mkdir(parents=True,exist_ok=True)
    checks=[]
    expect.set_options(timeout=60000)
    with tempfile.TemporaryDirectory(prefix='bibi-final-browser-') as work:
        result=import_catalog(Path(args.zip),Path(work),apply=True)
        assert result['importados']==32,result
        app=create_app({'DATA_DIR':work,'TESTING':True})
        server=create_server(app,host='127.0.0.1',port=0,threads=8)
        thread=threading.Thread(target=server.run,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.effective_port}'
        def api(page,path,method='GET',data=None):
            return page.evaluate('''async ({path,method,data})=>{
                const csrf=(await (await fetch('/api/acesso/csrf')).json()).csrf;
                const r=await fetch(path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:method==='GET'?undefined:JSON.stringify(data||{})});
                const result=await r.json();if(!r.ok)throw Error(path+': '+JSON.stringify(result));return result;
            }''',dict(path=path,method=method,data=data))
        def goto(page,path):
            print('Navegando:',path,flush=True)
            if page.locator('#settings-dialog').count() and page.locator('#settings-dialog').is_visible():
                page.locator('#settings-close').click()
                if page.locator('#settings-discard').is_visible():page.locator('#settings-discard-confirm').click()
            page.goto(base+path);page.wait_for_load_state('networkidle')
            if path.startswith('/app#'):
                page.locator('#m-'+path.split('#',1)[1]).click();page.wait_for_load_state('networkidle')
        def shot(page,name):
            targets={'reserva-fila':'#profile-reservations','notificacoes-reservas':'#profile-notifications'}
            if name in targets:page.locator(targets[name]).scroll_into_view_if_needed()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),name
            page.screenshot(path=str(screens/(name+'.png')),full_page=True)
        def settings(page,key):
            goto(page,'/configuracoes');page.locator(f'[data-settings-section="{key}"]').click()
        errors=[]
        try:
            with patch('smtplib.SMTP',side_effect=AssertionError('SMTP real proibido')),sync_playwright() as p:
                browser=p.chromium.launch()
                def context():
                    ctx=browser.new_context(viewport={'width':1366,'height':768},locale='pt-BR')
                    ctx.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
                    page=ctx.new_page();page.set_default_timeout(60000);page.set_default_navigation_timeout(60000)
                    page.on('pageerror',lambda error:errors.append(str(error)))
                    page.on('response',lambda r:print('HTTP',r.status,r.url.split(base)[-1],flush=True) if r.status>=400 or os.getenv('BIBI_BROWSER_TRACE') else None)
                    return page
                admin=context();goto(admin,'/app');assert '/configuracao-inicial' in admin.url
                for name,value in {'biblioteca':'Biblioteca de demonstração','nome':'Bibliotecária de teste','email':'admin@example.test','senha':'senha forte de teste','confirmacao':'senha forte de teste'}.items():admin.locator(f'[name={name}]').fill(value)
                admin.locator('[name=aceite]').check();admin.locator('#access-submit').click();admin.wait_for_url('**/boas-vindas');expect(admin.locator('#suggested-avatar')).to_be_visible();admin.locator('#suggested-avatar').click();admin.wait_for_url('**/app');admin.wait_for_load_state('networkidle')
                books=api(admin,'/api/livros');assert len(books)==32
                for b in books:assert admin.request.get(base+b['capa'],timeout=10000).status==200,b
                print('Catálogo e capas verificados',flush=True)
                assert admin.locator('.shelf').count()==4
                checks.append('Primeiro cadastro após importação; 32 livros e 32 capas HTTP 200; quatro prateleiras sem IA')
                book=books[0];bid=book['id']
                for query in [book['titulo'],book['autor'],book['isbn']]:
                    if not query:continue
                    admin.locator('#busca-acervo').fill(query);admin.wait_for_timeout(450);admin.wait_for_load_state('networkidle');assert admin.locator('.book').count()>0
                admin.locator('#catalog-clear').click();admin.wait_for_load_state('networkidle')
                # Preparação por API é explicitamente separada dos cliques testados abaixo.
                policy={'estudante':{'maximo':4,'prazo':7,'renovacoes':2,'bloquear_atraso':True},'professor':{'maximo':10,'prazo':7,'renovacoes':2,'bloquear_atraso':True},'retirada_horas':48}
                api(admin,'/api/gestao/configuracao','PUT',{'circulacao':policy})
                readers=[]
                for i in [1,2]:
                    goto(admin,'/app#lei');admin.locator('[data-bibi-onclick=h21]').click()
                    for field,value in {'nome':f'Leitor de teste {i}','sala':'8 A','periodo':'Manhã','email':f'leitor{i}@example.test'}.items():admin.locator('#leitor-'+field).fill(value)
                    admin.locator('#btn-salvar-leitor').click();admin.wait_for_load_state('networkidle');expect(admin.locator('#modalLeitor')).not_to_be_visible()
                    rid=next(r['id'] for r in api(admin,'/api/leitores') if r['email']==f'leitor{i}@example.test')
                    settings(admin,'gestao-convites');admin.locator('#invite-reader').select_option(str(rid),force=True);admin.locator('#invite-form button.btn-primary').click();expect(admin.locator('#invite-code')).not_to_be_empty();code=admin.locator('#invite-code').inner_text()
                    page=context();goto(page,'/acesso');page.get_by_role('button',name='Ativar convite',exact=True).click()
                    for name,value in {'email':f'leitor{i}@example.test','codigo':code,'senha':'senha forte do leitor','confirmacao':'senha forte do leitor'}.items():page.locator(f'[name={name}]').fill(value)
                    assert page.locator('#access-form').evaluate('form=>form.checkValidity()'),page.locator('#access-form').evaluate('form=>Array.from(form.elements).filter(e=>!e.validity.valid).map(e=>e.name)')
                    with page.expect_response(lambda response:response.url.endswith('/api/acesso/ativar')) as activation:
                        page.locator('#access-submit').click()
                    assert activation.value.status==200,activation.value.json()
                    page.wait_for_url('**/boas-vindas');expect(page.locator('#suggested-avatar')).to_be_visible();page.locator('#suggested-avatar').click();page.wait_for_url('**/app');page.wait_for_load_state('networkidle');readers.append(page)
                student,other=readers
                goto(student,f'/app?livro={bid}');expect(student.locator('#det-titulo')).to_have_text(book['titulo'])
                shot(student,'livro-capa-detalhes')
                student.locator('#fechar-detalhes').click();expect(student.locator('#info-livro')).not_to_be_visible()
                goto(student,f'/app?livro={bid}');student.get_by_role('button',name='Quero ler',exact=True).click();student.get_by_role('button',name='Marcar como lido',exact=True).click();student.wait_for_load_state('networkidle')
                student.get_by_role('radio',name='5 estrelas',exact=True).check();student.get_by_role('textbox',name='Comentário sobre a obra').fill('Gostei dos temas e dos personagens.');student.get_by_role('button',name='Salvar avaliação',exact=True).click();student.wait_for_load_state('networkidle');expect(student.locator('.review-state')).to_contain_text('publicada')
                student.locator('.book-review-form').scroll_into_view_if_needed();shot(student,'avaliacao-estrelas')
                goto(other,f'/app?livro={bid}');expect(other.locator('.book-review-card')).to_contain_text('Gostei dos temas');assert 'leitor1@' not in other.locator('.book-review-card').inner_text()
                other.locator('.book-review-card').scroll_into_view_if_needed();shot(other,'comentario-publicado')
                assert api(other,'/api/minha-conta/lidos')==[]
                checks.append('Convite e ativação de duas contas; seleção e desmarcação; Quero ler; livro lido privado; avaliação visível por outra conta sem identidade')
                goto(student,'/perfil');student.locator('#favorite-book').select_option(str(bid),force=True);student.locator('#favorite-form button.btn-primary').click();student.wait_for_load_state('networkidle');expect(student.locator('#profile-favorites article')).to_have_count(1);expect(student.locator('#profile-read article')).to_have_count(1)
                student.locator('#edit-avatar').click();expect(student.locator('#avatar-options')).to_be_visible();student.locator('[data-avatar-field=eyesVariant][data-avatar-value=variant02]').click();student.wait_for_load_state('networkidle');student.locator('#save-avatar').click();student.wait_for_load_state('networkidle')
                goto(admin,f'/app?livro={bid}');admin.locator('#btn-emprestar').click();admin.locator('#rapido-nome').fill('Leitor de teste 1');expect(admin.locator('#rapido-nome-suggestions')).to_be_visible();admin.locator('#rapido-nome-suggestions > div').first.click();admin.locator('#btn-confirmar-emprestimo').click();admin.wait_for_load_state('networkidle');expect(admin.locator('#modalEmprestimoRapido')).not_to_be_visible()
                goto(student,'/perfil');student.get_by_role('button',name='Solicitar renovação').click();student.wait_for_load_state('networkidle');expect(student.locator('#profile-loans')).to_contain_text('pendente')
                settings(admin,'circulacao');expect(admin.locator('#renewal-list article')).to_have_count(1);shot(admin,'renovacao-pendente');admin.get_by_role('button',name='Aprovar renovação').click();admin.wait_for_load_state('networkidle');expect(admin.locator('#renewal-list article')).to_have_count(0)
                expect(admin.locator('#settings-close')).to_be_enabled()
                goto(admin,'/app#emp');admin.wait_for_load_state('networkidle');shot(admin,'emprestimos')
                admin.get_by_role('button',name='Devolver',exact=True).first.click();admin.locator('#confirm-btn-sim').click();admin.wait_for_load_state('networkidle')
                goto(student,'/perfil');expect(student.locator('#profile-history article')).to_have_count(1);assert next(b for b in api(admin,'/api/livros') if b['id']==bid)['disponivel']==book['disponivel']
                checks.append('Cadastros de leitores e convites por UI; favorito, avatar, empréstimo, pedido e aprovação de renovação, devolução por UI; histórico/estoque conferidos')
                # Esgota um título apenas no banco temporário, sem alterar os 32 registros reais.
                reserve_book=api(admin,'/api/livros','POST',{'manual':True,'titulo':'Livro de teste para reserva','autor':'Autora de teste','quantidade':1})['id']
                api(admin,'/api/emprestimos','POST',{'leitor_id':1,'livros':[{'id':reserve_book}]})
                goto(other,f'/app?livro={reserve_book}');other.get_by_role('button',name='Reservar este título').click();other.wait_for_load_state('networkidle');goto(other,'/perfil');expect(other.locator('#profile-reservations')).to_contain_text('Posição na fila: 1');shot(other,'reserva-fila')
                loan=next(x for x in api(student,'/api/minha-conta/emprestimos') if x['livro_id']==reserve_book);api(admin,f"/api/emprestimos/{loan['id']}/devolver",'POST',{})
                goto(other,'/perfil');expect(other.locator('#profile-reservations')).to_contain_text('Retire até');other.get_by_role('button',name='Cancelar reserva').click();other.wait_for_load_state('networkidle');expect(other.locator('#profile-notifications')).to_contain_text('cancelada');other.get_by_role('button',name='Marcar como lida').first.click();other.wait_for_load_state('networkidle');shot(other,'notificacoes-reservas')
                goto(student,f'/app?livro={bid}');student.get_by_role('textbox',name='Comentário sobre a obra').fill('Esse personagem é idiota.');student.get_by_role('button',name='Atualizar avaliação').click();student.wait_for_load_state('networkidle');expect(student.locator('.review-state')).to_contain_text('revisão')
                goto(other,f'/app?livro={bid}');expect(other.locator('.book-review-card')).to_have_count(0)
                settings(admin,'moderacao');admin.get_by_role('textbox',name='Motivo da moderação').fill('Discussão sobre personagem, revisada pela biblioteca.');shot(admin,'moderacao');admin.get_by_role('button',name='Publicar',exact=True).click();admin.wait_for_load_state('networkidle')
                goto(other,f'/app?livro={bid}');expect(other.locator('.book-review-card')).to_contain_text('personagem')
                other.get_by_role('radio',name='3 estrelas',exact=True).check();other.get_by_role('textbox',name='Comentário sobre a obra').fill('Minha avaliação temporária.');other.get_by_role('button',name='Salvar avaliação',exact=True).click();expect(other.locator('.book-review-card')).to_have_count(2)
                other.get_by_role('button',name='Excluir minha avaliação',exact=True).click();expect(other.locator('.book-review-card')).to_have_count(1);expect(other.locator('.book-review-card')).to_contain_text('personagem')
                checks.append('Exclusão da própria avaliação preserva a opinião publicada pela outra conta')
                checks.append('Reserva em fila, separação após devolução, cancelamento, notificação e leitura; edição sinalizada, invisibilidade pública e revisão administrativa')
                goto(admin,'/app#age');shot(admin,'agenda')
                settings(admin,'inteligencia-artificial');shot(admin,'ia-opcional-desativada')
                settings(admin,'dados')
                with admin.expect_download() as download:admin.locator('#download-backup').click()
                assert download.value.failure() is None
                checks.append('Backup gerado e baixado pelo botão nas Configurações')
                goto(admin,'/app');admin.get_by_role('button',name='+ Adicionar Livro',exact=True).click();admin.get_by_role('button',name='Adicionar Manualmente',exact=True).click()
                admin.locator('#manual-titulo').fill('Cadastro de demonstração');admin.locator('#manual-autor').fill('Autora de teste');admin.locator('#btn-salvar-manual').click();admin.wait_for_load_state('networkidle');expect(admin.locator('#modalManualLivro')).not_to_be_visible()
                added=next(b for b in api(admin,'/api/livros') if b['titulo']=='Cadastro de demonstração')
                goto(admin,f"/app?livro={added['id']}");admin.get_by_role('button',name='Editar',exact=True).click();admin.locator('#edit-titulo').fill('Cadastro de demonstração revisado');admin.locator('#btn-salvar-edicao').click();admin.wait_for_load_state('networkidle');expect(admin.locator('#modalEditarLivro')).not_to_be_visible()
                assert api(admin,f"/api/livros/{added['id']}")['titulo']=='Cadastro de demonstração revisado'
                checks.append('Cadastro manual e edição de livro por UI, com estado final persistido')
                for width,height in [(1366,768),(1920,1080),(800,900),(390,844)]:
                    for dark in [False,True]:
                        label=f'{width}-'+('escuro' if dark else 'claro')
                        for page,path,name in [(admin,'/app','acervo'),(student,'/perfil','perfil'),(other,f'/app?livro={bid}','detalhes')]:
                            page.set_viewport_size(dict(width=width,height=height));goto(page,path)
                            if page.evaluate('document.body.classList.contains("dark-mode")')!=dark:
                                page.locator('#theme-toggle-btn').click();page.wait_for_load_state('networkidle')
                            if name=='detalhes':page.locator('.book-review-form').scroll_into_view_if_needed()
                            page.wait_for_timeout(180);shot(page,name+'-'+label)
                            if name=='perfil' and label in ('1366-claro','390-escuro'):
                                for section in ['favorites','history','wishes','read','reviews','notifications']:
                                    page.locator('#profile-'+section).scroll_into_view_if_needed();page.wait_for_timeout(120);shot(page,section+'-'+label)
                        goto(admin,'/app#dash');shot(admin,'dashboard-'+label)
                        settings(admin,'cadastro');shot(admin,'configuracoes-'+label)
                assert not errors,errors
                goto(student,'/perfil');student.locator('#account-logout').click();student.wait_for_url('**/acesso');student.locator('[name=email]').fill('leitor1@example.test');student.locator('[name=senha]').fill('senha forte do leitor');student.locator('#access-submit').click();student.wait_for_url('**/app');student.wait_for_load_state('networkidle');assert len(api(student,'/api/minha-conta/lidos'))==1
                checks.append('Logout, novo login e persistência das leituras da conta')
                checks.append('Acervo, detalhes/avaliações, perfil/listas/histórico, Dashboard e Configurações: 4 resoluções × claro/escuro; sem transbordamento horizontal ou erros JavaScript')
                browser.close()
        finally:
            server.close();thread.join(timeout=3)
        (screens/'resultados.json').write_text(json.dumps({'resultado':'aprovado','cenarios':checks,'rede_externa':'bloqueada','banco':'temporário','smtp':'mock'},ensure_ascii=False,indent=2),encoding='utf-8')
        print('\n'.join(checks))
        print('Capturas:',screens)


if __name__=='__main__':main()
