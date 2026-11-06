#!/bin/bash
# Sobe diretório, 4 relés e mural em background.
# Guarda os PIDs em logs/pids.txt para o parar_rede.sh matar depois.

set -e

# Vai para a pasta do script (funciona de qualquer lugar)
cd "$(dirname "$0")"

# Cria pasta de logs se não existir
mkdir -p logs

# Se já houver PIDs antigos, para antes
if [ -f logs/pids.txt ]; then
    echo "Encontrei PIDs antigos. Parando..."
    ./parar_rede.sh 2>/dev/null || true
fi

# Limpa logs antigos
rm -f logs/*.txt

# Sobe diretório
python3 -u diretorio.py > logs/diretorio.txt 2>&1 &
echo $! > logs/pids.txt

# Espera um instante para o diretório subir
sleep 0.5

# Sobe 4 relés
for i in 1 2 3 4; do
    python3 -u rele.py R$i 900$i > logs/R$i.txt 2>&1 &
    echo $! >> logs/pids.txt
    sleep 0.3
done

# Sobe mural
python3 -u mural.py > logs/mural.txt 2>&1 &
echo $! >> logs/pids.txt

sleep 0.5

echo "Rede no ar. PIDs em logs/pids.txt"
echo "Para ver os logs: tail -f logs/*.txt"