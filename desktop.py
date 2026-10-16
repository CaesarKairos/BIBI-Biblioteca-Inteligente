"""Servidor WSGI local e janela desktop; rede requer configuração explícita."""
import threading
from waitress import create_server


DESKTOP_SHORTCUTS = """
(() => {
    if (window.__bibiDesktopShortcuts) return;
    window.__bibiDesktopShortcuts = true;
    let pending = false;
    let altOnly = false;
    document.addEventListener('keydown', event => {
        if (event.key === 'Alt' && !event.ctrlKey && !event.metaKey) {
            event.preventDefault();
            if (!event.repeat) altOnly = true;
            return;
        }
        altOnly = false;
        if (event.key !== 'F11' || event.ctrlKey || event.altKey || event.metaKey) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        if (event.repeat || pending) return;
        pending = true;
        window.pywebview.api.alternar_tela_cheia()
            .catch(() => console.error('Não foi possível alternar a tela cheia.'))
            .finally(() => { pending = false; });
    }, true);
    document.addEventListener('keyup', event => {
        if (event.key !== 'Alt') return;
        if (altOnly) {
            event.preventDefault();
            window.pywebview.api.alternar_menu();
        }
        altOnly = false;
    }, true);
    window.addEventListener('blur', () => { altOnly = false; });
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
        def update_menu(toggle=False):
            # Recovery remains a native action; JS can only show or hide the menu.
            from System import Action
            from System.Windows.Forms import MenuStrip
            def update():
                for control in window.native.Controls:
                    if isinstance(control, MenuStrip):
                        if not toggle:
                            control.MenuDeactivate += lambda sender, args: setattr(sender,'Visible',False)
                        control.Visible = not control.Visible if toggle else False
            if window.native.InvokeRequired:
                window.native.Invoke(Action(update))
            else:
                update()
        def alternar_menu():
            update_menu(toggle=True)
        window.expose(alternar_tela_cheia, alternar_menu)
        window.events.before_show += update_menu
        def bind_shortcuts():
            window.evaluate_js(DESKTOP_SHORTCUTS)
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
