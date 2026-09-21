"""Servidor WSGI local e janela desktop; rede requer configuração explícita."""
import threading
from waitress import create_server


def run_desktop(app):
    import webview
    from services.email_service import iniciar_verificacao_notificacoes
    # Somente o proxy local da escola pode informar origem HTTPS/IP de cliente.
    server = create_server(app,host='127.0.0.1',port=5000,threads=8,
        trusted_proxy='127.0.0.1',trusted_proxy_headers={'x-forwarded-for','x-forwarded-host','x-forwarded-proto'},
        clear_untrusted_proxy_headers=True,max_request_body_size=512*1024*1024)
    threading.Thread(target=server.run,daemon=True).start()
    iniciar_verificacao_notificacoes(app)
    webview.create_window('BIBI — Biblioteca Inteligente','http://127.0.0.1:5000',width=1366,height=768,resizable=True)
    try:
        webview.start()
    finally:
        server.close()
