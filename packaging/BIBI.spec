# Distribuição onedir: não inclui bancos, .env ou segredos da instalação.
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root=Path(SPECPATH).parent
# Inclui somente assets versionados: uploads/caches locais jamais entram no pacote.
import subprocess
tracked=subprocess.check_output(['git','ls-files','-z','static'],cwd=root).decode('utf-8').split('\0')
static_data=[(str(root/path),str(Path(path).parent)) for path in tracked if path]
avatar_data,avatar_binaries,avatar_imports=collect_all('dicebear_styles')
core_data,core_binaries,core_imports=collect_all('dicebear')
schema_data,schema_binaries,schema_imports=collect_all('dicebear_schema')
a=Analysis([str(root/'app.py')],pathex=[str(root)],
    binaries=avatar_binaries+core_binaries+schema_binaries,
    datas=[(str(root/'LICENSE'),'.'),(str(root/'templates'),'templates'),
           (str(root/'database'/'schema.sql'),'database'),
           (str(root/'database'/'migrations'),'database/migrations')]+static_data+avatar_data+core_data+schema_data,
    hiddenimports=['waitress','cheroot.wsgi','cheroot.ssl.builtin','cryptography','psutil',
                   'requests','services.ai.providers','services.ai.policy','services.ai.recommendations','services.ai.runtime']+avatar_imports+core_imports+schema_imports,
    hookspath=[],hooksconfig={},runtime_hooks=[],excludes=[],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='BIBI',debug=False,
        strip=False,upx=False,console=False,icon=str(root/'static'/'images'/'icon.ico'))
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='BIBI')
