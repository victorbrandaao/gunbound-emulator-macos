#!/bin/zsh
cd -- "${0:A:h}"
.venv/bin/python -m operacao.administrar status
printf '\nPressione Enter para fechar.'
read -r
