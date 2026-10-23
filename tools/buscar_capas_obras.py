"""Busca candidatos por obra para revisão, sem modificar o banco."""
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import requests


def main():
    report=json.loads(Path('docs/validacao/capas-distribuicao.json').read_text(encoding='utf-8'))
    session=requests.Session()
    session.headers['User-Agent']='BIBI/1.1 (https://github.com/CaesarKairos/BIBI-Biblioteca-Inteligente)'
    results=[]
    for item in report['resultados']:
        # Títulos dos oito registros de teste têm ISBN sem correspondência;
        # busca textual nunca se apresenta como confirmação dessa edição.
        title=item['titulo']
        corrections={'V de Vinganca':'V de Vingança','Batman: Ano Um':'Batman Year One','Sandman Vol. 1':'Sandman Preludes Nocturnes','Sandman Vol. 2':'Sandman Dolls House','Batman: Cavaleiro das Trevas':'Batman Dark Knight Returns','Maus Volume 2':'Maus II','Laços':'Turma da Mônica Laços','Eu':'Eu Augusto dos Anjos'}
        query=corrections.get(title,title)
        try:
            r=session.get('https://openlibrary.org/search.json',params={'q':query,'limit':4,'fields':'key,title,author_name,cover_i,edition_key,isbn,language'},timeout=25)
            r.raise_for_status()
            docs=r.json().get('docs',[])
            results.append({'id':item['id'],'titulo':title,'isbn_cadastrado':item['isbn'],'candidatos':docs})
            print(item['id'],title,[(d.get('title'),d.get('author_name'),d.get('cover_i')) for d in docs],flush=True)
        except requests.RequestException as error:
            results.append({'id':item['id'],'titulo':title,'erro':str(error)})
            print(title,str(error),flush=True)
        time.sleep(1.1)
    Path('docs/validacao/capas-candidatos.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()
