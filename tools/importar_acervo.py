"""Preview by default; --aplicar adds only catalog and covers to the chosen installation."""
import argparse
import json
from pathlib import Path
import socket
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from config import DATA_DIR
from services.importacao_acervo import import_catalog


def main():
    parser=argparse.ArgumentParser(description='Importar catálogo legado sem substituir contas ou histórico. Feche a BIBI antes de aplicar.')
    parser.add_argument('--zip',required=True,type=Path)
    parser.add_argument('--destino',type=Path,default=Path(DATA_DIR))
    parser.add_argument('--aplicar',action='store_true')
    args=parser.parse_args()
    if args.aplicar and args.destino.resolve()==Path(DATA_DIR).resolve():
        with socket.socket() as sock:
            sock.settimeout(1)
            if sock.connect_ex(('127.0.0.1',5000))==0:parser.error('Feche a BIBI na bandeja antes de importar na instalação local.')
    result=import_catalog(args.zip,args.destino,args.aplicar)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
