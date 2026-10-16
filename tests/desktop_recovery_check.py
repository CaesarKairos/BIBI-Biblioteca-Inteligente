"""Windows/WebView2 real, janela oculta e banco sintético; nenhum dado da instalação."""
from pathlib import Path
import sys
import tempfile
import threading
import time
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import webview
import desktop
from app import create_app
from werkzeug.security import generate_password_hash, check_password_hash


def main():
    with tempfile.TemporaryDirectory(prefix='bibi-native-test-') as directory:
        app=create_app({'DATA_DIR':directory,'TESTING':True})
        with app.extensions['database'].connection() as conn:
            conn.execute("INSERT INTO Contas(nome,email,senha_hash,papel,ativacao,onboarding_concluido_em) VALUES ('Teste','native@example.test',?,'bibliotecario','inicial',CURRENT_TIMESTAMP)",(generate_password_hash('senha inicial sintetica'),))
            conn.commit()
        original_server=desktop.create_server
        original_window=webview.create_window
        original_start=webview.start
        context={}
        errors=[]

        def make_server(application,**kwargs):
            kwargs['port']=0
            result=original_server(application,**kwargs)
            context['base']=f'http://127.0.0.1:{result.effective_port}'
            return result

        def make_window(title,url,**kwargs):
            kwargs.update(hidden=True,focus=False)
            result=original_window(title,url.replace('http://127.0.0.1:5000',context['base']),**kwargs)
            load=result.load_url
            result.load_url=lambda target:load(target.replace('http://127.0.0.1:5000',context['base']))
            context['window']=result
            return result

        def start(**kwargs):
            menu=kwargs['menu']
            def exercise():
                window=context['window']
                try:
                    window.events.loaded.wait(20)
                    menu[0].items[0].function()
                    deadline=time.monotonic()+25
                    while time.monotonic()<deadline:
                        ready=window.evaluate_js("location.pathname==='/recuperacao-local' && document.querySelector('#access-submit') && !document.querySelector('#access-submit').disabled && location.hash===''")
                        if ready:
                            break
                        time.sleep(.1)
                    else:
                        raise AssertionError('O formulário desktop não ficou pronto.')
                    window.evaluate_js("""const f=document.getElementById('access-form'); f.elements.email.value='native@example.test';f.elements.senha.value='nova senha nativa sintetica';f.elements.confirmacao.value='nova senha nativa sintetica';f.requestSubmit();""")
                    while time.monotonic()<deadline:
                        with app.extensions['database'].connection() as conn:
                            hashed=conn.execute('SELECT senha_hash FROM Contas').fetchone()[0]
                        if check_password_hash(hashed,'nova senha nativa sintetica'):
                            assert app.extensions['desktop_recovery'].pending is None
                            print('PASS: PyWebView/WebView2 oculto, ação do menu, sessão, redefinição e consumo único.',flush=True)
                            break
                        time.sleep(.1)
                    else:
                        raise AssertionError('A redefinição nativa não foi concluída.')
                except Exception as error:
                    errors.append(type(error).__name__+': '+str(error))
                finally:
                    window.destroy()
            watchdog=threading.Timer(55,lambda:context['window'].destroy())
            watchdog.daemon=True;watchdog.start()
            try:
                return original_start(exercise,gui='edgechromium',**kwargs)
            finally:
                watchdog.cancel()

        with patch.object(desktop,'create_server',make_server),patch.object(webview,'create_window',make_window),patch.object(webview,'start',start),patch('services.email_service.iniciar_verificacao_notificacoes'):
            desktop.run_desktop(app)
        if errors:
            raise AssertionError(errors)


if __name__=='__main__':
    main()
