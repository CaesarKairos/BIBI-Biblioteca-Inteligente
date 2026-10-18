"""Segredos por instalação: DPAPI por usuário Windows; nunca exportar este arquivo."""
import base64
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import secrets
import threading
import hashlib
from contextlib import contextmanager

_lock = threading.RLock()


def _dpapi(data, decrypt=False):
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise OSError('Segredo indisponível para este usuário/computador. Reconfigure as credenciais.')
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel.LocalFree(target.data)


class SecretStore:
    def __init__(self, directory):
        self.path = Path(directory) / 'segredos.dpapi'

    @contextmanager
    def locked(self):
        # Protege também duas inicializações simultâneas no mesmo usuário Windows.
        with _lock:
            if os.name != 'nt':
                yield
                return
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
            kernel.CreateMutexW.restype=wintypes.HANDLE
            kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
            kernel.WaitForSingleObject.restype=wintypes.DWORD
            kernel.ReleaseMutex.argtypes=[wintypes.HANDLE]
            kernel.CloseHandle.argtypes=[wintypes.HANDLE]
            name='Local\\BIBISecrets-'+hashlib.sha256(str(self.path.resolve()).casefold().encode()).hexdigest()
            handle=kernel.CreateMutexW(None,False,name)
            if not handle:
                raise OSError('Não foi possível proteger a configuração da instalação.')
            acquired=False
            try:
                acquired=kernel.WaitForSingleObject(handle,30000) in (0,0x80)
                if not acquired:
                    raise OSError('Outra instância está atualizando os segredos. Tente novamente.')
                yield
            finally:
                if acquired:
                    kernel.ReleaseMutex(handle)
                kernel.CloseHandle(handle)

    def _read(self):
        if not self.path.exists():
            return {}
        raw = self.path.read_bytes()
        if os.name == 'nt':
            raw = _dpapi(raw, True)
        return json.loads(raw)

    def get(self, key, default=None):
        with self.locked():
            return self._read().get(key, default)

    def set(self, key, value):
        if key.startswith('ia_') and value is not None and os.name != 'nt':
            raise OSError('Credenciais de IA exigem o armazenamento protegido DPAPI desta distribuição Windows.')
        with self.locked():
            values = self._read()
            if value is None:
                values.pop(key, None)
            else:
                values[key] = value
            self.path.parent.mkdir(parents=True, exist_ok=True)
            raw = json.dumps(values).encode()
            if os.name == 'nt':
                raw = _dpapi(raw)
            temp = self.path.with_suffix('.tmp')
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'wb') as output:
                output.write(raw)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp, self.path)

    def session_key(self):
        with self.locked():
            key = self.get('session_key')
            if not key:
                key = secrets.token_hex(32)
                self.set('session_key', key)
            return key

    def recovery_key(self, rotate=False):
        """Vínculo da recuperação com esta instalação/usuário, sem senha de conta."""
        with self.locked():
            key = self.get('recovery_installation')
            if rotate or not key:
                key = secrets.token_urlsafe(32)
                self.set('recovery_installation', key)
            return key
