"""Valida e compacta a distribuição onedir completa, sem dados da instalação."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from version import VERSION


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('dist/release'))
    args=parser.parse_args();root=args.build.resolve()
    required=['BIBI.exe','_internal/templates/app.html','_internal/static/js/livros.js','_internal/static/vendor/nunito/Nunito.ttf','_internal/database/schema.sql','_internal/dicebear_schema/definition.json','_internal/dicebear_schema/options.json','_internal/LICENSE']
    for name in required:
        if not (root/name).is_file():raise RuntimeError('Arquivo obrigatório ausente: '+name)
    if len(list((root/'_internal/database/migrations').glob('*.sql')))<6:raise RuntimeError('Migrações ausentes.')
    data=(root/'BIBI.exe').read_bytes()
    pe=struct.unpack_from('<I',data,0x3c)[0]
    if data[:2]!=b'MZ' or data[pe:pe+4]!=b'PE\0\0' or struct.unpack_from('<H',data,pe+4)[0]!=0x8664:
        raise RuntimeError('O executável não é um PE Windows x64 válido.')
    paths=sorted(path for path in root.rglob('*') if path.is_file())
    for path in paths:
        rel=path.relative_to(root)
        if path.is_symlink() or path.suffix.lower() in ('.db','.sqlite','.sqlite3','.dpapi','.log') or path.name in ('.env','servidor.pem','servidor.key.pem','BIBI-rede-local.crt'):
            raise RuntimeError('Arquivo de instalação/segredo inesperado: '+str(rel))
        if any(part in ('uploadedcovers','externalcovers') for part in rel.parts) and path.name!='placeholder.png':
            raise RuntimeError('Capa do catálogo não pode acompanhar a distribuição: '+str(rel))
    args.output.mkdir(parents=True,exist_ok=True)
    archive=args.output/f'BIBI-{VERSION}-Windows-x64-Portatil.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in paths:z.write(path,'BIBI/'+path.relative_to(root).as_posix())
        z.writestr('BIBI/LEIA-ME.txt',f'BIBI — Biblioteca Inteligente {VERSION}\n\nExtraia toda a pasta BIBI e abra BIBI.exe. Mantenha _internal ao lado do executável.\nRequer Windows 10/11 x64 e Microsoft Edge WebView2.\nCadastre a instituição e a primeira conta na abertura.\nDados persistentes: %LOCALAPPDATA%\\BIBI. Faça backup pelas Configurações.\nOutros dispositivos usam o HTTPS da rede local com o computador servidor ligado.\nIA opcional: configure e verifique os serviços na aplicação.\nLicença proprietária de uso gratuito nas condições de LICENSE.\nGuia: https://github.com/CaesarKairos/BIBI-Biblioteca-Inteligente\n')
    with archive.open('rb') as source:digest=hashlib.file_digest(source,'sha256').hexdigest()
    (args.output/'SHA256SUMS.txt').write_text(f'{digest}  {archive.name}\n',encoding='utf-8')
    report={'versao':VERSION,'formato':'Windows PE x64 / PyInstaller onedir','arquivos':len(paths),'pacote':archive.name,'bytes':archive.stat().st_size,'sha256':digest,'bancos_e_segredos':'ausentes','capas_do_catalogo':'ausentes; apenas placeholders da interface','schema_avatar':'incluído','migracoes':'incluídas'}
    Path('docs/validacao/distribuicao-pacote.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
