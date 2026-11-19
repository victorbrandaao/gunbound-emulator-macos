#!/bin/zsh
set -eu
cd -- "${0:A:h}"
.venv/bin/python -m operacao.administrar rede-zerotier --aplicar
ip_zerotier=$(.venv/bin/python -c 'from operacao.administrar import zerotier_address; print(zerotier_address()[0])')
.venv/bin/python -m operacao.administrar pacote-windows --ip "$ip_zerotier"
./'Parar servidor.command'
./'Iniciar servidor.command'
printf '\nRede aplicada e pacote Windows atualizado na pasta compartilhar. Reabra o jogo.\n'
printf 'Pressione Enter para fechar.'
read -r
