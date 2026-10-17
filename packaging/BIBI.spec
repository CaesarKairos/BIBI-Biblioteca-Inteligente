# Distribuição onedir: não inclui bancos, .env ou segredos da instalação.
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root=Path(SPECPATH).parent
avatar_data,avatar_binaries,avatar_imports=collect_all('dicebear_styles')
core_data,core_binaries,core_imports=collect_all('dicebear')
a=Analysis([str(root/'app.py')],pathex=[str(root)],
    binaries=avatar_binaries+core_binaries,
    datas=[(str(root/'LICENSE'),'.'),(str(root/'static'),'static'),(str(root/'templates'),'templates'),
           (str(root/'database'/'schema.sql'),'database'),
           (str(root/'database'/'migrations'),'database/migrations')]+avatar_data+core_data,
    hiddenimports=['waitress','cheroot.wsgi','cheroot.ssl.builtin','cryptography','psutil']+avatar_imports+core_imports,
    hookspath=[],hooksconfig={},runtime_hooks=[],excludes=[],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='BIBI',debug=False,
        strip=False,upx=False,console=False,icon=str(root/'static'/'images'/'icon.ico'))
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='BIBI')
