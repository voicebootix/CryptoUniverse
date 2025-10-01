"""Utility data structures for market data, asset expectations, and yield products."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class AssetProfile:
    """Static profile describing long-run expectations for an asset."""

    symbol: str
    category: str
    tier: str
    baseline_return: float  # Expected annual price appreciation (decimal)
    volatility: float       # Expected annualized volatility (decimal)
    staking_yield: float = 0.0  # Additional staking / yield component (decimal)
    notes: str = ""
    yield_sources: Tuple[str, ...] = ()

    @property
    def total_expected_return(self) -> float:
        """Convenience helper returning baseline + staking."""
        return self.baseline_return + self.staking_yield


DEFAULT_EXPECTED_RETURN: float = 0.18
DEFAULT_VOLATILITY: float = 0.85
DEFAULT_STABLECOIN_RETURN: float = 0.03


ASSET_PROFILES: Dict[str, AssetProfile] = {
    # Large-cap layer 1s
    "BTC": AssetProfile(
        symbol="BTC",
        category="large_cap",
        tier="tier_institutional",
        baseline_return=0.18,
        volatility=0.65,
        staking_yield=0.0,
        notes="Benchmark asset with institutional liquidity.",
        yield_sources=("lending", "covered_calls"),
    ),
    "ETH": AssetProfile(
        symbol="ETH",
        category="large_cap",
        tier="tier_institutional",
        baseline_return=0.18,
        volatility=0.75,
        staking_yield=0.045,
        notes="Proof-of-Stake with liquid staking derivatives widely available.",
        yield_sources=("staking", "lending"),
    ),
    "BNB": AssetProfile(
        symbol="BNB",
        category="large_cap",
        tier="tier_enterprise",
        baseline_return=0.17,
        volatility=0.70,
        staking_yield=0.04,
        notes="Exchange token with burn schedule and staking programs.",
        yield_sources=("staking", "exchange_rebates"),
    ),
    "SOL": AssetProfile(
        symbol="SOL",
        category="large_cap",
        tier="tier_enterprise",
        baseline_return=0.22,
        volatility=0.95,
        staking_yield=0.07,
        notes="High throughput L1 with active staking delegation.",
        yield_sources=("staking", "liquid_staking"),
    ),
    "ADA": AssetProfile(
        symbol="ADA",
        category="large_cap",
        tier="tier_enterprise",
        baseline_return=0.16,
        volatility=0.85,
        staking_yield=0.045,
        notes="Delegated staking with liquid ADA pools.",
        yield_sources=("staking",),
    ),
    "DOT": AssetProfile(
        symbol="DOT",
        category="large_cap",
        tier="tier_professional",
        baseline_return=0.18,
        volatility=0.90,
        staking_yield=0.08,
        notes="Nominated Proof-of-Stake with bonded staking rewards.",
        yield_sources=("staking", "parachain_bonds"),
    ),
    "AVAX": AssetProfile(
        symbol="AVAX",
        category="large_cap",
        tier="tier_professional",
        baseline_return=0.20,
        volatility=0.92,
        staking_yield=0.075,
        notes="Subnet incentives and validator staking yields.",
        yield_sources=("staking",),
    ),
    "MATIC": AssetProfile(
        symbol="MATIC",
        category="large_cap",
        tier="tier_professional",
        baseline_return=0.19,
        volatility=0.88,
        staking_yield=0.055,
        notes="Polygon staking plus DeFi liquidity programs.",
        yield_sources=("staking", "liquidity_mining"),
    ),
    "ATOM": AssetProfile(
        symbol="ATOM",
        category="large_cap",
        tier="tier_professional",
        baseline_return=0.19,
        volatility=0.90,
        staking_yield=0.11,
        notes="Cosmos hub staking with liquid staking availability.",
        yield_sources=("staking", "airdrop_rewards"),
    ),
    "NEAR": AssetProfile(
        symbol="NEAR",
        category="large_cap",
        tier="tier_professional",
        baseline_return=0.18,
        volatility=0.95,
        staking_yield=0.1,
        notes="Nightshade sharded L1 with liquid staking providers.",
        yield_sources=("staking",),
    ),
    "FTM": AssetProfile(
        symbol="FTM",
        category="mid_cap",
        tier="tier_retail",
        baseline_return=0.21,
        volatility=1.05,
        staking_yield=0.09,
        notes="Opera chain validators provide competitive staking rewards.",
        yield_sources=("staking",),
    ),
    "TRX": AssetProfile(
        symbol="TRX",
        category="large_cap",
        tier="tier_professional",
        baseline_return=0.14,
        volatility=0.65,
        staking_yield=0.06,
        notes="Resource staking via Tron energy/bandwidth model.",
        yield_sources=("staking", "lending"),
    ),
    "LTC": AssetProfile(
        symbol="LTC",
        category="large_cap",
        tier="tier_professional",
        baseline_return=0.13,
        volatility=0.60,
        staking_yield=0.0,
        notes="Mature UTXO asset, primarily price appreciation driven.",
        yield_sources=("lending",),
    ),
    "XRP": AssetProfile(
        symbol="XRP",
        category="large_cap",
        tier="tier_institutional",
        baseline_return=0.12,
        volatility=0.55,
        staking_yield=0.0,
        notes="Cross-border payments token with institutional flows.",
        yield_sources=("lending",),
    ),
    # DeFi governance tokens
    "UNI": AssetProfile(
        symbol="UNI",
        category="defi",
        tier="tier_professional",
        baseline_return=0.16,
        volatility=0.95,
        staking_yield=0.0,
        notes="DEX governance token with fee switch potential.",
        yield_sources=("liquidity_mining", "governance_incentives"),
    ),
    "AAVE": AssetProfile(
        symbol="AAVE",
        category="defi",
        tier="tier_professional",
        baseline_return=0.17,
        volatility=0.90,
        staking_yield=0.08,
        notes="Safety module staking and protocol fee accrual.",
        yield_sources=("staking", "lending"),
    ),
    "MKR": AssetProfile(
        symbol="MKR",
        category="defi",
        tier="tier_professional",
        baseline_return=0.15,
        volatility=0.80,
        staking_yield=0.0,
        notes="Maker buyback and burn driven by DAI stability fees.",
        yield_sources=("fee_sharing",),
    ),
    "SNX": AssetProfile(
        symbol="SNX",
        category="defi",
        tier="tier_retail",
        baseline_return=0.19,
        volatility=1.05,
        staking_yield=0.12,
        notes="Synthetic asset protocol with high staking incentives.",
        yield_sources=("staking", "inflationary_rewards"),
    ),
    "CRV": AssetProfile(
        symbol="CRV",
        category="defi",
        tier="tier_retail",
        baseline_return=0.15,
        volatility=1.0,
        staking_yield=0.14,
        notes="Curve vote-escrow boosts and emission rewards.",
        yield_sources=("staking", "liquidity_mining"),
    ),
    "COMP": AssetProfile(
        symbol="COMP",
        category="defi",
        tier="tier_retail",
        baseline_return=0.15,
        volatility=0.95,
        staking_yield=0.0,
        notes="Lending governance with fee sharing proposals.",
        yield_sources=("liquidity_mining",),
    ),
    "SUSHI": AssetProfile(
        symbol="SUSHI",
        category="defi",
        tier="tier_retail",
        baseline_return=0.17,
        volatility=1.1,
        staking_yield=0.10,
        notes="DEX token with xSUSHI fee sharing.",
        yield_sources=("staking", "liquidity_mining"),
    ),
    "CAKE": AssetProfile(
        symbol="CAKE",
        category="defi",
        tier="tier_retail",
        baseline_return=0.16,
        volatility=1.05,
        staking_yield=0.11,
        notes="BNB Chain DEX token with flexible syrup pool yields.",
        yield_sources=("staking", "liquidity_mining"),
    ),
    "LDO": AssetProfile(
        symbol="LDO",
        category="defi",
        tier="tier_retail",
        baseline_return=0.17,
        volatility=0.95,
        staking_yield=0.0,
        notes="Liquid staking governance exposure.",
        yield_sources=("governance_incentives",),
    ),
    # Stablecoins
    "USDC": AssetProfile(
        symbol="USDC",
        category="stablecoin",
        tier="tier_institutional",
        baseline_return=0.0,
        volatility=0.02,
        staking_yield=0.04,
        notes="Reserve-backed stablecoin with treasury bill yields via CeFi/DeFi lending.",
        yield_sources=("lending", "treasury_bills"),
    ),
    "USDT": AssetProfile(
        symbol="USDT",
        category="stablecoin",
        tier="tier_institutional",
        baseline_return=0.0,
        volatility=0.03,
        staking_yield=0.035,
        notes="Most liquid stablecoin; CeFi/DeFi lending and liquidity pools.",
        yield_sources=("lending", "liquidity_pools"),
    ),
    "DAI": AssetProfile(
        symbol="DAI",
        category="stablecoin",
        tier="tier_professional",
        baseline_return=0.0,
        volatility=0.025,
        staking_yield=0.045,
        notes="Maker savings rate and DeFi lending opportunities.",
        yield_sources=("staking", "lending"),
    ),
    "BUSD": AssetProfile(
        symbol="BUSD",
        category="stablecoin",
        tier="tier_enterprise",
        baseline_return=0.0,
        volatility=0.02,
        staking_yield=0.03,
        notes="Exchange-backed stablecoin with cash-equivalent reserves.",
        yield_sources=("lending", "exchange_yield"),
    ),
    "TUSD": AssetProfile(
        symbol="TUSD",
        category="stablecoin",
        tier="tier_professional",
        baseline_return=0.0,
        volatility=0.025,
        staking_yield=0.035,
        notes="Regulated stablecoin used in CeFi and DeFi markets.",
        yield_sources=("lending",),
    ),
    "FRAX": AssetProfile(
        symbol="FRAX",
        category="stablecoin",
        tier="tier_retail",
        baseline_return=0.0,
        volatility=0.03,
        staking_yield=0.06,
        notes="Fractional-algorithmic stablecoin with staking and liquidity incentives.",
        yield_sources=("staking", "liquidity_mining"),
    ),
}

DEFAULT_ASSET_PROFILE = AssetProfile(
    symbol="GENERIC",
    category="altcoin",
    tier="tier_retail",
    baseline_return=DEFAULT_EXPECTED_RETURN,
    volatility=DEFAULT_VOLATILITY,
    staking_yield=0.0,
    notes="Estimated from diversified altcoin basket.",
)


def get_asset_profile(symbol: str) -> AssetProfile:
    """Return a static asset profile with sane defaults if unknown."""
    if not symbol:
        return DEFAULT_ASSET_PROFILE
    return ASSET_PROFILES.get(symbol.upper(), DEFAULT_ASSET_PROFILE)


YIELD_PRODUCT_CATALOG: Dict[str, List[Dict[str, object]]] = {
    "ETH": [
        {
            "product": "Ethereum Native Staking",
            "type": "staking",
            "estimated_apy": 0.045,
            "lockup": "Validator exit queue (variable)",
            "yield_sources": ["execution_layer_rewards", "consensus_layer_rewards"],
            "risks": ["Slashing if validator misbehaves", "Smart contract risk for liquid staking"],
        },
        {
            "product": "Aave Lending (stETH/ETH)",
            "type": "lending",
            "estimated_apy": 0.03,
            "lockup": "Flexible",
            "yield_sources": ["borrower_interest"],
            "risks": ["Smart contract risk", "Liquidity risk during market stress"],
        },
    ],
    "SOL": [
        {
            "product": "Solana Validator Staking",
            "type": "staking",
            "estimated_apy": 0.07,
            "lockup": "~2-3 days warmup/cooldown",
            "yield_sources": ["inflationary_rewards"],
            "risks": ["Validator downtime", "Slashing"],
        },
    ],
    "DOT": [
        {
            "product": "Polkadot NPoS Staking",
            "type": "staking",
            "estimated_apy": 0.08,
            "lockup": "28 day unbonding",
            "yield_sources": ["inflationary_rewards"],
            "risks": ["Slashing", "Nominator selection risk"],
        }
    ],
    "AVAX": [
        {
            "product": "Avalanche Validator Staking",
            "type": "staking",
            "estimated_apy": 0.075,
            "lockup": "14 day minimum",
            "yield_sources": ["staking_rewards"],
            "risks": ["Validator downtime", "Token lockup"],
        }
    ],
    "ATOM": [
        {
            "product": "Cosmos Hub Staking",
            "type": "staking",
            "estimated_apy": 0.11,
            "lockup": "21 day unbonding",
            "yield_sources": ["inflationary_rewards"],
            "risks": ["Slashing", "Validator reliability"],
        }
    ],
    "USDC": [
        {
            "product": "CeFi Savings / Treasury Bills",
            "type": "yield_bearing_stable",
            "estimated_apy": 0.04,
            "lockup": "1-7 days",
            "yield_sources": ["treasury_bill_yield", "repo_markets"],
            "risks": ["Counterparty risk", "Regulatory risk"],
        },
        {
            "product": "Aave Lending (USDC)",
            "type": "lending",
            "estimated_apy": 0.035,
            "lockup": "Flexible",
            "yield_sources": ["borrower_interest"],
            "risks": ["Smart contract risk", "Utilization risk"],
        },
    ],
    "USDT": [
        {
            "product": "Centralized Lending Desks",
            "type": "lending",
            "estimated_apy": 0.035,
            "lockup": "7-30 days",
            "yield_sources": ["institutional_borrowers"],
            "risks": ["Counterparty risk", "Transparency concerns"],
        }
    ],
    "DAI": [
        {
            "product": "Maker DAI Savings Rate (DSR)",
            "type": "staking",
            "estimated_apy": 0.045,
            "lockup": "Flexible",
            "yield_sources": ["stability_fees", "protocol_reserves"],
            "risks": ["Smart contract risk", "Peg stability"],
        }
    ],
    "AAVE": [
        {
            "product": "AAVE Safety Module Staking",
            "type": "staking",
            "estimated_apy": 0.08,
            "lockup": "10 day cooldown",
            "yield_sources": ["protocol_fees", "staking_rewards"],
            "risks": ["Slashing in protocol shortfall", "Smart contract risk"],
        }
    ],
    "SNX": [
        {
            "product": "Synthetix Staking",
            "type": "staking",
            "estimated_apy": 0.12,
            "lockup": "1 week claim cycles",
            "yield_sources": ["inflationary_rewards", "trading_fees"],
            "risks": ["Debt pool exposure", "Smart contract risk"],
        }
    ],
}


DEFI_PROTOCOL_MAPPINGS: Dict[str, str] = {
    "UNI": "uniswap",
    "AAVE": "aave",
    "MKR": "makerdao",
    "SNX": "synthetix",
    "CRV": "curve",
    "COMP": "compound",
    "SUSHI": "sushiswap",
    "CAKE": "pancakeswap",
    "LDO": "lido",
    "YFI": "yearn-finance",
    "GMX": "gmx",
}


def get_yield_products(symbol: str) -> List[Dict[str, object]]:
    """Return configured yield-bearing products for a symbol."""
    if not symbol:
        return []
    return YIELD_PRODUCT_CATALOG.get(symbol.upper(), [])

