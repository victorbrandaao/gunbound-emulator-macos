#!/bin/bash
set -e
service="gui/$(id -u)/local.gunbound.season2.testes"
if launchctl print "$service" >/dev/null 2>&1; then
    launchctl bootout "$service"
fi
printf 'Servidor GunBound Season 2 parado.\n'
