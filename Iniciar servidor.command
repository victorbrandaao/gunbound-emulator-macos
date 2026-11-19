#!/bin/bash
set -e
cd "$(dirname "$0")"
service="gui/$(id -u)/local.gunbound.season2.testes"
if ! launchctl print "$service" >/dev/null 2>&1; then
    launchctl bootstrap "gui/$(id -u)" "$PWD/servidor-local.plist"
fi
host=$(.venv/bin/python -c 'import yaml; print(yaml.safe_load(open("config.yml"))["broker"]["host"])')
printf 'Servidor GunBound Season 2 iniciado.\nBroker %s:8372\nJogo %s:8360\nAmigos %s:8352\n' "$host" "$host" "$host"
