"""Opcional: NÃO faz parte do discover. Somente com autorização explícita na CLI."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from services.ai.providers import Provider, PROVIDERS, ProviderError
from services.ai.runtime import config

def main():
    parser=argparse.ArgumentParser(description='Teste real pode consumir créditos. Nenhum dado de aluno é enviado.')
    parser.add_argument('--autorizar-consumo',action='store_true',required=True)
    parser.add_argument('--provedor',choices=PROVIDERS,required=True)
    parser.add_argument('--modelo',required=True)
    parser.add_argument('--data-dir',required=True)
    args=parser.parse_args()
    app=create_app({'DATA_DIR':args.data_dir})
    with app.app_context():
        if not config()['ativa']:
            parser.error('IA globalmente desativada; nenhuma chamada foi realizada.')
        key=app.extensions['secrets'].get('ia_'+args.provedor)
        if not key:parser.error('Provedor sem credencial salva; nenhuma chamada foi realizada.')
        try:
            provider=Provider(args.provedor,key)
            available={row['id'] for row in provider.models()}
            if args.modelo not in available:parser.error('Modelo não listado para esta chave.')
            result=''.join(provider.stream(args.modelo,'Responda apenas OK.',[{'role':'user','content':'Teste técnico de conexão, sem dados pessoais.'}],128))
            if not result:raise ProviderError('Resposta vazia.')
            print('Conectividade e geração reais confirmadas neste instante para',args.provedor,args.modelo)
        except ProviderError as error:
            print('Falha:',error);return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
