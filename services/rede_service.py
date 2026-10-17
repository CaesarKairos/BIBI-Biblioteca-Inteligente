"""HTTPS LAN integrado; não concede privilégios por endereço de origem."""
from datetime import datetime, timedelta, timezone
import errno
import ipaddress
import os
from pathlib import Path
import secrets
import socket
import ssl
import threading


PRIVATE_NETWORKS=tuple(ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'))


def private_peer(address):
    try:
        ip=ipaddress.ip_address(address)
        return ip.is_loopback or any(ip in network for network in PRIVATE_NETWORKS)
    except ValueError:
        return False


def interfaces():
    """Consulta interfaces locais, sem depender de DNS nem enviar pacotes externos."""
    import psutil
    states=psutil.net_if_stats()
    result=[]
    for name,addresses in psutil.net_if_addrs().items():
        if name not in states or not states[name].isup:
            continue
        for address in addresses:
            if address.family==socket.AF_INET:
                ip=ipaddress.ip_address(address.address)
                if not ip.is_loopback and private_peer(str(ip)):
                    result.append({'interface':name,'ip':str(ip)})
    return sorted(result,key=lambda item:(item['interface'].casefold(),item['ip']))


def write_private(path, content):
    temp=path.with_suffix(path.suffix+'.tmp')
    fd=os.open(temp,os.O_CREAT|os.O_TRUNC|os.O_WRONLY,0o600)
    with os.fdopen(fd,'wb') as output:
        output.write(content)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temp,path)


class LocalCertificates:
    def __init__(self, directory, store):
        self.directory=Path(directory)/'rede'
        self.directory.mkdir(exist_ok=True)
        self.store=store
        self.ca_path=self.directory/'BIBI-rede-local.crt'
        self.cert_path=self.directory/'servidor.pem'
        self.key_path=self.directory/'servidor.key.pem'

    def prepare(self, addresses):
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes,serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID
        now=datetime.now(timezone.utc)
        bundle=self.store.get('lan_ca')
        if bundle:
            ca=x509.load_pem_x509_certificate(bundle['certificate'].encode())
            ca_key=serialization.load_pem_private_key(bundle['key'].encode(),password=None)
            if ca.not_valid_after_utc < now+timedelta(days=100):
                raise RuntimeError('O certificado da instalação está perto de expirar. Renove a confiança nos dispositivos com o suporte da biblioteca.')
        else:
            ca_key=ec.generate_private_key(ec.SECP256R1())
            name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'BIBI LAN '+secrets.token_hex(6))])
            ca=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(ca_key.public_key())
                .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=5))
                .not_valid_after(now+timedelta(days=3650))
                .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
                .add_extension(x509.KeyUsage(False,False,False,False,False,True,True,False,False),critical=True)
                .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),critical=False)
                .add_extension(x509.NameConstraints(
                    permitted_subtrees=[x509.IPAddress(n) for n in PRIVATE_NETWORKS]+[
                        x509.IPAddress(ipaddress.ip_network('127.0.0.0/8')),x509.DNSName('localhost')],
                    excluded_subtrees=None),critical=True)
                .sign(ca_key,hashes.SHA256()))
            self.store.set('lan_ca',{
                'certificate':ca.public_bytes(serialization.Encoding.PEM).decode(),
                'key':ca_key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()).decode(),
            })
        public_ca=ca.public_bytes(serialization.Encoding.PEM)
        if not self.ca_path.exists() or self.ca_path.read_bytes()!=public_ca:
            write_private(self.ca_path,public_ca)
        self.fingerprint=':'.join(f'{byte:02X}' for byte in ca.fingerprint(hashes.SHA256()))
        ips=sorted(set(addresses)|{'127.0.0.1'})
        renew=True
        try:
            previous=x509.load_pem_x509_certificate(self.cert_path.read_bytes())
            sans=previous.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
            renew=(set(map(str,sans.get_values_for_type(x509.IPAddress)))!=set(ips)
                   or previous.not_valid_after_utc<now+timedelta(days=7))
            previous.verify_directly_issued_by(ca)
        except (OSError,ValueError,x509.ExtensionNotFound):
            renew=True
        password=self.store.get('lan_tls_password')
        if not password:
            password=secrets.token_urlsafe(48)
            self.store.set('lan_tls_password',password)
            renew=True
        if renew or not self.key_path.exists():
            key=ec.generate_private_key(ec.SECP256R1())
            certificate=(x509.CertificateBuilder()
                .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'BIBI servidor local')]))
                .issuer_name(ca.subject).public_key(key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=90))
                .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
                .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(ip)) for ip in ips]+[x509.DNSName('localhost')]),critical=False)
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),critical=False)
                .add_extension(x509.KeyUsage(True,False,False,False,False,False,False,False,False),critical=True)
                .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),critical=False)
                .sign(ca_key,hashes.SHA256()))
            write_private(self.key_path,key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.BestAvailableEncryption(password.encode())))
            write_private(self.cert_path,certificate.public_bytes(serialization.Encoding.PEM))
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version=ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(self.cert_path,self.key_path,password=password)
        return context


class NetworkRuntime:
    def __init__(self, app):
        self.app=app
        self.port=app.config.get('LAN_PORT',5443)
        self.adapters=[]
        self.server=None
        self.thread=None
        self.monitor_thread=None
        self.error=None
        self.certificates=None
        self.stopping=threading.Event()
        self.lock=threading.RLock()

    @property
    def hosts(self):
        with self.lock:
            return {item['ip'] for item in self.adapters}

    def start(self):
        if not self.app.config.get('LAN_ENABLED',True):
            self.error='Acesso de rede desativado nesta execução.'
            return
        try:
            from cheroot.wsgi import Server
            from cheroot.ssl.builtin import BuiltinSSLAdapter
            class LocalServer(Server):
                def bind_socket(self,connection,address):
                    # Cheroot 11 deixa o socket sem fechamento se bind falhar.
                    try:
                        return Server.bind_socket(connection,address)
                    except OSError as error:
                        self.bind_error=error
                        connection.close()
                        raise
            self.certificates=LocalCertificates(self.app.config['DATA_DIR'],self.app.extensions['secrets'])
            self.refresh()
            adapter=BuiltinSSLAdapter(str(self.certificates.cert_path),str(self.certificates.key_path),
                                     private_key_password=self.app.extensions['secrets'].get('lan_tls_password'))
            adapter.context=self.context
            def lan_application(environ,start_response):
                environ['bibi.lan']=True
                return self.app(environ,start_response)
            self.server=LocalServer(('0.0.0.0',self.port),lan_application,numthreads=8,timeout=15,shutdown_timeout=3)
            self.server.ssl_adapter=adapter
            self.server.max_request_body_size=512*1024*1024
            self.server.prepare()
            self.port=self.server.socket.getsockname()[1]
            self.thread=threading.Thread(target=self.server.serve,daemon=True,name='bibi-lan-https')
            self.thread.start()
            self.monitor_thread=threading.Thread(target=self.monitor,daemon=True,name='bibi-lan-addresses')
            self.monitor_thread.start()
        except Exception as error:
            bind_error=getattr(self.server,'bind_error',None)
            if bind_error and (bind_error.errno==errno.EADDRINUSE or getattr(bind_error,'winerror',None)==10048):
                self.error=f'A porta {self.port} já está em uso. Encerre outra instância da BIBI, inclusive na bandeja, ou o servidor de teste e abra o aplicativo novamente.'
                self.app.logger.warning(self.error)
            else:
                self.error=f'Não foi possível iniciar o HTTPS local: {error}'
                self.app.logger.exception('Servidor LAN não iniciado; janela local permanece disponível')
            if self.server:
                self.server.stop()

    def refresh(self):
        current=interfaces()
        with self.lock:
            # Duas instâncias não podem criar autoridades diferentes simultaneamente.
            with self.certificates.store.locked():
                context=self.certificates.prepare([item['ip'] for item in current])
            if self.server:
                self.server.ssl_adapter.context=context
            self.context=context
            self.adapters=current

    def monitor(self):
        while not self.stopping.wait(15):
            try:
                self.refresh()
                self.error=None
            except Exception as error:
                self.error=f'Não foi possível atualizar o endereço ou certificado: {error}'

    def status(self):
        with self.lock:
            running=bool(self.server and self.server.ready and self.thread and self.thread.is_alive())
            return {'ativo':running,'porta':self.port,'erro':self.error,
                    'enderecos':[item|{'url':f'https://{item["ip"]}:{self.port}'} for item in self.adapters],
                    'certificado_sha256':getattr(self.certificates,'fingerprint',None),
                    'bandeja':bool(self.app.extensions.get('desktop_tray')),
                    'origem_legada_preservada':True}

    def diagnose(self):
        result=[]
        context=ssl.create_default_context(cafile=str(self.certificates.ca_path)) if self.certificates else None
        for address in self.status()['enderecos']:
            try:
                if not context:
                    raise OSError('Certificado indisponível.')
                with socket.create_connection((address['ip'],self.port),timeout=2) as raw:
                    with context.wrap_socket(raw,server_hostname=address['ip']):
                        pass
                result.append(address|{'conectou':True})
            except (OSError,ssl.SSLError) as error:
                result.append(address|{'conectou':False,'erro':str(error)})
        return {'resultados':result,'aviso':'Autoteste feito neste computador. Acesso por outro dispositivo precisa ser verificado nesse dispositivo.'}

    def stop(self):
        self.stopping.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        if self.server:
            self.server.stop()
        if self.thread:
            self.thread.join(timeout=5)
