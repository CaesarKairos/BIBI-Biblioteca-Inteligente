"""Smoke opcional do build Windows, isolado da instalação e sem serviços externos."""
import argparse
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


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--exe',required=True,type=Path);parser.add_argument('--zip',required=True,type=Path);args=parser.parse_args()
    with socket.socket() as sock:
        if sock.connect_ex(('127.0.0.1',5000))==0:raise RuntimeError('Porta 5000 ocupada. Não será encerrada outra instalação.')
    with tempfile.TemporaryDirectory(prefix='bibi-exe-smoke-') as work:
        root=Path(work)/'BIBI';import_catalog(args.zip,root,apply=True)
        env=os.environ.copy();env['LOCALAPPDATA']=work
        startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        process=subprocess.Popen([str(args.exe.resolve())],env=env,startupinfo=startup)
        try:
            client=requests.Session();client.trust_env=False
            for _ in range(40):
                if process.poll() is not None:raise RuntimeError('Executável encerrou antes de servir a aplicação.')
                try:
                    response=client.get('http://127.0.0.1:5000/configuracao-inicial',timeout=2)
                    if response.status_code==200:break
                except requests.RequestException:pass
                time.sleep(.5)
            else:raise RuntimeError('Servidor do executável não iniciou no prazo.')
            assert 'Configuração' in response.text or 'biblioteca' in response.text.lower()
            version=re.search(r'name="termos_versao" value="([^"]+)"',response.text).group(1)
            # O cadastro é sintético; nenhum dado da instalação real é aberto.
            token=client.get('http://127.0.0.1:5000/api/acesso/csrf',timeout=5).json()['csrf']
            response=client.post('http://127.0.0.1:5000/api/acesso/configurar',headers={'X-CSRF-Token':token},json={'biblioteca':'Teste do executável','nome':'Admin de teste','email':'exe@example.test','senha':'senha forte de teste','confirmacao':'senha forte de teste','aceite':True,'termos_versao':version},timeout=10)
            if response.status_code!=200:raise RuntimeError('Cadastro: '+str(response.status_code)+' '+response.text)
            books=client.get('http://127.0.0.1:5000/api/livros',timeout=5).json();assert len(books)==32
            for book in books:assert client.get('http://127.0.0.1:5000'+book['capa'],timeout=5).status_code==200
            assert (root/'Biblioteca.db').is_file()
            assert not list(args.exe.parent.glob('*.db'))
            print('Executável: servidor local, primeiro cadastro, catálogo de 32 livros e 32 capas aprovados em LOCALAPPDATA temporário.')
        finally:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            client.close()


if __name__=='__main__':main()
