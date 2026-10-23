"""Verifica capas reais com conta sintética, sem abrir a aplicação/banco privado.

Lê somente os campos de Livros e copia as capas para uma instalação descartável.
Não salva imagens ou o catálogo nas evidências públicas.
"""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import threading
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from tests.support import authenticate, HASH
from waitress import create_server
from playwright.sync_api import sync_playwright


def main():
    source=Path(os.environ['LOCALAPPDATA'])/'BIBI'
    conn=sqlite3.connect((source/'Biblioteca.db').as_uri()+'?mode=ro',uri=True)
    rows=conn.execute('SELECT id,isbn,nome,autor,capa_url,estoque,quantidade_disponivel FROM Livros WHERE arquivado=0').fetchall()
    conn.close()
    with tempfile.TemporaryDirectory(prefix='bibi-capas-browser-') as work:
        root=Path(work)
        app=create_app({'TESTING':True,'DATA_DIR':work})
        with app.extensions['database'].connection() as conn:
            conn.execute("INSERT INTO Contas(id,nome,email,senha_hash,papel,ativacao,onboarding_concluido_em) VALUES (1,'Teste','test@example.test',?,'bibliotecario','inicial',CURRENT_TIMESTAMP)",(HASH,))
            conn.executemany('INSERT INTO Livros(id,isbn,nome,autor,capa_url,estoque,quantidade_disponivel) VALUES (?,?,?,?,?,?,?)',rows)
            conn.commit()
        for _,_,_,_,url,_,_ in rows:
            for folder in ('uploadedcovers','externalcovers'):
                if (url or '').startswith('/'+folder+'/'):
                    path=source/folder/Path(url).name
                    if path.is_file():shutil.copy2(path,root/folder/path.name)
        server=create_server(app,host='127.0.0.1',port=0,threads=8)
        thread=threading.Thread(target=server.run,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.effective_port}'
        with app.app_context():
            client=authenticate(app,app.test_client())
            cookie=client.get_cookie('session').value
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch()
                context=browser.new_context(viewport={'width':1366,'height':768})
                context.add_cookies([{'name':'session','value':cookie,'url':base}])
                page=context.new_page();page.goto(base+'/app')
                page.locator('.book').first.wait_for()
                results=page.evaluate('''async rows=>{
                    const result=[];
                    for(const [id,isbn,titulo,autor,url] of rows){
                        if(!url){result.push({id,titulo,estado:'sem referência'});continue;}
                        const image=new Image();const state=await new Promise(resolve=>{
                            const timeout=setTimeout(()=>resolve('timeout'),12000);
                            image.onload=()=>{clearTimeout(timeout);resolve(Math.min(image.naturalWidth,image.naturalHeight)>=40?'renderizada':'placeholder remoto');};
                            image.onerror=()=>{clearTimeout(timeout);resolve('erro no navegador');};image.src=url;
                        });result.push({id,titulo,estado:state});
                    }return result;
                }''',rows)
                # Exercita a função usada tanto no catálogo quanto nos detalhes.
                for bid in (rows[0][0],44,53):
                    page.goto(base+f'/app?livro={bid}')
                    page.locator('#det-titulo').wait_for()
                    page.wait_for_function("!getComputedStyle(document.querySelector('#det-capa')).backgroundImage.includes('placeholder')&&getComputedStyle(document.querySelector('#det-capa')).backgroundImage!=='none'")
                browser.close()
            report={'banco':'temporário; somente campos bibliográficos e arquivos de capas; conta sintética', 'total':len(rows),'renderizadas':sum(r['estado']=='renderizada' for r in results),'pendencias':[r for r in results if r['estado']!='renderizada'],'detalhes':'Primeira obra, ID 44 e ID 53: capas renderizadas sem placeholder.'}
            Path('docs/validacao/capas-navegador.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(report,ensure_ascii=False),flush=True)
        finally:
            server.close();thread.join(timeout=3)


if __name__=='__main__':main()
