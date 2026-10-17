"""TLS real com banco sintético; não substitui teste em outro dispositivo."""
import ssl
import socket
import json
import http.cookiejar
import urllib.request
import urllib.error
from unittest.mock import patch
from cryptography import x509
from tests.support import AppTest, authenticate, HASH
from services.rede_service import NetworkRuntime, LocalCertificates, private_peer


class NetworkTests(AppTest):
    def test_real_tls_and_shutdown(self):
        self.app.config['LAN_PORT']=0
        runtime=NetworkRuntime(self.app)
        self.app.extensions['network_runtime']=runtime
        self.addCleanup(runtime.stop)
        runtime.start()
        self.assertTrue(runtime.status()['ativo'],runtime.error)
        untrusted=ssl.create_default_context()
        with socket.create_connection(('127.0.0.1',runtime.port),timeout=3) as raw:
            with self.assertRaises(ssl.SSLCertVerificationError):
                untrusted.wrap_socket(raw,server_hostname='127.0.0.1')
        context=ssl.create_default_context(cafile=str(runtime.certificates.ca_path))
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=context))
        for ip in ['127.0.0.1']+list(runtime.hosts):
            with opener.open(f'https://{ip}:{runtime.port}/acesso',timeout=5) as response:
                self.assertEqual(response.status,200)
                self.assertIn('Secure',response.headers['Set-Cookie'])
        cookies=http.cookiejar.CookieJar()
        authenticated=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=context),urllib.request.HTTPCookieProcessor(cookies))
        base=f'https://{next(iter(runtime.hosts),"127.0.0.1")}:{runtime.port}'
        with authenticated.open(base+'/api/acesso/csrf') as response:
            csrf=json.load(response)['csrf']
        payload=json.dumps({'email':'admin@example.test','senha':'senha forte de teste'}).encode()
        request=urllib.request.Request(base+'/api/acesso/entrar',data=payload,headers={'Content-Type':'application/json','X-CSRF-Token':csrf,'Origin':base})
        with authenticated.open(request) as response:
            self.assertEqual(response.status,200)
        with authenticated.open(base+'/api/gestao/rede') as response:
            self.assertTrue(json.load(response)['ativo'])
        self.assertTrue(all(cookie.secure for cookie in cookies))
        self.assertTrue(all(item['conectou'] for item in runtime.diagnose()['resultados']))
        runtime.stop()
        self.assertFalse(runtime.status()['ativo'])

    def test_bind_failure_preserves_local_app(self):
        with socket.socket() as occupied:
            occupied.bind(('0.0.0.0',0))
            occupied.listen()
            self.app.config['LAN_PORT']=occupied.getsockname()[1]
            runtime=NetworkRuntime(self.app)
            self.addCleanup(runtime.stop)
            with self.assertLogs(self.app.logger,level='WARNING'):
                runtime.start()
            self.assertFalse(runtime.status()['ativo'])
            self.assertIn('já está em uso',runtime.status()['erro'])
            self.assertIn(str(runtime.port),runtime.status()['erro'])
            self.assertEqual(self.client.get('/app').status_code,200)

    def test_ca_persistence_and_ip_change(self):
        certificates=LocalCertificates(self.directory,self.app.extensions['secrets'])
        certificates.prepare(['192.168.1.2'])
        fingerprint=certificates.fingerprint
        again=LocalCertificates(self.directory,self.app.extensions['secrets'])
        again.prepare(['10.0.0.5'])
        self.assertEqual(fingerprint,again.fingerprint)
        cert=x509.load_pem_x509_certificate(again.cert_path.read_bytes())
        ips=set(map(str,cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.IPAddress)))
        self.assertEqual(ips,{'127.0.0.1','10.0.0.5'})
        self.assertIn(b'ENCRYPTED PRIVATE KEY',again.key_path.read_bytes())

    def test_network_authorization_and_forwarded_headers(self):
        runtime=NetworkRuntime(self.app)
        runtime.adapters=[{'interface':'Test','ip':'192.168.1.2'}]
        self.app.extensions['network_runtime']=runtime
        options={'base_url':'https://192.168.1.2','environ_overrides':{'REMOTE_ADDR':'192.168.1.3','bibi.lan':True}}
        self.client.set_cookie('session',self.client.get_cookie('session').value,domain='192.168.1.2')
        self.assertEqual(self.client.get('/api/gestao/rede',**options).status_code,200)
        self.assertEqual(self.client.get('/recuperacao-local',headers={'X-Forwarded-For':'127.0.0.1'},**options).status_code,403)
        self.assertEqual(self.client.get('/api/gestao/rede',base_url='http://192.168.1.2',environ_overrides=options['environ_overrides'],headers={'X-Forwarded-Proto':'https'}).status_code,403)
        self.assertEqual(self.client.get('/api/gestao/rede',base_url='https://evil.test').status_code,400)
        self.assertEqual(self.client.get('/acesso',base_url='https://192.168.1.2',environ_overrides={'REMOTE_ADDR':'8.8.8.8','bibi.lan':True}).status_code,403)
        self.sql("INSERT INTO Contas(nome,email,senha_hash,papel,ativacao) VALUES ('Leitor','reader@example.test',?,'leitor','presencial')",(HASH,))
        reader=authenticate(self.app,self.app.test_client(),2)
        reader.set_cookie('session',reader.get_cookie('session').value,domain='192.168.1.2')
        for path in ('/api/gestao/rede','/api/gestao/rede/certificado'):
            self.assertEqual(reader.get(path,**options).status_code,403)
        self.assertFalse(private_peer('8.8.8.8'))
        self.assertFalse(private_peer('169.254.1.1'))
        self.assertTrue(private_peer('172.16.1.1'))
