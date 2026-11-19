"""Administração do ambiente privado. Execute com .venv/bin/python."""
from pathlib import Path
import argparse
import configparser
import getpass
import ipaddress
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import time
import zipfile
import yaml

ROOT = Path(__file__).resolve().parents[1]
ZEROTIER_NETWORK_ID = os.environ.get('ZEROTIER_NETWORK_ID', '')


def zerotier_address(network_id=None):
    """Retorna o primeiro IPv4 atribuído pela rede ZeroTier em estado OK."""
    candidates = [
        shutil.which('zerotier-cli'),
        '/usr/local/bin/zerotier-cli',
        '/Library/Application Support/ZeroTier/One/zerotier-cli',
    ]
    cli = next((p for p in candidates if p and Path(p).exists()), None)
    if cli is None:
        raise OSError('zerotier-cli não encontrado; instale o ZeroTier One.')
    result = subprocess.run(
        [cli, 'listnetworks'],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise OSError(result.stderr.strip() or 'não foi possível consultar o ZeroTier.')
    matches = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) < 9 or fields[0] != '200' or fields[1] != 'listnetworks':
            continue
        if network_id and fields[2] != network_id:
            continue
        matches.append(fields)
    if not network_id and len(matches) == 1:
        network_id = matches[0][2]
    if not network_id:
        if len(matches) > 1:
            raise ValueError('Informe o ID da rede com --rede; este Mac pertence a mais de uma rede ZeroTier.')
        raise ValueError('Este Mac não está conectado a nenhuma rede ZeroTier.')
    for fields in matches:
        if fields[2] != network_id:
            continue
        if fields[5] != 'OK':
            raise ValueError(f'ZeroTier ainda não autorizou a rede {network_id} (estado: {fields[5]}).')
        for assigned in fields[8].split(','):
            try:
                interface = ipaddress.ip_interface(assigned)
            except ValueError:
                continue
            if isinstance(interface, ipaddress.IPv4Interface):
                return str(interface.ip), str(interface.network)
        raise ValueError(f'A rede ZeroTier {network_id} não recebeu um IPv4.')
    raise ValueError(f'Este Mac não está conectado à rede ZeroTier {network_id}.')


def backup(root=ROOT):
    folder = root / 'backups/automaticos'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / time.strftime('gbwc-%Y%m%d-%H%M%S.db')
    with sqlite3.connect(root / 'gbwc.db', timeout=15) as source:
        with sqlite3.connect(path) as dest:
            source.backup(dest)
    os.chmod(path, 0o600)
    for old in sorted(folder.glob('gbwc-*.db'), reverse=True)[14:]:
        old.unlink()
    return path


def create_account(user, password, nick=None, cash=50000, gold=100000, root=ROOT):
    if not re.fullmatch(r'[A-Za-z0-9_]{3,16}', user):
        raise ValueError('Login: 3 a 16 letras, números ou _.')
    if not 1 <= len(password) <= 16 or not password.isascii() or any(ord(c)<33 for c in password):
        raise ValueError('Senha: 1 a 16 caracteres ASCII sem espaços.')
    nick = nick or user[:12]
    if not nick.isascii() or not 1 <= len(nick) <= 12:
        raise ValueError('Apelido: 1 a 12 caracteres ASCII.')
    if not all(0 <= v <= 2_000_000_000 for v in (cash, gold)):
        raise ValueError('Saldo fora da faixa suportada.')
    c = sqlite3.connect(root / 'gbwc.db', timeout=15)
    c.row_factory = sqlite3.Row
    try:
        with c:
            if c.execute('select 1 from User where lower(User)=lower(?) or lower(Id)=lower(?)', (user,user)).fetchone():
                raise ValueError('Esta conta já existe; nenhum dado foi alterado.')
            if c.execute('select 1 from User where lower(Nickname)=lower(?)',(nick,)).fetchone():
                raise ValueError('Apelido já utilizado.')
            for table in ('User', 'Game'):
                row = dict(c.execute(f'SELECT * FROM "{table}" WHERE Id=?', ('test',)).fetchone())
                row['Id'] = user
                if table == 'User':
                    row.update(User=user,Nickname=nick,Password=password,Authority=1,Authority2=1,
                               E_Mail='',MuteTime=None,RestrictTime=None)
                else:
                    row.update(NickName=nick,Guild='',MemberCount=0,Money=gold,AvatarWear=0,
                               TotalGrade=1,SeasonGrade=1,CountryGrade=1,TotalScore=0,SeasonScore=0,
                               TotalRank=0,SeasonRank=0,CountryRank=0,GuildRank=0,
                               AccumShot=0,AccumDamage=0,NoRankUpdate=0,StageRecords=None,
                               MobileRecords=None,LastUpdateTime=None,GiftProhibitTime=None,
                               Prop1='',Prop2='',ReadyItems=None)
                cols=','.join('"'+col+'"' for col in row)
                c.execute(f'INSERT INTO "{table}" ({cols}) VALUES ({",".join("?" for _ in row)})',list(row.values()))
            c.execute('INSERT INTO Cash(ID,Cash,OldCash) VALUES (?,?,0)',(user,cash))
    finally:
        c.close()


def write_client_ini(host, path):
    cfg=configparser.ConfigParser()
    cfg.optionxform=str
    cfg['Gunbound']={'BrokerServerIP':host,'BrokerServerPort':'8372','BuddyIP':host,'BuddyPort':'8352'}
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w') as f: cfg.write(f)


def prepare_network(host, network, apply=False, root=ROOT):
    ip=ipaddress.IPv4Address(host)
    net=ipaddress.IPv4Network(network,strict=False)
    if ip not in net or ip.is_unspecified or ip.is_multicast or (not ip.is_private and not ip.is_loopback):
        raise ValueError('Use o IPv4 privado atribuído ao Mac pelo ZeroTier e sua sub-rede.')
    if ip in (net.network_address,net.broadcast_address) and net.prefixlen<31:
        raise ValueError('Use o endereço do dispositivo, não o endereço da rede/broadcast.')
    if net.prefixlen < 16:
        raise ValueError('Informe a sub-rede específica da rede ZeroTier (/16 a /32).')
    cfg=yaml.safe_load((root/'config.yml').read_text())
    cfg['broker']['host']=str(ip)
    cfg['buddy_server']['host']=str(ip)
    for server in cfg['gameservers']:
        server['host']=str(ip)
        server['accept']=[str(net)]
        server['udp_allow']=['127.0.0.1/32',str(ip)+'/32']
        server['users_max']=16
        server['description']='Grupo de amigos\nSeason 2'
    output=root/'config.online.yml'
    output.write_text(yaml.safe_dump(cfg,allow_unicode=True,sort_keys=False))
    if apply:
        with socket.socket() as s:
            s.bind((str(ip),0)) # não aplicar um endereço ausente/desconectado
        backup(root)
        stamp=time.strftime('%Y%m%d-%H%M%S')
        shutil.copy2(root/'config.yml',root/f'backups/config-{stamp}.yml')
        shutil.copy2(output,root/'config.yml')
        write_client_ini(str(ip),root/'runtime/prefix-v584/drive_c/GunBoundS2/GunBound.ini')
        (root/'servidor-rede.json').write_text(json.dumps({'host':str(ip),'network':str(net)},indent=2)+'\n')
    return output


def prepare_zerotier(network_id=ZEROTIER_NETWORK_ID, apply=False, root=ROOT):
    host, network = zerotier_address(network_id)
    return prepare_network(host, network, apply=apply, root=root)


def windows_package(host, root=ROOT):
    ipaddress.IPv4Address(host)
    folder=root/'compartilhar/GunBound-S2-Windows'
    if not folder.exists():
        shutil.copytree(root/'cliente-v584',folder)
    shutil.copy2(root/'runtime/LauncherAmigos.exe',folder/'Jogar GunBound.exe')
    write_client_ini(host,folder/'GunBound.ini')
    (folder/'LEIA-ME.txt').write_text(
        'GunBound Season 2 — grupo privado\n\n'
        '1. Instale ZeroTier pelo site https://www.zerotier.com/download/\n'
        '2. Entre na rede cujo ID o dono informar e aguarde autorização.\n'
        '3. Extraia TODO o ZIP para uma pasta local. Não execute dentro do ZIP.\n'
        '4. Abra Jogar GunBound.exe e informe sua conta individual.\n'
        '5. Escolha GunBound Season 2 - Testes na lista.\n\n'
        f'Servidor: {host}\n'
        'O Mac que hospeda precisa estar ligado e conectado à rede.\n'
        'Se o Windows perguntar pelo firewall, permita apenas o jogo na rede privada.\n'
        'Não use NyxLauncher.exe: ele depende de um atualizador antigo.\n'
        'Este pacote foi preparado; precisa ser validado em um PC Windows.\n',encoding='utf-8')
    target=root/'compartilhar/GunBound-S2-Windows.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for p in folder.rglob('*'):
            if p.is_file() and p.suffix.lower() not in ('.log','.pdb'):
                z.write(p,p.relative_to(folder.parent))
    return target


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sp=ap.add_subparsers(dest='cmd',required=True)
    a=sp.add_parser('criar-conta');a.add_argument('usuario');a.add_argument('--apelido');a.add_argument('--cash',type=int,default=50000);a.add_argument('--gold',type=int,default=100000)
    sp.add_parser('backup')
    a=sp.add_parser('rede');a.add_argument('--ip',required=True);a.add_argument('--subrede',required=True);a.add_argument('--aplicar',action='store_true')
    a=sp.add_parser('rede-zerotier');a.add_argument('--rede',default=ZEROTIER_NETWORK_ID);a.add_argument('--aplicar',action='store_true')
    a=sp.add_parser('pacote-windows');a.add_argument('--ip',required=True)
    sp.add_parser('status')
    args=ap.parse_args()
    try:
        if args.cmd=='criar-conta':
            password=getpass.getpass('Senha da nova conta: ')
            if password!=getpass.getpass('Repita a senha: '):raise ValueError('As senhas são diferentes.')
            backup();create_account(args.usuario,password,args.apelido,args.cash,args.gold)
            print(f'Conta {args.usuario} criada como jogador comum.')
        elif args.cmd=='backup':print(backup())
        elif args.cmd=='rede':
            print(prepare_network(args.ip,args.subrede,args.aplicar))
            print('Aplicado. Reinicie o servidor e reabra o jogo.' if args.aplicar else 'Prévia criada; a configuração ativa não mudou.')
        elif args.cmd=='rede-zerotier':
            host, network = zerotier_address(args.rede)
            print(f'ZeroTier: {host} ({network})')
            print(prepare_zerotier(args.rede,args.aplicar))
            print('Aplicado. Reinicie o servidor e reabra o jogo.' if args.aplicar else 'Prévia criada; a configuração ativa não mudou.')
        elif args.cmd=='pacote-windows':print(windows_package(args.ip))
        elif args.cmd=='status':
            cfg=yaml.safe_load((ROOT/'config.yml').read_text());host=cfg['broker']['host']
            print('IP configurado:',host)
            for port in (8372,8360,8352):
                try:
                    with socket.create_connection((host,port),timeout=2):print(port,'TCP OK')
                except OSError as e:print(port,'indisponível:',e)
            state=ROOT/'logs/estado-servidor.json'
            if state.exists():print(state.read_text())
    except (ValueError,OSError,sqlite3.Error) as e:
        ap.exit(1,str(e)+'\n')


if __name__=='__main__':main()
