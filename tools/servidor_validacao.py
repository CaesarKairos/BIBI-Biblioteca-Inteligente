"""Servidor de demonstração em loopback; exige pasta separada da instalação real."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from config import DATA_DIR
from app import create_app
from waitress import serve


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--data-dir',type=Path,required=True)
    parser.add_argument('--port',type=int,required=True)
    args=parser.parse_args()
    if args.data_dir.resolve()==Path(DATA_DIR).resolve():
        raise RuntimeError('A validação exige uma pasta diferente da instalação real.')
    serve(create_app({'DATA_DIR':str(args.data_dir.resolve()),'LAN_ENABLED':False}),host='127.0.0.1',port=args.port,threads=8)
