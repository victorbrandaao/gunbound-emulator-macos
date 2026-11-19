#!/bin/zsh
set -eu
cd -- "${0:A:h}"
printf 'Login do amigo (3 a 16 letras, números ou _): '
read -r usuario
.venv/bin/python -m operacao.administrar criar-conta "$usuario"
printf '\nPressione Enter para fechar.'
read -r
