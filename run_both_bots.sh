#!/bin/bash
# Run both bots for testing
# Usage: ./run_both_bots.sh

cd "$(dirname "$0")"

echo "=== Starting both bots ==="
echo ""

# Kill any previous bot processes
pkill -f "test_ia_mother.py" 2>/dev/null
pkill -f "test_zero_bot.py" 2>/dev/null
sleep 1

echo "[1/2] Starting IA-Mother bot..."
python test_ia_mother.py &
IA_PID=$!
echo "  PID: $IA_PID"
sleep 3

echo ""
echo "[2/2] Starting Zero Bot..."
python test_zero_bot.py &
ZERO_PID=$!
echo "  PID: $ZERO_PID"
sleep 3

echo ""
echo "=== Both bots started ==="
echo "  IA-Mother: PID $IA_PID"
echo "  Zero Bot:  PID $ZERO_PID"
echo ""
echo "Send /start to:"
echo "  - @IAMotherBot"
echo "  - Your Zero Bot"
echo ""
echo "Press Ctrl+C to stop both bots"

trap "kill $IA_PID $ZERO_PID 2>/dev/null; echo 'Bots stopped'; exit 0" INT TERM

wait
