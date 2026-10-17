"""Teste Windows/WebView2 real, janela invisível e instalação sintética."""
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


def main():
    with tempfile.TemporaryDirectory(prefix='bibi-tray-test-') as directory:
        app=create_app({'DATA_DIR':directory,'LAN_PORT':0,'DESKTOP_TRAY':True})
        original_server=desktop.create_server
        original_window=webview.create_window
        original_start=webview.start
        state={};errors=[]
        def server(application,**kwargs):
            kwargs['port']=0
            result=original_server(application,**kwargs)
            state['base']=f'http://127.0.0.1:{result.effective_port}'
            return result
        def window(title,url,**kwargs):
            kwargs.update(hidden=True,focus=False)
            result=original_window(title,state['base'],**kwargs)
            state['window']=result
            return result
        def start(**kwargs):
            def exercise():
                current=state['window']
                try:
                    assert current.events.shown.wait(15),'Janela não inicializou'
                    from System import Action
                    def invisible():
                        current.native.Opacity=0
                        current.native.ShowInTaskbar=False
                    current.native.Invoke(Action(invisible))
                    current.native.Invoke(Action(lambda:current.native.Show()))
                    assert current.events.loaded.wait(15),'Página não carregou no WebView2'
                    tray=app.extensions.get('desktop_tray')
                    assert tray and tray.icon.Visible,'Ícone da bandeja não instalado'
                    current.native.Invoke(Action(lambda:current.native.Show()))
                    current.native.Invoke(Action(lambda:current.native.Close()))
                    time.sleep(.3)
                    assert not current.native.Visible
                    assert app.extensions['network_runtime'].status()['ativo']
                    result=app.extensions['network_runtime'].diagnose()
                    assert all(item['conectou'] for item in result['resultados'])
                    tray.show()
                    assert current.native.Visible
                    state['exercised']=True
                    print('PASS: fechar oculta; servidor HTTPS continua; bandeja reabre.',flush=True)
                except Exception as error:
                    errors.append(repr(error))
                finally:
                    tray=app.extensions.get('desktop_tray')
                    if tray: tray.exit()
                    else: current.destroy()
            watchdog=threading.Timer(45,lambda:app.extensions.get('desktop_tray').exit() if app.extensions.get('desktop_tray') else state['window'].destroy())
            watchdog.daemon=True;watchdog.start()
            try: return original_start(exercise,gui='edgechromium',**kwargs)
            finally: watchdog.cancel()
        with patch.object(desktop,'create_server',server),patch.object(webview,'create_window',window),patch.object(webview,'start',start),patch('services.email_service.iniciar_verificacao_notificacoes'):
            desktop.run_desktop(app)
        assert not app.extensions['network_runtime'].status()['ativo']
        assert not app.extensions.get('desktop_tray')
        if errors: raise AssertionError(errors)
        assert state.get('exercised'),'Teste da bandeja não foi concluído antes do watchdog'
        print('PASS: encerrar pela bandeja fecha janela e servidor.',flush=True)


if __name__=='__main__': main()
