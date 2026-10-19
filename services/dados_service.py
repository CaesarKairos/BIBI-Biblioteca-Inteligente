"""CSV explícito e backups consistentes. Nenhum segredo de instalação é exportado."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import sqlite3
import tempfile
import time
import zipfile
from flask import current_app,g
from werkzeug.exceptions import BadRequest
from database.database import db_manager
from services.contas_service import auditar

FIELDS={'livros':['isbn','titulo','autor','quantidade','categoria','localizacao','numero_paginas'],
        'leitores':['nome','tipo','email','sala','periodo','materia','telefone']}


def csv_preview(content,kind,mapping=None):
    if kind not in FIELDS or not isinstance(content,str) or len(content.encode())>2*1024*1024:
        raise BadRequest('CSV inválido ou maior que 2 MB.')
    stream=io.StringIO(content.lstrip('\ufeff'))
    try:
        dialect=csv.Sniffer().sniff(content[:4096],delimiters=',;\t')
    except csv.Error:
        dialect=csv.excel
    reader=csv.DictReader(stream,dialect=dialect)
    if not reader.fieldnames:
        raise BadRequest('CSV sem cabeçalho.')
    mapping=mapping or {key:key for key in FIELDS[kind]}
    if not isinstance(mapping,dict) or any(not isinstance(v,str) for v in mapping.values()):
        raise BadRequest('Mapeamento de colunas inválido.')
    results=[];identities=set()
    with db_manager.connection() as conn:
        from services.configuracoes_service import campos_cadastro
        fields=campos_cadastro(conn)
        location=conn.execute("SELECT valor FROM Configuracoes WHERE chave='obrigar_localizacao_livro'").fetchone()
        require_location=bool(location and location[0].lower()=='true')
        for number,raw in enumerate(reader,2):
            if number>2001:
                raise BadRequest('Importe até 2000 linhas por arquivo.')
            row={key:str(raw.get(mapping.get(key,key)) or '').strip() for key in FIELDS[kind]}
            errors=[]
            if kind=='livros':
                if require_location and not row['localizacao']:
                    errors.append('Informe a localização física exigida pela biblioteca.')
                if not row['titulo'] or not row['autor']:
                    errors.append('Título e autor obrigatórios.')
                try:
                    row['quantidade']=int(row['quantidade']);row['numero_paginas']=int(row['numero_paginas']) if row['numero_paginas'] else None
                    if not 1<=row['quantidade']<=10000 or (row['numero_paginas'] is not None and row['numero_paginas']<=0):
                        raise ValueError()
                except ValueError:
                    errors.append('Quantidade/páginas devem ser inteiros positivos.')
                identity=row['isbn']
                exists=identity and conn.execute('SELECT 1 FROM Livros WHERE isbn=?',(identity,)).fetchone()
                if not identity:
                    # Sem ISBN: sempre um título novo; nunca mesclar por nome.
                    row['isbn']=None
            else:
                if fields.get('campoNumeroUsuario') and row['tipo']=='estudante' and not row['telefone']:
                    errors.append('Informe o telefone do estudante exigido pela biblioteca.')
                if not row['nome'] or row['tipo'] not in ('estudante','professor'):
                    errors.append('Nome e categoria estudante/professor obrigatórios.')
                identity=row['email'].casefold()
                if identity:
                    from services.contas_service import email_normalizado
                    try:
                        row['email']=email_normalizado(identity)
                    except BadRequest:
                        errors.append('E-mail inválido.')
                else:
                    row['email']=None
                exists=identity and conn.execute('SELECT 1 FROM Usuarios WHERE lower(email)=?',(identity,)).fetchone()
            if identity and (identity in identities or exists):
                errors.append('Duplicata: a linha não será importada nem substituirá dados existentes.')
            if identity:
                identities.add(identity)
            results.append({'linha':number,'dados':row,'erros':errors})
    return {'colunas':reader.fieldnames,'campos':FIELDS[kind],'linhas':results}


def csv_import(content,kind,mapping=None):
    # Validação refeita no servidor ao confirmar; transação impede gravação parcial.
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        preview=csv_preview(content,kind,mapping)
        if any(row['erros'] for row in preview['linhas']):
            raise BadRequest('Corrija todas as linhas com erro antes de confirmar.')
        for item in preview['linhas']:
            row=item['dados']
            if kind=='livros':
                conn.execute('INSERT INTO Livros(isbn,nome,autor,estoque,quantidade_disponivel,categoria,localizacao,numero_paginas) VALUES (?,?,?,?,?,?,?,?)',
                    (row['isbn'],row['titulo'],row['autor'],row['quantidade'],row['quantidade'],row['categoria'] or 'Ficção',row['localizacao'],row['numero_paginas']))
            else:
                conn.execute('INSERT INTO Usuarios(nome,tipo,email,sala,periodo,materia,telefone) VALUES (?,?,?,?,?,?,?)',tuple(row[k] for k in FIELDS[kind]))
        auditar(conn,'importar_csv',kind,motivo=f"{len(preview['linhas'])} registros")
        conn.commit()
    return {'importados':len(preview['linhas'])}


def safe_cell(value):
    value='' if value is None else str(value)
    return "'"+value if value.lstrip().startswith(('=','+','-','@','\t','\r','\n')) else value


def export_loans(query):
    start=query.get('inicio') or '0001-01-01';end=query.get('fim') or '9999-12-31';status=query.get('status','')
    with db_manager.connection() as conn:
        output=io.StringIO();writer=csv.writer(output,delimiter=';')
        if query.get('formato')=='agregado':
            cursor=conn.execute('''SELECT substr(e.data_emprestimo,1,7),COALESCE(e.encerramento,e.status),COUNT(*),SUM(e.quantidade)
                FROM Emprestimo e WHERE e.data_emprestimo BETWEEN ? AND ?
                AND (?='' OR COALESCE(e.encerramento,e.status)=?) GROUP BY 1,2 ORDER BY 1,2''',(start,end,status,status))
            writer.writerow(['Mês','Status','Operações de empréstimo','Exemplares emprestados'])
        else:
            cursor=conn.execute('''SELECT e.id,l.nome,u.nome,u.sala,e.data_emprestimo,e.data_vencimento,e.data_devolucao,COALESCE(e.encerramento,e.status),e.quantidade
            FROM Emprestimo e JOIN Livros l ON l.id=e.livros_id JOIN Usuarios u ON u.id=e.usuarios_id
            WHERE e.data_emprestimo BETWEEN ? AND ? AND (?='' OR COALESCE(e.encerramento,e.status)=?) ORDER BY e.data_emprestimo,e.id''',(start,end,status,status))
            writer.writerow(['ID','Livro','Leitor','Turma','Empréstimo','Vencimento','Devolução','Status','Quantidade'])
        writer.writerows([[safe_cell(v) for v in row] for row in cursor.fetchall()])
        auditar(conn,'exportar_emprestimos','csv');conn.commit()
    return '\ufeff'+output.getvalue()


def backup():
    root=Path(current_app.config['DATA_DIR']);target=root/'backups'/f'bibi-{time.time_ns()}.zip'
    with tempfile.TemporaryDirectory(dir=root) as work:
        dbpath=Path(work)/'Biblioteca.db'
        with db_manager.connection() as conn:
            dest=sqlite3.connect(dbpath)
            try:
                conn.backup(dest)
                # Credenciais SMTP já estão fora do banco; sessões/códigos não pertencem à cópia portátil.
                dest.execute('DELETE FROM Sessoes');dest.execute('UPDATE Codigos SET consumido=1');dest.execute('UPDATE Contas SET recuperacao_hash=NULL,versao_sessao=versao_sessao+1');dest.commit()
            finally:
                dest.close()
        files={'Biblioteca.db':dbpath}
        for directory in ('uploadedcovers','externalcovers','avatars'):
            for file in (root/directory).rglob('*'):
                if file.is_file() and not file.is_symlink():
                    files[file.relative_to(root).as_posix()]=file
        manifest={'formato':1,'versao':'2.0-dev','arquivos':{name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in files.items()}}
        with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            for name,file in files.items():
                archive.write(file,name)
            archive.writestr('manifesto.json',json.dumps(manifest))
    with db_manager.connection() as conn:
        auditar(conn,'backup',target.name);conn.commit()
    return target


def validate_backup(upload):
    try:
        archive=zipfile.ZipFile(upload)
        infos=archive.infolist()
        if len(infos)>20000 or sum(i.file_size for i in infos)>512*1024*1024:
            raise BadRequest('Backup excede os limites de restauração (512 MB / 20000 arquivos).')
        names=[i.filename for i in infos]
        if len(set(names))!=len(names):
            raise BadRequest('Backup com entradas duplicadas.')
        for name in names:
            path=PurePosixPath(name)
            if '\\' in name or ':' in name or path.is_absolute() or '..' in path.parts or (name not in ('Biblioteca.db','manifesto.json') and path.parts[0] not in ('uploadedcovers','externalcovers','avatars')):
                raise BadRequest('Caminho inválido no backup.')
        manifest=json.loads(archive.read('manifesto.json'))
        if manifest.get('formato')!=1 or set(manifest['arquivos'])!=set(names)-{'manifesto.json'}:
            raise BadRequest('Manifesto incompatível.')
        for name,hash_value in manifest['arquivos'].items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=hash_value:
                raise BadRequest('Integridade do backup inválida.')
            if name!='Biblioteca.db':
                from services.image_service import validate_image
                if PurePosixPath(name).suffix.lower() not in ('.png','.jpg','.jpeg','.gif','.webp'):
                    raise BadRequest('O backup contém um arquivo persistente não permitido.')
                try:
                    validate_image(archive.read(name))
                except ValueError as error:
                    raise BadRequest('Imagem inválida no backup.') from error
        return archive,manifest
    except (ValueError,KeyError,zipfile.BadZipFile,TypeError) as error:
        raise BadRequest('Arquivo de backup inválido.') from error


def restore(upload):
    archive,manifest=validate_backup(upload)
    root=Path(current_app.config['DATA_DIR'])
    import secrets
    from services.contas_service import digest
    with archive, tempfile.TemporaryDirectory(dir=root) as work:
        stage=Path(work)
        for name in manifest['arquivos']:
            target=stage/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(name))
        source=sqlite3.connect(stage/'Biblioteca.db')
        try:
            if source.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or source.execute('PRAGMA foreign_key_check').fetchall():
                raise BadRequest('Banco do backup não passou na verificação de integridade.')
            with db_manager.connection() as conn:
                expected={r[0] for r in conn.execute('SELECT versao FROM Migracoes')}
            applied={r[0] for r in source.execute('SELECT versao FROM Migracoes')}
            if not applied.issubset(expected):
                raise BadRequest('Versão do backup mais recente ou incompatível com esta instalação.')
            if applied != expected:
                # Preserva a cópia recebida antes de migrar o banco isolado.
                original=root/'backups'/('antes-restauracao-migracao-'+str(time.time_ns())+'.db')
                original.parent.mkdir(exist_ok=True)
                saved=sqlite3.connect(original)
                try:
                    source.backup(saved)
                finally:
                    saved.close()
                source.close()
                from database.database import DatabaseManager
                DatabaseManager(stage/'Biblioteca.db')
                source=sqlite3.connect(stage/'Biblioteca.db')
            admin=source.execute("SELECT id,email FROM Contas WHERE papel='bibliotecario' AND ativa=1 ORDER BY id LIMIT 1").fetchone()
            if not admin:
                raise BadRequest('O backup precisa conter pelo menos um bibliotecário ativo.')
            safety=backup()
            # Backup original exato para rollback; não usa a cópia portátil sanitizada.
            rollback=sqlite3.connect(stage/'rollback.db')
            try:
                with db_manager.connection() as target:
                    target.backup(rollback)
                    source.execute('DELETE FROM Sessoes');source.execute('UPDATE Codigos SET consumido=1');source.execute('UPDATE Contas SET versao_sessao=versao_sessao+1,recuperacao_hash=NULL')
                    source.commit()
                    try:
                        # Arquivos entram antes do banco. Sobras não são servidas por nomes publicados até commit.
                        for name in manifest['arquivos']:
                            if name=='Biblioteca.db':
                                continue
                            dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True)
                            old=stage/'old'/name
                            if dest.exists():
                                old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,old)
                            shutil.copy2(stage/name,dest)
                        source.backup(target)
                        auditar(target,'restaurar',safety.name,ator=g.conta['id']);target.commit()
                    except Exception:
                        rollback.backup(target)
                        for old in (stage/'old').rglob('*') if (stage/'old').exists() else []:
                            if old.is_file():
                                shutil.copy2(old,root/old.relative_to(stage/'old'))
                        raise
            finally:
                rollback.close()
        except sqlite3.DatabaseError as error:
            raise BadRequest('Estrutura do banco de backup inválida ou incompatível.') from error
        finally:
            source.close()
    current_app.extensions['secrets'].set('smtp_password',None)
    from services.ai.providers import PROVIDERS
    for provider in PROVIDERS:
        current_app.extensions['secrets'].set('ia_'+provider,None)
        current_app.extensions['secrets'].set('ia_rascunho_'+provider,None)
    with db_manager.connection() as conn:
        conn.execute("DELETE FROM Configuracoes WHERE chave IN ('ia','ia_rascunho','ia_validacoes')")
        conn.commit()
    current_app.extensions.pop('ai_runtime',None)
    current_app.extensions.pop('ai_recommendations',None)
    current_app.extensions['secrets'].recovery_key(rotate=True)
    if current_app.extensions.get('desktop_recovery'):
        current_app.extensions['desktop_recovery'].pending=None
    return {'mensagem':'Restauração concluída. Sessões e códigos foram invalidados. Entre novamente ou use o menu de recuperação desktop. Reconfigure a credencial SMTP da instalação anterior e revise a rede.','backup_seguranca':safety.name}
