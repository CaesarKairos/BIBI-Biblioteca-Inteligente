"""Smoke opcional do build Windows, isolado da instalação e sem serviços externos."""
import argparse
from contextlib import closing
import os
import re
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import requests
from services.importacao_acervo import import_catalog
from tools.processos_validacao import stop_process_tree


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--exe',required=True,type=Path);parser.add_argument('--zip',required=True,type=Path);args=parser.parse_args()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));lan_port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    with tempfile.TemporaryDirectory(prefix='bibi-exe-smoke-') as work:
        root=Path(work)/'BIBI';import_catalog(args.zip,root,apply=True)
        env=os.environ.copy();env['LOCALAPPDATA']=work;env['BIBI_DESKTOP_PORT']=str(port);env['BIBI_LAN_PORT']=str(lan_port)
        startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        process=subprocess.Popen([str(args.exe.resolve())],env=env,startupinfo=startup)
        try:
            client=requests.Session();client.trust_env=False
            for _ in range(40):
                if process.poll() is not None:raise RuntimeError('Executável encerrou antes de servir a aplicação.')
                try:
                    response=client.get(base+'/configuracao-inicial',timeout=2)
                    if response.status_code==200:break
                except requests.RequestException:pass
                time.sleep(.5)
            else:raise RuntimeError('Servidor do executável não iniciou no prazo.')
            assert 'Configuração' in response.text or 'biblioteca' in response.text.lower()
            version=re.search(r'name="termos_versao" value="([^"]+)"',response.text).group(1)
            # O cadastro é sintético; nenhum dado da instalação real é aberto.
            token=client.get(base+'/api/acesso/csrf',timeout=5).json()['csrf']
            response=client.post(base+'/api/acesso/configurar',headers={'X-CSRF-Token':token},json={'biblioteca':'Teste do executável','nome':'Admin de teste','email':'exe@example.test','senha':'senha forte de teste','confirmacao':'senha forte de teste','aceite':True,'termos_versao':version},timeout=10)
            if response.status_code!=200:raise RuntimeError('Cadastro: '+str(response.status_code)+' '+response.text)
            books=client.get(base+'/api/livros',timeout=5).json();assert len(books)==32
            for book in books:assert client.get(base+book['capa'],timeout=30).status_code==200
            assert (root/'Biblioteca.db').is_file()
            assert not list(args.exe.parent.glob('*.db'))
            token=client.get(base+'/api/acesso/csrf',timeout=30).json()['csrf']
            from services.avatar_service import default
            response=client.put(base+'/api/minha-conta/avatar',headers={'X-CSRF-Token':token},json=default(),timeout=30)
            assert response.status_code==200,response.text
            from playwright.sync_api import sync_playwright,expect
            with sync_playwright() as p:
                browser=p.chromium.launch()
                context=browser.new_context(viewport={'width':1366,'height':768})
                context.add_cookies([{'name':k,'value':v,'url':base} for k,v in client.cookies.get_dict().items()])
                context.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
                page=context.new_page();page.set_default_timeout(60000)
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(base+'/app');expect(page.locator('.book')).to_have_count(32)
                page.locator('.book').first.click();expect(page.locator('#det-titulo')).not_to_be_empty()
                page.goto(base+'/perfil');expect(page.locator('#saved-avatar')).to_be_visible()
                page.goto(base+'/configuracoes');expect(page.locator('#settings-dialog')).to_be_visible()
                assert not errors,errors
                browser.close()
            # TLS real, com a autoridade desta instalação descartável.
            ca=root/'rede'/'BIBI-rede-local.crt'
            with requests.Session() as tls:
                tls.trust_env=False
                assert tls.get(f'https://127.0.0.1:{lan_port}/acesso',verify=str(ca),timeout=30).status_code==200
            print('Chromium no executável: acervo, detalhes, perfil, configurações e HTTPS com CA da instalação aprovados.')
            from services.image_service import validate_image
            for book in books:
                validate_image(client.get(base+book['capa'],timeout=30).content)
            for path in ('/static/js/livros.js','/static/images/icon.png'):
                assert client.get(base+path,timeout=30).status_code==200
            import sqlite3
            with closing(sqlite3.connect(root/'Biblioteca.db')) as conn:
                assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                assert not conn.execute('PRAGMA foreign_key_check').fetchall()
                assert conn.execute('SELECT COUNT(*) FROM Migracoes').fetchone()[0]>=6
            stop_process_tree(process)
            client.close()
            process=subprocess.Popen([str(args.exe.resolve())],env=env,startupinfo=startup)
            client=requests.Session();client.trust_env=False
            for _ in range(60):
                try:
                    if client.get(base+'/acesso',timeout=3).status_code==200:break
                except requests.RequestException:pass
                time.sleep(.5)
            else:raise RuntimeError('Servidor não voltou após reinício.')
            token=client.get(base+'/api/acesso/csrf',timeout=30).json()['csrf']
            response=client.post(base+'/api/acesso/entrar',headers={'X-CSRF-Token':token},json={'email':'exe@example.test','senha':'senha forte de teste'},timeout=30)
            assert response.status_code==200,response.text
            assert len(client.get(base+'/api/livros',timeout=30).json())==32
            print('Reinício, login, persistência, imagens decodificadas e integridade/migrações aprovados.')
            print('Executável: servidor local, primeiro cadastro, catálogo de 32 livros e 32 capas aprovados em LOCALAPPDATA temporário.')
        finally:
            stop_process_tree(process)
            client.close()


if __name__=='__main__':main()
