#!/bin/bash

echo "=== Checking Strategy Mapping ==="

# Show the strategy mapping
echo "Strategy IDs from portfolio:"
echo "- ai_risk_management"
echo "- ai_portfolio_optimization" 
echo "- ai_spot_momentum_strategy"
echo "- ai_options_trade"

echo -e "\nMapped to scanner functions:"
echo "- ai_risk_management -> risk_management"
echo "- ai_portfolio_optimization -> portfolio_optimization"
echo "- ai_spot_momentum_strategy -> spot_momentum_strategy"
echo "- ai_options_trade -> options_trade"

echo -e "\nAvailable scanners in code:"
echo "- risk_management"
echo "- portfolio_optimization"
echo "- spot_momentum_strategy ✓"
echo "- options_trade"

echo -e "\nPossible issues:"
echo "1. Other scanners might be returning empty results"
echo "2. Other scanners might have errors that are being caught"
echo "3. Asset filtering might not apply to other strategy types"

