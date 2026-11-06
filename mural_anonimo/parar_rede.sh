#!/bin/bash
# Mata todos os processos guardados em logs/pids.txt.

cd "$(dirname "$0")"

if [ ! -f logs/pids.txt ]; then
    echo "Nada para parar (logs/pids.txt não existe)."
    exit 0
fi

while read pid; do
    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null
    fi
done < logs/pids.txt

# Espera um instante e força quem sobrou
sleep 1
while read pid; do
    if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null
    fi
done < logs/pids.txt

rm -f logs/pids.txt
echo "Rede parada."