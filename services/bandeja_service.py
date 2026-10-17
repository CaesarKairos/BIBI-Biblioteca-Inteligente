"""Ciclo de vida da janela Windows separado do servidor da biblioteca."""
import os


class DesktopTray:
    def __init__(self, app, window):
        self.app=app
        self.window=window
        self.icon=None
        self.exiting=False

    def install(self):
        if os.name!='nt' or not self.app.config.get('DESKTOP_TRAY',True):
            return
        try:
            from System.Drawing import Icon
            from System.Windows.Forms import NotifyIcon,ContextMenuStrip,ToolStripMenuItem
            from config import STATIC_DIR
            from pathlib import Path
            icon=NotifyIcon()
            icon.Icon=Icon(str(Path(STATIC_DIR)/'images'/'icon.ico'))
            icon.Text='BIBI — servidor da biblioteca'
            menu=ContextMenuStrip()
            for title,action in [('Abrir BIBI',self.show),('Copiar endereço da rede',self.copy_address),('Encerrar BIBI e servidor',self.exit)]:
                item=ToolStripMenuItem(title)
                item.Click+=lambda sender,args,action=action:action()
                menu.Items.Add(item)
            icon.ContextMenuStrip=menu
            icon.DoubleClick+=lambda sender,args:self.show()
            icon.Visible=True
            self.icon=icon
            self.app.extensions['desktop_tray']=self
        except Exception:
            self.app.logger.exception('Bandeja indisponível; fechar a janela encerrará o servidor')

    def show(self):
        self.window.show()
        self.window.restore()

    def copy_address(self):
        from System.Windows.Forms import Clipboard
        addresses=self.app.extensions['network_runtime'].status()['enderecos']
        if addresses:
            Clipboard.SetText(addresses[0]['url'])

    def closing(self):
        if self.icon and not self.exiting:
            self.window.hide()
            return False
        return True

    def hide(self):
        if self.icon:
            self.window.hide()
        else:
            self.window.minimize()

    def exit(self):
        self.exiting=True
        self.dispose()
        self.window.destroy()

    def dispose(self):
        if self.icon:
            self.icon.Visible=False
            self.icon.Dispose()
            self.icon=None
        self.app.extensions.pop('desktop_tray',None)
