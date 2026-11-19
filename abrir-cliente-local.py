from pathlib import Path
import os,subprocess,json
from Crypto.Cipher import AES
root=Path(__file__).resolve().parent
prefix=root/'runtime/prefix-v584'
creds=json.loads((root/'conta-admin-local.json').read_text())
plain=creds['usuario'].encode('ascii').ljust(16,b'\0')+creds['senha'].encode('ascii').ljust(16,b'\0')+bytes(16)
auth=AES.new(bytes.fromhex('FAEE85F24073D9161390197F6E562A67'),AES.MODE_ECB).encrypt(plain).hex().upper()
env=os.environ.copy();env.update(WINEPREFIX=str(prefix),WINEDLLOVERRIDES='winemenubuilder.exe=d;ddraw=n,b',WINEDEBUG='-all',WINE_COMPATDB='exe=*;dll_overrides=mshtml=b\nexe=GunBound.gme;d3d9=wined3d;opengl=cgl')
with (root/'logs/cliente-local.log').open('w') as log:
 p=subprocess.Popen([str(root/'runtime/wine/bin/wine'),'explorer.exe','/desktop=GunBoundS2,800x600','LauncherLocal.exe',auth],cwd=prefix/'drive_c/GunBoundS2',env=env,stdout=log,stderr=subprocess.STDOUT)
 print('Inicializador PID',p.pid)
 print('Resultado',p.wait())
