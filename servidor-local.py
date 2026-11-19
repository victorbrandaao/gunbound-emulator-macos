#!/usr/bin/env python3
"""Mantém os três serviços do servidor de testes na mesma sessão."""
from pathlib import Path
import signal
import subprocess
import sys
import time
import json
from collections import deque
from operacao.administrar import backup

ROOT = Path(__file__).resolve().parent
stopping = False


def request_stop(signum, frame):
    global stopping
    stopping = True


signal.signal(signal.SIGTERM, request_stop)
signal.signal(signal.SIGINT, request_stop)
processes = []
restarts = {name: deque() for name in ('broker','game','buddy')}
names = ('broker','game','buddy')

def launch(name):
    print(f'Iniciando {name}',flush=True)
    return subprocess.Popen([sys.executable,'-u',f'{name}.py'],cwd=ROOT,
                            stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)

def status():
    state={'atualizado':time.strftime('%Y-%m-%dT%H:%M:%S%z'),
           'servicos':{name:{'pid':p.pid,'ativo':p.poll() is None,
                              'reinicios_recentes':len(restarts[name])}
                       for name,p in zip(names,processes)}}
    temp=ROOT/'logs/estado-servidor.tmp'
    temp.write_text(json.dumps(state,indent=2)+'\n')
    temp.replace(ROOT/'logs/estado-servidor.json')

try:
    try: print('Backup:',backup(),flush=True)
    except Exception as e: print('Falha de backup:',e,flush=True)
    next_backup=time.monotonic()+7200
    next_status=0
    for name in names: processes.append(launch(name))
    while not stopping:
        now=time.monotonic()
        for i,(name,process) in enumerate(zip(names,processes)):
            if process.poll() is None: continue
            while restarts[name] and now-restarts[name][0]>300: restarts[name].popleft()
            if len(restarts[name])>=3:
                raise RuntimeError(f'{name} falhou repetidamente. Consulte logs/{name}-*.log.')
            restarts[name].append(now)
            print(f'{name} encerrou com código {process.returncode}; reiniciando',flush=True)
            processes[i]=launch(name)
        if now>=next_backup:
            try: print('Backup:',backup(),flush=True)
            except Exception as e: print('Falha de backup:',e,flush=True)
            next_backup=now+7200
        if now>=next_status:
            status()
            next_status=now+10
        time.sleep(1)
finally:
    for process in processes:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    status()
