"""Confirma a tela inicial no WebView2 do executável real, em dados descartáveis."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psutil
from tools.processos_validacao import stop_process_tree


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--exe',required=True,type=Path)
    parser.add_argument('--report',type=Path,default=Path('docs/validacao/distribuicao-janela-exe.json'))
    args=parser.parse_args()
    import clr
    framework=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/WPF'
    for name in ('UIAutomationClient.dll','UIAutomationTypes.dll'):
        clr.AddReference(str(framework/name))
    from System.Windows.Automation import AutomationElement,TreeScope,PropertyCondition,Condition
    from System import Int32
    with tempfile.TemporaryDirectory(prefix='bibi-janela-exe-') as work:
        env=os.environ.copy();env['LOCALAPPDATA']=work
        for name in ('BIBI_DESKTOP_PORT','BIBI_LAN_PORT'):
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0));env[name]=str(sock.getsockname()[1])
        process=subprocess.Popen([str(args.exe.resolve())],env=env)
        result={'janela':False,'conteudo_webview':False}
        try:
            for _ in range(30):
                pids=[process.pid]+[p.pid for p in psutil.Process(process.pid).children(recursive=True)]
                for pid in pids:
                    windows=AutomationElement.RootElement.FindAll(TreeScope.Children,PropertyCondition(AutomationElement.ProcessIdProperty,Int32(pid)))
                    for window in windows:
                        if 'BIBI' not in window.Current.Name:continue
                        result['janela']=True
                        elements=window.FindAll(TreeScope.Descendants,Condition.TrueCondition)
                        if any('Vamos preparar sua biblioteca' in element.Current.Name for element in elements):
                            result['conteudo_webview']=True
                if result['conteudo_webview']:break
                time.sleep(1)
            args.report.parent.mkdir(parents=True,exist_ok=True)
            args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(result,ensure_ascii=False))
            assert result['conteudo_webview'],'Conteúdo da janela nativa não foi confirmado.'
        finally:stop_process_tree(process)


if __name__=='__main__':main()
