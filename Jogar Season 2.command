#!/bin/zsh
set -eu
cd -- "${0:A:h}"
./'Iniciar servidor.command'
exec .venv/bin/python abrir-cliente-local.py
