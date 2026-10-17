"""Gestão de políticas, contas, reservas, moderação e saúde; sempre administrativa."""
import json
import shutil
import time
from pathlib import Path
from urllib.parse import urlsplit
from flask import Blueprint,request,jsonify,current_app,g,send_file,Response,redirect
from werkzeug.exceptions import BadRequest,NotFound
from database.database import db_manager
from services.contas_service import auditar,limitar
from services.circulacao_service import regras,cancelar_reserva,notificar,distribuir
from routes.perfil import records
from utils.auth import admin_required

bp=Blueprint('gestao',__name__)


@bp.get('/api/gestao/rede')
@admin_required
def network_status():
    network=current_app.extensions.get('network_runtime')
    if not network:
        return jsonify(ativo=False,enderecos=[],erro='Servidor de rede não iniciado. Abra o BIBI pelo aplicativo desktop.',certificado_sha256=None,bandeja=False)
    return jsonify(network.status())


@bp.post('/api/gestao/rede/diagnostico')
@admin_required
def network_diagnose():
    network=current_app.extensions.get('network_runtime')
    if not network:
        raise BadRequest('Servidor de rede não iniciado nesta execução.')
    return jsonify(network.diagnose())


@bp.get('/api/gestao/rede/certificado')
@admin_required
def network_certificate():
    network=current_app.extensions.get('network_runtime')
    if not network or not network.certificates or not network.certificates.ca_path.exists():
        raise BadRequest('Certificado de rede ainda não disponível.')
    return send_file(network.certificates.ca_path,as_attachment=True,download_name='BIBI-rede-local.crt',mimetype='application/x-x509-ca-cert')


@bp.get('/api/gestao/csv/modelo/<kind>')
def csv_template(kind):
    from services.dados_service import FIELDS
    if kind not in FIELDS:
        raise BadRequest('Tipo inválido.')
    return Response('\ufeff'+';'.join(FIELDS[kind])+'\r\n',mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename="modelo-{kind}.csv"'})


@bp.post('/api/gestao/csv/<kind>/<action>')
def csv_action(kind,action):
    from services.dados_service import csv_preview,csv_import
    data=request.get_json()
    if action=='previa':
        return jsonify(csv_preview(data.get('conteudo'),kind,data.get('mapeamento')))
    if action=='importar' and data.get('confirmado') is True:
        return jsonify(csv_import(data.get('conteudo'),kind,data.get('mapeamento')))
    raise BadRequest('Confira a prévia e confirme a importação.')


@bp.get('/api/gestao/exportar/emprestimos')
def csv_export():
    from services.dados_service import export_loans
    return Response(export_loans(request.args),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename="emprestimos.csv"'})


@bp.post('/api/gestao/backup')
def create_backup():
    from services.dados_service import backup
    path=backup()
    return send_file(path,as_attachment=True,download_name=path.name)


@bp.post('/api/gestao/restaurar')
def restore_backup():
    from services.dados_service import restore,validate_backup
    from utils.auth import local_only
    local_only()
    upload=request.files.get('arquivo')
    if not upload:
        raise BadRequest('Selecione um backup.')
    if request.form.get('confirmado')!='true':
        archive,manifest=validate_backup(upload.stream);archive.close()
        return jsonify(mensagem='Formato e hashes válidos. A confirmação substituirá os dados atuais e encerrará sessões.',arquivos=len(manifest['arquivos']))
    from utils.auth import verificar_senha_admin
    if not verificar_senha_admin(request.form.get('senha_atual')):
        from werkzeug.exceptions import Forbidden
        raise Forbidden('Confirme a senha atual da sua conta bibliotecária.')
    return jsonify(restore(upload.stream))


@bp.before_request
@admin_required
def protect():
    pass


@bp.get('/gestao')
def page():
    return redirect('/configuracoes#gestao-config')


@bp.route('/api/gestao/configuracao',methods=['GET','PUT'])
def settings():
    keys=('biblioteca_nome','smtp_host','smtp_port','endereco_rede','termos_uso','aviso_privacidade')
    with db_manager.connection() as conn:
        if request.method=='GET':
            values=dict(conn.execute('SELECT chave,valor FROM Configuracoes'))
            return jsonify({key:values.get(key,'') for key in keys} | {'circulacao':regras(conn)})
        data=request.get_json()
        if 'smtp_host' in data or 'smtp_port' in data:
            raise BadRequest('Salve o remetente pelo formulário de E-mail em Configurações.')
        if 'endereco_rede' in data:
            previous=conn.execute("SELECT valor FROM Configuracoes WHERE chave='endereco_rede'").fetchone()
            if data['endereco_rede'] != (previous[0] if previous else ''):
                from utils.auth import verificar_senha_admin
                from werkzeug.exceptions import Forbidden
                if not verificar_senha_admin(data.get('senha_atual')):
                    raise Forbidden('Confirme sua senha atual para alterar a origem de acesso na rede.')
        for key in keys:
            if key not in data:
                continue
            value=data[key]
            if not isinstance(value,str) or len(value)>12000:
                raise BadRequest('Configuração inválida.')
            if key=='endereco_rede' and value:
                url=urlsplit(value)
                if url.scheme!='https' or not url.hostname or url.hostname in ('localhost','127.0.0.1','::1') or url.username or url.password or url.path not in ('','/') or url.query or url.fragment:
                    raise BadRequest('Informe a origem HTTPS da instalação na rede escolar, sem caminho. Configure TLS na infraestrutura da escola.')
            if key=='smtp_port' and value not in ('465','587'):
                raise BadRequest('Use SMTP TLS na porta 465 ou STARTTLS na porta 587.')
            if key=='smtp_host' and (not value or '/' in value or any(c.isspace() for c in value)):
                raise BadRequest('Servidor SMTP inválido.')
            conn.execute('INSERT OR REPLACE INTO Configuracoes VALUES (?,?)',(key,value.strip()))
        if 'circulacao' in data:
            policies=data['circulacao']
            if not isinstance(policies,dict):
                raise BadRequest('Regras de circulação inválidas.')
            for category in ('estudante','professor'):
                rule=policies.get(category,{})
                if not isinstance(rule,dict):
                    raise BadRequest('Regras da categoria inválidas.')
                for key,low,high in [('maximo',1,100),('prazo',1,365),('renovacoes',0,20)]:
                    if type(rule.get(key)) is not int or not low<=rule[key]<=high:
                        raise BadRequest('Limites de circulação inválidos.')
                if type(rule.get('bloquear_atraso')) is not bool:
                    raise BadRequest('Defina o tratamento de atrasos.')
            if type(policies.get('retirada_horas')) is not int or not 1<=policies['retirada_horas']<=720:
                raise BadRequest('Prazo de retirada deve ser de 1 a 720 horas.')
            conn.execute("INSERT OR REPLACE INTO Configuracoes VALUES ('circulacao',?)",(json.dumps(policies),))
        auditar(conn,'configuracao','biblioteca')
        conn.commit()
    return jsonify(status='ok')


@bp.post('/api/gestao/email/testar')
def test_email():
    from services.mensagens_service import enviar
    limitar('teste_smtp',str(g.conta['id']),limite=4,janela=3600)
    success=enviar(g.conta['email'],'BIBI — Teste de remetente','Conexão, autenticação e envio de teste solicitados na biblioteca. Confirme se esta mensagem chegou à sua caixa de entrada.')
    with db_manager.connection() as conn:
        auditar(conn,'teste_smtp','remetente',resultado='aceito' if success else 'falha');conn.commit()
    if not success:
        raise BadRequest('Não foi possível conectar, autenticar ou enviar. Confira o remetente e a senha de aplicativo.')
    return jsonify(mensagem='Conexão, autenticação e envio aceitos pelo SMTP. Confira a caixa de entrada; aceitação não comprova entrega.')


@bp.get('/api/gestao/reservas')
def reservations():
    with db_manager.connection() as conn:
        return jsonify(records(conn,'SELECT r.*,u.nome AS leitor,l.nome AS livro FROM Reservas r JOIN Usuarios u ON u.id=r.leitor_id JOIN Livros l ON l.id=r.livro_id ORDER BY r.criada_em,r.id'))


@bp.delete('/api/gestao/reservas/<int:id>')
def cancel(id):
    return jsonify(cancelar_reserva(id))


@bp.get('/api/gestao/renovacoes')
def requests_renewal():
    with db_manager.connection() as conn:
        return jsonify(records(conn,"SELECT p.id,p.emprestimo_id,u.nome AS leitor,l.nome AS livro FROM PedidosRenovacao p JOIN Emprestimo e ON e.id=p.emprestimo_id JOIN Usuarios u ON u.id=e.usuarios_id JOIN Livros l ON l.id=e.livros_id WHERE p.estado='pendente' ORDER BY p.id"))


@bp.post('/api/gestao/renovacoes/<int:id>/recusar')
def decline(id):
    reason=str(request.get_json().get('motivo','')).strip()
    if not reason:
        raise BadRequest('Informe o motivo.')
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute("SELECT e.usuarios_id FROM PedidosRenovacao p JOIN Emprestimo e ON e.id=p.emprestimo_id WHERE p.id=? AND p.estado='pendente'",(id,)).fetchone()
        if not row:
            raise NotFound('Pedido pendente não encontrado.')
        conn.execute("UPDATE PedidosRenovacao SET estado='recusado',motivo=? WHERE id=?",(reason[:500],id))
        notificar(conn,row[0],f'renovacao-recusada:{id}','Pedido de renovação recusado: '+reason[:500])
        auditar(conn,'recusar_renovacao',id,motivo=reason[:500]);conn.commit()
    return jsonify(status='ok')


@bp.get('/api/gestao/avaliacoes')
def moderation():
    with db_manager.connection() as conn:
        return jsonify(records(conn,'SELECT a.*,l.nome AS livro FROM Avaliacoes a JOIN Livros l ON l.id=a.livro_id ORDER BY a.atualizada_em DESC LIMIT 200'))


@bp.put('/api/gestao/avaliacoes/<int:id>')
def moderate(id):
    data=request.get_json();state=data.get('estado');reason=str(data.get('motivo','')).strip()
    if state not in ('publicado','oculto','revisao') or not reason:
        raise BadRequest('Informe estado e motivo da moderação.')
    with db_manager.connection() as conn:
        row=conn.execute('SELECT leitor_id FROM Avaliacoes WHERE id=?',(id,)).fetchone()
        if not row:
            raise NotFound()
        conn.execute('UPDATE Avaliacoes SET estado=?,motivo=? WHERE id=?',(state,reason[:500],id))
        notificar(conn,row[0],f'moderacao:{id}:{time.time_ns()}',f'Sua avaliação foi moderada: {state}. Motivo: {reason[:500]}')
        auditar(conn,'moderar',id,motivo=reason[:500]);conn.commit()
    return jsonify(status='ok')


@bp.post('/api/gestao/ocorrencias')
def occurrence():
    data=request.get_json();kind=data.get('tipo');qty=data.get('quantidade');book=data.get('livro_id');loan=data.get('emprestimo_id');reason=str(data.get('observacao','')).strip()
    if kind not in ('observacao','reparo','baixa','perda','retorno_reparo') or type(qty) is not int or qty<=0 or not reason:
        raise BadRequest('Informe tipo, quantidade positiva e observação.')
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT estoque,quantidade_disponivel FROM Livros WHERE id=?',(book,)).fetchone()
        if not row:
            raise NotFound('Livro não encontrado.')
        if loan:
            emp=conn.execute("SELECT usuarios_id,quantidade FROM Emprestimo WHERE id=? AND livros_id=? AND status IN ('Aprovado','Atrasado') AND encerramento IS NULL",(loan,book)).fetchone()
            if not emp or kind not in ('perda','observacao') or qty>emp[1] or (kind=='perda' and qty!=emp[1]):
                raise BadRequest('Vincule uma observação ao empréstimo ativo ou registre a perda de sua quantidade integral.')
            if kind=='perda':
                conn.execute("UPDATE Emprestimo SET encerramento='Perdido' WHERE id=?",(loan,))
                conn.execute('UPDATE Livros SET estoque=estoque-? WHERE id=?',(qty,book))
                conn.execute("UPDATE PedidosRenovacao SET estado='cancelado',motivo='Perda registrada' WHERE emprestimo_id=? AND estado='pendente'",(loan,))
                notificar(conn,emp[0],f'perda:{loan}','O empréstimo foi encerrado como perda, sem devolução ao estoque.')
        elif kind in ('reparo','baixa','perda'):
            if row[1]<qty:
                raise BadRequest('Quantidade maior que o estoque livre. Resolva reservas ou vincule o empréstimo perdido.')
            conn.execute('UPDATE Livros SET quantidade_disponivel=quantidade_disponivel-?,estoque=estoque-? WHERE id=?',(qty,qty if kind in ('baixa','perda') else 0,book))
        elif kind=='retorno_reparo':
            repairs=conn.execute("SELECT COALESCE(SUM(CASE WHEN tipo='reparo' THEN quantidade WHEN tipo='retorno_reparo' THEN -quantidade ELSE 0 END),0) FROM Ocorrencias WHERE livro_id=?",(book,)).fetchone()[0]
            if qty>repairs:
                raise BadRequest('Não há essa quantidade em reparo.')
            conn.execute('UPDATE Livros SET quantidade_disponivel=quantidade_disponivel+? WHERE id=?',(qty,book))
        conn.execute('INSERT INTO Ocorrencias(livro_id,emprestimo_id,tipo,quantidade,observacao,conta_id) VALUES (?,?,?,?,?,?)',(book,loan,kind,qty,reason[:2000],g.conta['id']))
        distribuir(conn,book);auditar(conn,'ocorrencia',book,motivo=kind+': '+reason[:500]);conn.commit()
    return jsonify(status='ok')


@bp.get('/api/gestao/saude')
def health():
    with db_manager.connection() as conn:
        integrity=conn.execute('PRAGMA quick_check').fetchone()[0]
        migrations=records(conn,'SELECT * FROM Migracoes ORDER BY versao')
        emails=records(conn,'SELECT estado,COUNT(*) AS quantidade FROM FilaEmail GROUP BY estado')
    backups=sorted((Path(current_app.config['DATA_DIR'])/'backups').glob('*'),key=lambda p:p.stat().st_mtime)
    worker=current_app.extensions.get('notification_worker')
    return jsonify(banco=integrity,versao='2.0-dev',espaco_livre=shutil.disk_usage(current_app.config['DATA_DIR']).free,
        migracoes=migrations,email=emails,ultimo_backup=backups[-1].name if backups else None,
        worker='executando' if worker and worker.is_alive() else 'não iniciado',metadados=current_app.extensions.get('metadata_health',{'estado':'Nenhuma consulta nesta execução. Fontes consultadas sob demanda.'}),
        rede=(current_app.extensions['network_runtime'].status() if current_app.extensions.get('network_runtime')
              else {'ativo':False,'erro':'Servidor desktop não iniciado nesta execução.'}))


@bp.get('/api/gestao/auditoria')
def audit():
    with db_manager.connection() as conn:
        return jsonify(records(conn,'SELECT id,conta_id,quando,acao,recurso,resultado,motivo FROM Auditoria ORDER BY id DESC LIMIT 200'))


@bp.get('/leitores/contas')
def reader_accounts():
    from urllib.parse import urlencode
    return redirect('/app?'+urlencode({'config':'gestao-convites','leitor':request.args.get('leitor','')}))


@bp.get('/emprestimos/circulacao')
def circulation_page():
    return redirect('/app?config=circulacao')


@bp.get('/acervo/importacao')
@bp.get('/leitores/importacao')
def import_page():
    kind='leitores' if request.path.startswith('/leitores') else 'livros'
    return redirect('/app?config=dados&tipo='+kind)
