"""Servidor WSGI local e janela desktop; rede requer configuração explícita."""
import threading
from waitress import create_server


FULLSCREEN_SHORTCUT = """
(() => {
    if (window.__bibiFullscreenShortcut) return;
    window.__bibiFullscreenShortcut = true;
    let pending = false;
    document.addEventListener('keydown', event => {
        if (event.key !== 'F11' || event.ctrlKey || event.altKey || event.metaKey) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        if (event.repeat || pending) return;
        pending = true;
        window.pywebview.api.alternar_tela_cheia()
            .catch(() => console.error('Não foi possível alternar a tela cheia.'))
            .finally(() => { pending = false; });
    }, true);
})();
"""


def run_desktop(app):
    import webview
    from services.email_service import iniciar_verificacao_notificacoes
    # Somente o proxy local da escola pode informar origem HTTPS/IP de cliente.
    server = create_server(app,host='127.0.0.1',port=5000,threads=8,
        trusted_proxy='127.0.0.1',trusted_proxy_headers={'x-forwarded-for','x-forwarded-host','x-forwarded-proto'},
        clear_untrusted_proxy_headers=True,max_request_body_size=512*1024*1024)
    threading.Thread(target=server.run,daemon=True).start()
    try:
        iniciar_verificacao_notificacoes(app)
        from services.recuperacao_local import RecuperacaoDesktop
        from webview.menu import Menu, MenuAction
        recovery = RecuperacaoDesktop(app.extensions['secrets'])
        app.extensions['desktop_recovery'] = recovery
        window = webview.create_window('BIBI — Biblioteca Inteligente','http://127.0.0.1:5000',width=1366,height=768,resizable=True)
        def alternar_tela_cheia():
            window.toggle_fullscreen()
        window.expose(alternar_tela_cheia)
        def bind_shortcuts():
            window.evaluate_js(FULLSCREEN_SHORTCUT)
        window.events.loaded += bind_shortcuts
        def recover():
            token = recovery.abrir()
            window.load_url('http://127.0.0.1:5000/recuperacao-local#' + token)
        webview.start(menu=[
            Menu('Conta', [MenuAction('Recuperar conta bibliotecária neste computador', recover)]),
            Menu('Exibir', [MenuAction('Tela cheia (F11)', alternar_tela_cheia)]),
        ])
    finally:
        server.close()
