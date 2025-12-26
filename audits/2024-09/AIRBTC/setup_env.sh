#!/usr/bin/env bash
set -euo pipefail

if ! command -v forge >/dev/null 2>&1; then
  echo "forge not found. Install Foundry first:"
  echo "  curl -L https://foundry.paradigm.xyz | bash"
  echo "  source ~/.bashrc  # or restart your shell"
  echo "  foundryup"
  exit 1
fi

if ! command -v anvil >/dev/null 2>&1 || ! command -v chisel >/dev/null 2>&1; then
  echo "Foundry is installed but anvil/chisel are missing. Running foundryup..."
  foundryup
fi

if [ ! -d "../../../defihackLabs/lib/forge-std" ] && [ ! -d "lib/forge-std" ]; then
  echo "forge-std not found. Either run:"
  echo "  forge install foundry-rs/forge-std"
  echo "or update remappings to a local forge-std checkout."
  exit 1
fi

echo "Environment ready."
echo "Run: forge test --contracts ./test/2024-09/AIRBTC_exp.sol -vvv"
