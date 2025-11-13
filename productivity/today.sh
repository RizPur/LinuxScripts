#!/bin/bash

# Load environment variables
if [ -f "$(dirname "$0")/.env" ]; then
    export $(grep -v '^#' "$(dirname "$0")/.env" | xargs)
fi

LOG_FILE="${LOG_FILE:-~/Scripts/logs.log}"
DAYS=${1:-7}
START_DATE=$(date +%Y-%m-%d)
END_DATE=$(date -d "+$DAYS days" +%Y-%m-%d)

#echo $END_DATE
echo "[$(date)] 📆 Weekly Calendar Check" | tee -a "$LOG_FILE"
echo "Events from $START_DATE to $END_DATE:" | tee -a "$LOG_FILE"

gcalcli --nocolor agenda "$START_DATE" "$END_DATE" 2>&1 | tee -a "$LOG_FILE"

#echo ""
#echo "[$(date)] 💰 Crypto Prices:" | tee -a "$LOG_FILE"

# curl -s "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd" | jq -r '. | "Bitcoin: $" + (.bitcoin.usd|tostring) + "\nEthereum: $" + (.ethereum.usd|tostring)' | tee -a "$LOG_FILE"

