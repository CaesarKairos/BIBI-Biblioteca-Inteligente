"""Servidor descartável para teste em outro dispositivo; nunca abre o banco real."""
from pathlib import Path
import json
import secrets
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from services.rede_service import NetworkRuntime
from werkzeug.security import generate_password_hash
from waitress import create_server


def main():
    with tempfile.TemporaryDirectory(prefix='bibi-rede-manual-') as directory:
        app=create_app({'DATA_DIR':directory,'LAN_PORT':5443,'TESTING':True})
        password=secrets.token_urlsafe(16)
        with app.extensions['database'].connection() as conn:
            conn.execute("INSERT INTO Contas(nome,email,senha_hash,papel,ativacao,onboarding_concluido_em) VALUES ('Teste de rede','rede@example.test',?,'bibliotecario','inicial',CURRENT_TIMESTAMP)",(generate_password_hash(password),))
            conn.execute("INSERT INTO Livros(nome,autor,estoque,quantidade_disponivel) VALUES ('Livro sintético de rede','Teste',1,1)")
            conn.commit()
        runtime=NetworkRuntime(app)
        app.extensions['network_runtime']=runtime
        local=create_server(app,host='127.0.0.1',port=5001,threads=4)
        try:
            runtime.start()
            if not runtime.status()['ativo']:
                raise RuntimeError(runtime.error)
            information=runtime.status()|{'pasta':directory,'local':'http://127.0.0.1:5001','email':'rede@example.test','senha':password,'certificado':str(runtime.certificates.ca_path)}
            report=Path(tempfile.gettempdir())/'bibi-rede-manual.json'
            report.write_text(json.dumps(information,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(information,ensure_ascii=False,indent=2),flush=True)
            print('Interrompa este processo para encerrar o servidor e apagar os dados sintéticos.',flush=True)
            local.run()
        finally:
            local.close()
            runtime.stop()


if __name__=='__main__':
    main()
