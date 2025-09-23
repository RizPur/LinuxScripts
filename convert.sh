#!/bin/bash

# Load environment variables
if [ -f "$(dirname "$0")/.env" ]; then
    export $(grep -v '^#' "$(dirname "$0")/.env" | xargs)
fi

API_KEY="${EXCHANGE_API_KEY}"
CRYPTO_LIST=("BTC" "ETH" "LTC" "XRP" "ADA" "DOGE")

if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <from_currency> <to_currency> <amount>"
  echo "Example: $0 usd jmd 10"
  exit 1
fi

FROM=$(echo "$1" | tr '[:lower:]' '[:upper:]')
TO=$(echo "$2" | tr '[:lower:]' '[:upper:]')
AMOUNT=$3

is_crypto() {
  [[ " ${CRYPTO_LIST[@]} " =~ " $1 " ]]
}

if is_crypto "$FROM" || is_crypto "$TO"; then
  # Crypto conversion using CoinGecko
  FROM_LOWER=$(echo "$FROM" | tr '[:upper:]' '[:lower:]')
  TO_LOWER=$(echo "$TO" | tr '[:upper:]' '[:lower:]')
  
  RESPONSE=$(curl -s "https://api.coingecko.com/api/v3/simple/price?ids=$FROM_LOWER&vs_currencies=$TO_LOWER")
  
  PRICE=$(echo "$RESPONSE" | jq -r ".[\"$FROM_LOWER\"][\"$TO_LOWER\"]")
  
  if [[ "$PRICE" == "null" || -z "$PRICE" ]]; then
    echo "❌ Error: Could not fetch conversion rate for $FROM → $TO"
    exit 1
  fi

  RESULT=$(echo "$AMOUNT * $PRICE" | bc -l)
  printf "💱 %s %s = %.8f %s\n" "$AMOUNT" "$FROM" "$RESULT" "$TO"
else
  # Fiat conversion using ExchangeRate API
  RESPONSE=$(curl -s "https://v6.exchangerate-api.com/v6/$API_KEY/pair/$FROM/$TO/$AMOUNT")

  if ! echo "$RESPONSE" | jq empty 2>/dev/null; then
    echo "❌ Invalid response from API. Check your internet or API key."
    exit 1
  fi

  RESULT=$(echo "$RESPONSE" | jq -r '.conversion_result')

  if [[ "$RESULT" == "null" || -z "$RESULT" ]]; then
    echo "❌ Error: $(echo $RESPONSE | jq -r '.["error-type"] // "Unknown error"')"
  else
    echo "💱 $AMOUNT $FROM = $RESULT $TO"
  fi
fi

