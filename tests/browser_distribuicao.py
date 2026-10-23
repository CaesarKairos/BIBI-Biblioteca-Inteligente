"""Capturas novas da aplicação real; preparação sintética via APIs reais."""
import json
import argparse
import base64
import os
import shutil
import sqlite3
from pathlib import Path
import sys
import tempfile
import threading
import socket
import subprocess
import time
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from services.importacao_acervo import import_catalog
from tools.catalogo_distribuicao import create_archive
from tools.processos_validacao import stop_process_tree
from services.avatar_service import default
from services.termos_service import VERSAO
from tests.support import AuthClient
from waitress import create_server
from playwright.sync_api import sync_playwright, expect


def main():
    expect.set_options(timeout=60000)
    if os.getenv('BIBI_BROWSER_TRACE'):
        import faulthandler
        faulthandler.dump_traceback_later(45,repeat=True)
    parser=argparse.ArgumentParser()
    parser.add_argument('--catalogo-local',type=Path,help='Somente livros e capas; nunca importa contas ou leitores.')
    args=parser.parse_args()
    screens=Path('docs/readme');screens.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bibi-distribuicao-ui-') as work:
        root=Path(work)
        if not args.catalogo_local:
            archive=root/'demo.zip';create_archive(archive)
            import_catalog(archive,root/'dados',apply=True)
        app=create_app({'TESTING':True,'DATA_DIR':str(root/'dados')})
        if args.catalogo_local:
            origin=args.catalogo_local.resolve()
            source=sqlite3.connect((origin/'Biblioteca.db').as_uri()+'?mode=ro',uri=True)
            columns=['isbn','nome','autor','ano_publicacao','numero_paginas','capa_url','descricao','temas','categoria','estoque','data_cadastro','localizacao']
            rows=source.execute('SELECT '+','.join(columns)+' FROM Livros WHERE arquivado=0 ORDER BY id').fetchall();source.close()
            with app.extensions['database'].connection() as conn:
                conn.executemany('INSERT INTO Livros('+','.join(columns)+',quantidade_disponivel) VALUES ('+','.join('?' for _ in range(len(columns)+1))+')',[tuple(row)+(row[9],) for row in rows]);conn.commit()
            for row in rows:
                url=row[5] or ''
                for folder in ('uploadedcovers','externalcovers'):
                    if url.startswith('/'+folder+'/'):
                        path=origin/folder/Path(url).name
                        if path.is_file():shutil.copy2(path,root/'dados'/folder/path.name)
        app.test_client_class=AuthClient
        admin=app.test_client()
        def api(client,path,method='GET',data=None):
            response=client.open(path,method=method,json=data)
            assert response.status_code<400,(path,response.status_code,response.json)
            return response.json
        api(admin,'/api/acesso/csrf')
        api(admin,'/api/acesso/configurar','POST',dict(biblioteca='Biblioteca de demonstração',nome='Bibliotecária de demonstração',email='admin@example.test',senha='senha forte de teste',confirmacao='senha forte de teste',aceite=True,termos_versao=VERSAO))
        api(admin,'/api/minha-conta/avatar','PUT',default())
        real_ai=bool(os.getenv('BIBI_SCREENSHOT_OPENROUTER_KEY'))
        if real_ai:
            api(admin,'/api/ia/servicos/openrouter','PUT',dict(chave=os.environ['BIBI_SCREENSHOT_OPENROUTER_KEY'],senha_atual='senha forte de teste',habilitado=True,custos_autorizados=False,privacidade_revisada=True,limite_diario=30))
            api(admin,'/api/ia/servicos/openrouter/modelos','POST',{})
            result=api(admin,'/api/ia/servicos/openrouter/testar','POST',{})
            print('Verificação real OpenRouter:',result,flush=True)
            api(admin,'/api/ia/servicos','PUT',dict(ativa=True,senha_atual='senha forte de teste',max_tokens=384,por_dia=30))
        books=api(admin,'/api/livros')
        readers=[]
        for i in range(8):
            readers.append(api(admin,'/api/leitores','POST',dict(nome=['Ana Demonstração','Lia Exemplo','Caio Demonstração','Rita Exemplo','Davi Demonstração','Bia Exemplo','Luís Demonstração','Eva Exemplo'][i],tipo='estudante',sala=f'{7+i%3} A',periodo='Manhã',email=f'leitor{i}@example.test'))['id'])
        invite=api(admin,f'/api/contas/leitores/{readers[0]}/codigo','POST',{})['codigo']
        student=app.test_client();api(student,'/api/acesso/csrf')
        api(student,'/api/acesso/ativar','POST',dict(email='leitor0@example.test',codigo=invite,senha='senha forte de teste',confirmacao='senha forte de teste'))
        api(student,'/api/minha-conta/avatar','PUT',default())
        policy={'estudante':{'maximo':4,'prazo':7,'renovacoes':2,'bloquear_atraso':True},'professor':{'maximo':10,'prazo':7,'renovacoes':2,'bloquear_atraso':True},'retirada_horas':48}
        api(admin,'/api/gestao/configuracao','PUT',{'circulacao':policy})
        for i in range(6):
            api(admin,'/api/emprestimos','POST',dict(leitor_id=readers[i%4],livros=[{'id':books[i]['id']}]))
        loans=api(student,'/api/minha-conta/emprestimos')
        api(admin,f"/api/emprestimos/{loans[0]['id']}/devolver",'POST',{})
        bid=next((book['id'] for book in books if book['titulo']=='Capitães da Areia'),books[0]['id'])
        api(student,'/api/minha-conta/favoritos','PUT',{'livros':[bid,books[4]['id']]})
        # Usa os mesmos endpoints que os botões dos detalhes.
        api(student,f'/api/minha-conta/quero-ler/{bid}','POST',{})
        api(student,f'/api/minha-conta/lidos/{bid}','POST',{})
        api(student,f'/api/minha-conta/avaliacoes/{bid}','POST',{'estrelas':5,'comentario':'Uma leitura que rende boas conversas no clube da biblioteca.'})
        from utils.datetime import get_brasilia_today
        today=get_brasilia_today()
        with app.extensions['database'].connection() as conn:
            for i in range(3):
                conn.execute('INSERT INTO Agendamento(data,periodo,dia_semana,aula,professor,materia,uso,turma) VALUES (?,?,?,?,?,?,?,?)',(today.isoformat(),'Manhã',today.weekday(),i+1,['Professora de demonstração','Professor de exemplo','Mediadora de leitura'][i],'Língua Portuguesa',['Clube de leitura','Pesquisa orientada','Roda de conversa'][i],f'{7+i} A'))
            conn.commit()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=subprocess.Popen([sys.executable,'tools/servidor_validacao.py','--data-dir',str(root/'dados'),'--port',str(port)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        base=f'http://127.0.0.1:{port}'
        for _ in range(60):
            try:
                if requests.get(base+'/acesso',timeout=1).status_code==200:break
            except requests.RequestException:pass
            time.sleep(.2)
        else:raise RuntimeError('Servidor temporário não iniciou.')
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch();errors=[]
                def page_for(client):
                    context=browser.new_context(viewport={'width':1920,'height':1080},locale='pt-BR')
                    if not args.catalogo_local:
                        context.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
                    context.add_cookies([{'name':'session','value':client.get_cookie('session').value,'url':base}])
                    page=context.new_page();page.set_default_timeout(60000)
                    page.on('pageerror',lambda e:errors.append(str(e)))
                    return page
                a=page_for(admin);s=page_for(student)
                def capture(page,path):
                    page.wait_for_function("Array.from(document.querySelectorAll('.book,.capa-mini,#det-capa')).filter(element=>element.getClientRects().length).every(element=>!getComputedStyle(element).backgroundImage.includes('placeholder'))",timeout=90000)
                    page.wait_for_function("Array.from(document.images).filter(image=>image.getClientRects().length).every(image=>image.complete&&image.naturalWidth>0)",timeout=90000)
                    # Captura nativa do Chromium via Playwright/CDP. Evita o
                    # bloqueio de screenshot causado por páginas com mídia ativa.
                    session=page.context.new_cdp_session(page)
                    try:
                        result=session.send('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
                        Path(path).write_bytes(base64.b64decode(result['data']))
                    finally:session.detach()
                def shot(page,path,name,selector):
                    print('Captura',name,flush=True)
                    page.goto(base+path,wait_until='domcontentloaded')
                    print('DOM pronto',name,flush=True)
                    if '#' in path:page.locator('#m-'+path.split('#')[1]).click()
                    expect(page.locator(selector).first).to_be_visible(timeout=60000)
                    print('Conteúdo pronto',name,flush=True)
                    if path.startswith('/app') and '#' not in path:
                        page.wait_for_timeout(6000 if args.catalogo_local else 2500)
                    if path.startswith('/app') and '#' not in path:
                        page.wait_for_function("Array.from(document.querySelectorAll('.book')).every(book=>!getComputedStyle(book).backgroundImage.includes('placeholder'))",timeout=90000)
                    page.wait_for_timeout(1200)
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),name
                    capture(page,screens/(name+'.png'))
                    print('Salva',name,flush=True)
                shot(a,'/app','acervo','.book')
                # Valida todas as imagens do acervo sintético por HTTP e pelo decodificador do navegador.
                for book in books:
                    if book['capa'] and book['capa'].startswith('/'):
                        response=a.request.get(base+book['capa'],timeout=60000);assert response.status==200
                shot(a,'/app#dash','dashboard','#m-dash')
                shot(a,f'/app?livro={bid}','detalhes-livro','#det-titulo')
                shot(a,'/app#emp','emprestimos','#m-emp')
                shot(a,'/app#age','agenda','#m-age')
                shot(s,'/perfil','perfil-leitor','#profile-favorites article')
                s.locator('#profile-history').scroll_into_view_if_needed();capture(s,screens/'historico-leitura.png')
                s.locator('#profile-wishes').scroll_into_view_if_needed();capture(s,screens/'listas-pessoais.png')
                shot(s,f'/app?livro={bid}','avaliacoes','#det-titulo')
                s.locator('.book-review-form').scroll_into_view_if_needed();capture(s,screens/'avaliacoes.png')
                a.goto(base+'/configuracoes');a.locator('[data-settings-section="gestao-config"]').click();a.wait_for_timeout(1000);capture(a,screens/'configuracoes.png')
                a.locator('[data-settings-section="inteligencia-artificial"]').click();a.wait_for_timeout(500);capture(a,screens/'ia-opcional.png')
                if real_ai:
                    s.goto(base+'/app');expect(s.locator('#bibi-input')).to_be_visible()
                    s.locator('#bibi-input').fill('Em até 40 palavras, recomende uma obra de autora brasileira deste acervo para começar a ler. Responda em português brasileiro, sem formatação.')
                    s.locator('#bibi-send').click()
                    expect(s.locator('.bibi-answer').last).not_to_be_empty(timeout=180000)
                    s.wait_for_function("!document.querySelector('#bibi-send').disabled",timeout=180000)
                    expect(s.locator('#bibi-status')).to_have_text('Resposta concluída. Confira os dados do acervo.')
                    s.locator('#bibi-messages').evaluate('(element)=>element.scrollTop=0')
                    s.wait_for_timeout(1000);capture(s,screens/'ia-conversa.png')
                    print('Conversa real capturada:',s.locator('.bibi-answer').last.inner_text(),flush=True)
                s.goto(base+'/perfil');expect(s.locator('#profile-favorites article').first).to_be_visible();s.locator('#theme-toggle-btn').click();s.set_viewport_size({'width':390,'height':844});s.wait_for_timeout(700);capture(s,screens/'perfil-mobile-escuro.png')
                a.goto(base+'/app');expect(a.locator('.book').first).to_be_visible();a.locator('#theme-toggle-btn').click();a.wait_for_timeout(6000);capture(a,screens/'acervo-escuro.png')
                assert not errors,errors
                browser.close()
            Path('docs/validacao/distribuicao-interface.json').write_text(json.dumps({'resultado':'aprovado','capturas':14 if real_ai else 13,'catalogo':f'{len(books)} obras da instalação local; contas e circulação sintéticas' if args.catalogo_local else '32 obras fictícias; capas tipográficas próprias','resolucoes':['1920x1080','390x844'],'temas':['claro','escuro'],'ia':'OpenRouter real; verificação e conversa geradas por modelo gratuito, sem simulação' if real_ai else 'Interface real, desativada; nenhuma resposta simulada ou serviço externo','erros_js':errors},ensure_ascii=False,indent=2),encoding='utf-8')
        finally:
            stop_process_tree(server)


if __name__=='__main__':main()
