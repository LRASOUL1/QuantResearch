# Quant Research Platform

Research environment for developing and evaluating systematic trading
strategies using market microstructure and order-flow data.

## Initial Focus

**Asset:** BTC/USD

**Primary research data:**
- Level 2 order-book data
- Trades / executions
- Market depth
- Order-book snapshots and/or event data

## Research Philosophy

The goal is to identify statistically and economically meaningful
relationships between market microstructure characteristics and subsequent
price behavior.

The research process will emphasize:

1. Exploratory data analysis
2. Hypothesis generation
3. Feature engineering
4. Statistical modeling
5. Out-of-sample validation
6. Walk-forward testing
7. Robustness / sensitivity analysis
8. Transaction costs and slippage
9. Paper trading
10. Live deployment only after adequate validation

Avoid data leakage, look-ahead bias, survivorship bias, and overfitting.

## Technology

- Python
- R
- DuckDB
- Parquet
- Git
- VS Code

## Project Structure

```text
QuantResearch/
├── data/
│   ├── raw/
│   ├── processed/
│   └── features/
├── docs/
├── experiments/
├── notebooks/
├── results/
└── src/