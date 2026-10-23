"""Prepara somente release em rascunho usando a autenticação Git existente.

Nunca imprime tokens. Não publica releases, não sobrescreve tags e não altera branches.
"""
import argparse
import json
from pathlib import Path
import subprocess
import requests


REPO='CaesarKairos/BIBI-Biblioteca-Inteligente'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--version',default='1.1.0')
    parser.add_argument('--notes',type=Path)
    parser.add_argument('--asset',type=Path,action='append',default=[])
    parser.add_argument('--inspect',action='store_true')
    args=parser.parse_args()
    credential=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',capture_output=True,text=True,check=True)
    values=dict(line.split('=',1) for line in credential.stdout.splitlines() if '=' in line)
    token=values.get('password')
    if not token:raise RuntimeError('A autenticação Git não forneceu uma credencial.')
    session=requests.Session()
    session.headers.update({'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
    base=f'https://api.github.com/repos/{REPO}'
    def api(method,path,**kwargs):
        response=session.request(method,base+path,timeout=120,**kwargs)
        if not response.ok:raise RuntimeError(f'GitHub {method} {path}: HTTP {response.status_code}')
        return response.json() if response.content else None
    releases=api('GET','/releases?per_page=100')
    if args.inspect:
        print(json.dumps({'releases':[{'id':r['id'],'tag':r['tag_name'],'nome':r['name'],'draft':r['draft'],'url':r['html_url']} for r in releases],'prs':[{'numero':r['number'],'branch':r['head']['ref']} for r in api('GET','/pulls?state=open&per_page=100')],'branches':[r['name'] for r in api('GET','/branches?per_page=100')]},ensure_ascii=False,indent=2))
        return
    if not args.notes:parser.error('--notes é obrigatório para preparar o rascunho.')
    tag='v'+args.version
    commit=api('GET','/git/ref/tags/'+tag)['object']['sha']
    main=api('GET','/git/ref/heads/main')['object']['sha']
    if commit!=main:raise RuntimeError('A tag precisa apontar diretamente para o commit final da main.')
    existing=[r for r in releases if r['tag_name']==tag]
    if len(existing)>1:raise RuntimeError('Há mais de uma release para a tag; revisão necessária.')
    if existing and not existing[0]['draft']:raise RuntimeError('A versão já foi publicada; não será alterada.')
    payload={'tag_name':tag,'target_commitish':main,'name':'BIBI — Biblioteca Inteligente '+args.version,'body':args.notes.read_text(encoding='utf-8-sig'),'draft':True,'prerelease':False}
    release=api('PATCH',f"/releases/{existing[0]['id']}",json=payload) if existing else api('POST','/releases',json=payload)
    for path in args.asset:
        if not path.is_file():raise RuntimeError('Artefato ausente: '+str(path))
        # Só troca um asset no rascunho autorizado da mesma versão.
        for asset in release.get('assets',[]):
            if asset['name']==path.name:api('DELETE',f"/releases/assets/{asset['id']}")
        url=release['upload_url'].split('{')[0]
        with path.open('rb') as source:
            response=session.post(url,params={'name':path.name},data=source,headers={'Content-Type':'application/octet-stream'},timeout=600)
        if response.status_code!=201:raise RuntimeError(f'Upload {path.name}: HTTP {response.status_code}')
    final=api('GET',f"/releases/{release['id']}")
    if not final['draft']:raise RuntimeError('A release perdeu o estado de rascunho.')
    print(json.dumps({'id':final['id'],'url':final['html_url'],'tag':tag,'commit':main,'draft':final['draft'],'assets':[{'name':a['name'],'bytes':a['size']} for a in final['assets']]},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
