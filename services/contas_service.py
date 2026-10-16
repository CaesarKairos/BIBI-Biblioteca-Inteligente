"""Contas separadas dos leitores; códigos de finalidade única e sessões revogáveis."""
import hashlib
import secrets
import time
import re
from flask import g, request, session, has_request_context,current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import BadRequest, Forbidden, TooManyRequests
from database.database import db_manager


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def email_normalizado(value):
    if not isinstance(value, str):
        raise BadRequest('Informe um e-mail válido.')
    value = value.strip().casefold()
    if len(value) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
        raise BadRequest('Informe um e-mail válido.')
    return value


def senha_validada(data):
    senha = data.get('senha')
    if not isinstance(senha, str) or not 12 <= len(senha) <= 128:
        raise BadRequest('Use uma senha com 12 a 128 caracteres.')
    if senha != data.get('confirmacao'):
        raise BadRequest('As senhas não conferem.')
    return generate_password_hash(senha, method='scrypt')


def auditar(conn, acao, recurso='', resultado='ok', motivo=None, ator=None):
    if ator is None:
        ator = getattr(g, 'conta', None) if has_request_context() else None
        ator = ator['id'] if ator else None
    conn.execute('INSERT INTO Auditoria(conta_id,acao,recurso,resultado,motivo) VALUES (?,?,?,?,?)',
                 (ator, acao, str(recurso), resultado, motivo))


def limitar(operacao, identidade='', limite=8, janela=900):
    now = int(time.time())
    # IP impede tentar muitos destinatários; identidade limita ataques distribuídos.
    keys = [digest(f'{operacao}:ip:{request.remote_addr}')]
    if identidade:
        keys.append(digest(f'{operacao}:id:{identidade}'))
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('DELETE FROM Tentativas WHERE inicio < ?', (now - 86400,))
        for key in keys:
            conn.execute('INSERT INTO Tentativas VALUES (?,1,?) ON CONFLICT(chave) DO UPDATE SET quantidade=CASE WHEN inicio<? THEN 1 ELSE quantidade+1 END, inicio=CASE WHEN inicio<? THEN excluded.inicio ELSE inicio END',
                         (key, now, now - janela, now - janela))
        blocked = any(conn.execute('SELECT quantidade FROM Tentativas WHERE chave=?', (key,)).fetchone()[0] > limite for key in keys)
        conn.commit()
    if blocked:
        raise TooManyRequests('Muitas tentativas. Aguarde e tente novamente.')


def configurado():
    with db_manager.connection() as conn:
        return conn.execute('SELECT 1 FROM Contas LIMIT 1').fetchone() is not None


def conta_atual():
    token = session.get('sid')
    if not isinstance(token, str):
        return None
    with db_manager.connection() as conn:
        cursor = conn.execute('''SELECT c.id,c.leitor_id,c.nome,c.email,c.papel,c.email_verificado,c.ativacao,c.onboarding_concluido_em,c.criada_em
            FROM Sessoes s JOIN Contas c ON c.id=s.conta_id
            LEFT JOIN Usuarios u ON u.id=c.leitor_id
            WHERE s.hash=? AND s.expira>? AND c.ativa=1 AND c.versao_sessao=s.versao''', (digest(token), int(time.time())))
        row = cursor.fetchone()
        return dict(zip([d[0] for d in cursor.description], row)) if row else None


def iniciar_sessao(conta_id):
    token = secrets.token_urlsafe(32)
    with db_manager.connection() as conn:
        row = conn.execute('SELECT versao_sessao FROM Contas WHERE id=? AND ativa=1', (conta_id,)).fetchone()
        if not row:
            raise Forbidden('Conta indisponível.')
        conn.execute('DELETE FROM Sessoes WHERE expira<=?', (int(time.time()),))
        conn.execute('INSERT INTO Sessoes VALUES (?,?,?,?)', (digest(token), conta_id, row[0], int(time.time()) + 8*3600))
        conn.commit()
    session.clear()
    session.update(sid=token, csrf=secrets.token_urlsafe(32))
    session.permanent = True


def configurar(data):
    email = email_normalizado(data.get('email'))
    senha = senha_validada(data)
    nome, biblioteca = str(data.get('nome', '')).strip(), str(data.get('biblioteca', '')).strip()
    if not nome or not biblioteca or max(len(nome), len(biblioteca)) > 180:
        raise BadRequest('Informe o nome da biblioteca e do bibliotecário (até 180 caracteres).')
    from services.termos_service import VERSAO, TERMOS, PRIVACIDADE
    if data.get('aceite') not in (True, 'on') or data.get('termos_versao') != VERSAO:
        raise BadRequest('Leia e aceite os Termos de Uso e o Aviso de Privacidade disponíveis nesta tela.')
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute('SELECT 1 FROM Contas LIMIT 1').fetchone():
            raise Forbidden('A configuração inicial já foi concluída.')
        cur = conn.execute("INSERT INTO Contas(nome,email,senha_hash,papel,ativacao,recuperacao_hash) VALUES (?,?,?,'bibliotecario','inicial',?)", (nome,email,senha,None))
        conn.execute("INSERT OR REPLACE INTO Configuracoes VALUES ('biblioteca_nome',?)", (biblioteca,))
        conn.execute('INSERT INTO AceitesTermos(conta_id,versao) VALUES (?,?)',(cur.lastrowid,VERSAO))
        for key,value in [('termos_uso',TERMOS),('aviso_privacidade',PRIVACIDADE)]:
            conn.execute('INSERT OR IGNORE INTO Configuracoes VALUES (?,?)',(key,value))
        conn.execute("INSERT OR IGNORE INTO Configuracoes VALUES ('instalacao_criada_em',CURRENT_TIMESTAMP)")
        conn.execute("INSERT OR IGNORE INTO Configuracoes VALUES ('instalacao_data_estimada','false')")
        auditar(conn,'configuracao_inicial',cur.lastrowid,ator=cur.lastrowid)
        conn.commit()
        conta_id = cur.lastrowid
    iniciar_sessao(conta_id)
    current_app.extensions['secrets'].recovery_key(rotate=True)
    return {'destino':'/boas-vindas'}


def login(data):
    email = str(data.get('email', '')).strip().casefold()
    limitar('login',email)
    with db_manager.connection() as conn:
        row = conn.execute('SELECT id,senha_hash,ativa FROM Contas WHERE email=?', (email,)).fetchone()
        senha = data.get('senha', '')
        # Mesmo custo adaptativo também quando a conta não existe.
        hashed = row[1] if row else current_app.extensions['dummy_password_hash']
        valid = isinstance(senha,str) and len(senha) <= 128 and check_password_hash(hashed,senha)
        if not row or not row[2] or not valid:
            auditar(conn,'login','',resultado='negado')
            conn.commit()
            raise Forbidden('E-mail ou senha inválidos, ou conta indisponível.')
    iniciar_sessao(row[0])
    return {'status':'ok','destino':'/app'}


def emitir_codigo(leitor_id, finalidade='ativacao', entrega='presencial'):
    limitar('emissao',str(g.conta['id']),limite=30)
    if finalidade not in ('ativacao','recuperacao') or entrega not in ('presencial','email'):
        raise BadRequest('Finalidade ou entrega inválida.')
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    raw = ''.join(secrets.choice(alphabet) for _ in range(16))
    code = '-'.join(raw[i:i+4] for i in range(0,16,4))
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT email FROM Usuarios WHERE id=? AND arquivado=0', (leitor_id,)).fetchone()
        if not row:
            raise BadRequest('Leitor não encontrado.')
        email = email_normalizado(row[0])
        account = conn.execute('SELECT id,email,ativa FROM Contas WHERE leitor_id=?', (leitor_id,)).fetchone()
        if finalidade == 'ativacao' and account:
            raise BadRequest('Este leitor já possui conta.')
        if finalidade == 'recuperacao' and (not account or not account[2]):
            raise BadRequest('A recuperação exige uma conta ativa.')
        if account:
            email = account[1]
        conn.execute('UPDATE Codigos SET consumido=1 WHERE leitor_id=? AND finalidade=?', (leitor_id,finalidade))
        cur = conn.execute('INSERT INTO Codigos(leitor_id,conta_id,email,finalidade,entrega,hash,expira,criado_por) VALUES (?,?,?,?,?,?,?,?)',
                         (leitor_id,account[0] if account else None,email,finalidade,entrega,digest(raw),int(time.time())+86400,g.conta['id']))
        auditar(conn,'emitir_'+finalidade,leitor_id,motivo=entrega)
        conn.commit()
    return {'id':cur.lastrowid,'codigo':code,'email':email,'validade_horas':24,'entrega':entrega}


def consumir_codigo(data, finalidade):
    email = email_normalizado(data.get('email'))
    limitar('codigo',email)
    password = senha_validada(data)
    code = str(data.get('codigo','')).replace('-','').replace(' ','').upper()
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT id,leitor_id,conta_id,entrega FROM Codigos WHERE hash=? AND email=? AND finalidade=? AND consumido=0 AND expira>?',
                           (digest(code),email,finalidade,int(time.time()))).fetchone()
        if not row:
            raise BadRequest('Código inválido, expirado ou já utilizado. Procure a biblioteca.')
        if finalidade == 'ativacao':
            reader = conn.execute('SELECT nome,email FROM Usuarios WHERE id=?', (row[1],)).fetchone()
            if not reader or email_normalizado(reader[1]) != email:
                raise BadRequest('Solicite um novo convite à biblioteca.')
            cur = conn.execute("INSERT INTO Contas(leitor_id,nome,email,senha_hash,papel,email_verificado,ativacao) VALUES (?,?,?,?,'leitor',?,?)",
                               (row[1],reader[0],email,password,int(row[3]=='email'),row[3]))
            account_id = cur.lastrowid
        else:
            account_id = row[2]
            changed = conn.execute('UPDATE Contas SET senha_hash=?,versao_sessao=versao_sessao+1 WHERE id=? AND ativa=1 AND email=?', (password,account_id,email)).rowcount
            if not changed:
                raise BadRequest('Conta indisponível. Procure a biblioteca.')
        conn.execute('UPDATE Codigos SET consumido=1 WHERE id=?', (row[0],))
        auditar(conn,finalidade,account_id,ator=account_id)
        conn.commit()
    if finalidade == 'ativacao':
        iniciar_sessao(account_id)
        return {'status':'ok','destino':'/boas-vindas'}
    return {'status':'ok','mensagem':'Senha definida. Entre com seu e-mail e senha.'}


def recuperar_offline(data):
    email = email_normalizado(data.get('email'))
    limitar('offline',email,limite=5,janela=3600)
    password = senha_validada(data)
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute("SELECT id,recuperacao_hash FROM Contas WHERE email=? AND papel='bibliotecario' AND ativa=1", (email,)).fetchone()
        if not row or not row[1] or not secrets.compare_digest(row[1],digest(str(data.get('codigo','')))):
            raise BadRequest('Dados de recuperação inválidos.')
        conn.execute('UPDATE Contas SET senha_hash=?,recuperacao_hash=?,versao_sessao=versao_sessao+1 WHERE id=?', (password,None,row[0]))
        conn.execute('UPDATE Codigos SET consumido=1 WHERE conta_id=?', (row[0],))
        conn.execute('DELETE FROM Sessoes WHERE conta_id=?',(row[0],))
        auditar(conn,'recuperacao_offline',row[0],ator=row[0])
        conn.commit()
    current_app.extensions['secrets'].recovery_key(rotate=True)
    return {'mensagem':'Código legado consumido. Use a recuperação pelo menu desktop nas próximas vezes. Entre novamente.'}


def alterar_acesso(conta_id,data):
    papel, ativa = data.get('papel'), data.get('ativa')
    if papel not in ('leitor','bibliotecario') or type(ativa) is not bool or not data.get('motivo'):
        raise BadRequest('Informe papel, estado e motivo.')
    with db_manager.connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        actor = conn.execute('SELECT senha_hash FROM Contas WHERE id=?', (g.conta['id'],)).fetchone()
        if not check_password_hash(actor[0],str(data.get('senha_atual',''))):
            raise Forbidden('Confirme sua senha para alterar o acesso.')
        row = conn.execute('SELECT papel,ativa FROM Contas WHERE id=?', (conta_id,)).fetchone()
        if not row:
            raise BadRequest('Conta não encontrada.')
        if row == ('bibliotecario',1) and (not ativa or papel != 'bibliotecario'):
            if conn.execute("SELECT COUNT(*) FROM Contas WHERE papel='bibliotecario' AND ativa=1").fetchone()[0] <= 1:
                raise BadRequest('Não é possível desativar o último bibliotecário ativo.')
        conn.execute('UPDATE Contas SET papel=?,ativa=?,versao_sessao=versao_sessao+1 WHERE id=?',(papel,int(ativa),conta_id))
        auditar(conn,'alterar_acesso',conta_id,motivo=str(data['motivo'])[:500])
        conn.commit()
    return {'status':'ok'}
