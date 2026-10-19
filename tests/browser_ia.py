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
        failure={'active':False}
        def stream(model,system,messages,tokens):
            calls.append((system,messages))
            if failure['active']:raise ProviderError('Chave inv\u00e1lida. Confira a chave do servi\u00e7o.','chave')
            yield 'Vamos conversar '
            time.sleep(1.2)
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
                from tests.browser_ia_refino import run_scenarios,run_loading_scenario
                if '--loading-only' in sys.argv:run_loading_scenario(student,base,browser)
                else:run_scenarios(page,student,second,base,calls,errors,browser,failure)
        finally:
            server.close();thread.join(timeout=3)

if __name__=='__main__':main()
