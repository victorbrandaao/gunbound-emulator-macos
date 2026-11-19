#!/bin/zsh
set -eu
printf 'Conectando o Mac à rede privada GunBound.\n'
printf 'ID da rede ZeroTier (16 caracteres): '
read -r rede_zerotier
if [[ ! "$rede_zerotier" =~ ^[0-9a-fA-F]{16}$ ]]; then
    printf 'ID inválido.\n'
    exit 1
fi
printf 'Digite a senha de administrador do Mac se for solicitada (ela não aparece na tela).\n'
sudo /usr/local/bin/zerotier-cli join "$rede_zerotier"
sudo /usr/local/bin/zerotier-cli set "$rede_zerotier" allowDefault=0
sudo /usr/local/bin/zerotier-cli set "$rede_zerotier" allowGlobal=0
sudo /usr/local/bin/zerotier-cli set "$rede_zerotier" allowDNS=0
printf '\nEstado da rede:\n'
sudo /usr/local/bin/zerotier-cli listnetworks
printf '\nSe aparecer ACCESS_DENIED, autorize este Mac no painel do ZeroTier.\n'
printf 'Depois pressione Enter para fechar.'
read -r
