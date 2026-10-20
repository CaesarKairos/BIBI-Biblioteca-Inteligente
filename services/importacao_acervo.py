"""Offline, additive catalog import. Never executes code or imports readers from a ZIP."""
import hashlib
import json
from pathlib import Path,PurePosixPath
import sqlite3
import tempfile
import time
import unicodedata
from urllib.parse import unquote,urlsplit
import zipfile
from database.database import DatabaseManager
from services.image_service import validate_image,MAX_IMAGE_BYTES


def digest(data):
    return hashlib.sha256(data).hexdigest()


def identity(value):
    return ' '.join(unicodedata.normalize('NFKC',value or '').casefold().split())


def inspect(archive):
    archive=Path(archive)
    with archive.open('rb') as source:source_hash=hashlib.file_digest(source,'sha256').hexdigest()
    with zipfile.ZipFile(archive) as z, tempfile.TemporaryDirectory(prefix='bibi-catalogo-origem-') as work:
        databases=[name for name in z.namelist() if PurePosixPath(name).name=='Biblioteca.db']
        if len(databases)!=1:raise ValueError('O ZIP precisa conter exatamente um Biblioteca.db.')
        name=databases[0];info=z.getinfo(name)
        if info.file_size>100*1024*1024:raise ValueError('Banco de origem maior que 100 MB.')
        path=Path(work)/'origem.db';path.write_bytes(z.read(name))
        conn=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True);conn.row_factory=sqlite3.Row
        try:
            if conn.execute('PRAGMA integrity_check').fetchall()[0][0]!='ok':raise ValueError('Banco de origem sem integridade.')
            if conn.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Origem possui referências históricas inválidas.')
            rows=[dict(row) for row in conn.execute('SELECT * FROM Livros ORDER BY id')]
            if len(rows)>10000:raise ValueError('Importe até 10000 obras por arquivo.')
            historic={table:conn.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('Usuarios','Emprestimo','Agendamento') if conn.execute('SELECT 1 FROM sqlite_master WHERE type=? AND name=?',('table',table)).fetchone()}
        finally:conn.close()
        images={};prefix=PurePosixPath(name).parent
        for row in rows:
            if not row.get('nome') or not row.get('autor') or type(row.get('estoque')) is not int or row['estoque']<0:
                raise ValueError('Origem possui título, autoria ou estoque inválido.')
            available=row.get('quantidade_disponivel')
            if type(available) is not int or not 0<=available<=row['estoque']:raise ValueError('Disponibilidade inválida na origem.')
            url=row.get('capa_url') or ''
            parsed=urlsplit(url);part=unquote(parsed.path).replace('\\','/')
            if parsed.scheme or parsed.netloc:raise ValueError('A capa deve existir localmente no ZIP, sem download externo.')
            recognized=False
            for folder in ('uploadedcovers','externalcovers'):
                for beginning in ('/static/images/'+folder+'/', '/'+folder+'/'):
                    if not part.startswith(beginning):continue
                    filename=part[len(beginning):]
                    if not filename or PurePosixPath(filename).name!=filename or ':' in filename or filename in ('.','..'):
                        raise ValueError('Referência de capa insegura.')
                    member=(prefix/'static'/'images'/folder/filename).as_posix()
                    matches=[item for item in z.infolist() if item.filename==member]
                    if len(matches)!=1:raise ValueError('Capa ausente ou ambígua no ZIP para a obra '+str(row['id']))
                    image=matches[0]
                    if image.file_size>MAX_IMAGE_BYTES or (image.external_attr>>16)&0o170000==0o120000:raise ValueError('Imagem excede o limite ou é um link simbólico.')
                    data=z.read(image);extension=validate_image(data)
                    if Path(filename).suffix.lower() not in ('.'+extension,'.jpeg' if extension=='jpg' else '.'+extension):filename=Path(filename).stem+'.'+extension
                    images[row['id']]={'folder':folder,'filename':filename,'bytes':data,'sha256':digest(data)}
                    recognized=True;break
                if recognized:break
            if not recognized:raise ValueError('Referência de capa não reconhecida para a obra '+str(row['id']))
    return {'hash':source_hash,'livros':rows,'capas':images,'historicos_nao_importados':historic}


def backup(root):
    """Raw recovery copy is local only; no credentials are touched or exported."""
    root=Path(root);directory=root/'backups';directory.mkdir(parents=True,exist_ok=True)
    target=directory/f'antes-acervo-{time.time_ns()}.zip'
    with tempfile.TemporaryDirectory(prefix='bibi-backup-acervo-') as work:
        snapshot=Path(work)/'Biblioteca.db'
        source=sqlite3.connect((root/'Biblioteca.db').as_uri()+'?mode=ro',uri=True)
        dest=sqlite3.connect(snapshot)
        try:source.backup(dest)
        finally:dest.close();source.close()
        with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as z:
            z.write(snapshot,'Biblioteca.db')
            for folder in ('uploadedcovers','externalcovers','avatars'):
                for path in (root/folder).rglob('*'):
                    if path.is_file() and not path.is_symlink():z.write(path,path.relative_to(root).as_posix())
    return target


def import_catalog(archive,root,apply=False):
    data=inspect(archive);root=Path(root).resolve();db=root/'Biblioteca.db'
    report={'origem_sha256':data['hash'],'catalogo_origem':len(data['livros']),'capas_origem':len(data['capas']),
        'historicos_nao_importados':data['historicos_nao_importados'],'importados':0,'existentes':0,'conflitos':[],
        'estoque_reconciliado':'Somente catálogo: disponibilidade dos novos títulos igual ao estoque total.'}
    if not apply:return report
    root.mkdir(parents=True,exist_ok=True)
    if db.exists():report['backup']=str(backup(root))
    manager=DatabaseManager(str(db));created=[]
    try:
        with manager.connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            existing=[dict(zip([d[0] for d in cur.description],row)) for cur in [conn.execute('SELECT id,isbn,nome,autor FROM Livros')] for row in cur.fetchall()]
            for row in data['livros']:
                mapped=conn.execute('SELECT livro_id FROM ImportacoesAcervo WHERE origem=? AND origem_id=?',(data['hash'],row['id'])).fetchone()
                match=next((book for book in existing if row.get('isbn') and identity(book['isbn']).replace('-','')==identity(row['isbn']).replace('-','')),None)
                if mapped or match:
                    if match and (identity(match['nome']),identity(match['autor']))!=(identity(row['nome']),identity(row['autor'])):
                        report['conflitos'].append({'origem_id':row['id'],'motivo':'ISBN existente com título ou autoria diferente; preservado.'});continue
                    report['existentes']+=1;continue
                if not row.get('isbn') and any((identity(book['nome']),identity(book['autor']))==(identity(row['nome']),identity(row['autor'])) for book in existing):
                    report['conflitos'].append({'origem_id':row['id'],'motivo':'Possível duplicata sem ISBN; revisão necessária.'});continue
                image=data['capas'][row['id']];folder=root/image['folder']
                if folder.is_symlink():raise ValueError('Pasta persistente de capas não pode ser link simbólico.')
                folder.mkdir(exist_ok=True)
                target=folder/image['filename']
                if target.exists() and (target.is_symlink() or digest(target.read_bytes())!=image['sha256']):
                    target=folder/(Path(image['filename']).stem+'_'+image['sha256']+Path(image['filename']).suffix)
                if target.is_symlink():raise ValueError('Destino da capa é um link simbólico.')
                if not target.exists():
                    with target.open('xb') as out:out.write(image['bytes'])
                    created.append((target,image['sha256']))
                elif digest(target.read_bytes())!=image['sha256']:raise ValueError('Colisão de conteúdo na capa de destino.')
                url='/'+image['folder']+'/'+target.name
                cur=conn.execute('INSERT INTO Livros(isbn,nome,autor,ano_publicacao,capa_url,descricao,temas,categoria,estoque,quantidade_disponivel,data_cadastro,localizacao,numero_paginas) VALUES (?,?,?,?,?,?,?,?,?,?,COALESCE(?,date(\'now\')),?,?)',
                    (row.get('isbn') or None,row['nome'],row['autor'],row.get('ano_publicacao'),url,row.get('descricao'),row.get('temas'),row.get('categoria'),row['estoque'],row['estoque'],row.get('data_cadastro'),row.get('localizacao'),row.get('numero_paginas')))
                conn.execute('INSERT INTO ImportacoesAcervo VALUES (?,?,?)',(data['hash'],row['id'],cur.lastrowid))
                existing.append({'id':cur.lastrowid,'isbn':row.get('isbn'),'nome':row['nome'],'autor':row['autor']});report['importados']+=1
            from services.contas_service import auditar
            auditar(conn,'importar_acervo_legado',data['hash'],motivo=f"{report['importados']} títulos; somente catálogo")
            if conn.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Integridade referencial do destino inválida.')
            conn.commit()
    except Exception:
        for path,signature in created:
            if path.is_file() and path.is_relative_to(root) and digest(path.read_bytes())==signature:path.unlink()
        raise
    report['destino']=str(db);report['capas_associadas']=report['importados']
    manifest=root/'backups'/f'importacao-acervo-{time.time_ns()}.json';manifest.parent.mkdir(exist_ok=True)
    manifest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');report['relatorio_local']=str(manifest)
    return report
