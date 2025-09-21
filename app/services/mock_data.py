"""
Mock data service for when database is unavailable.
Provides realistic fake data for development/testing.
"""

import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any
from decimal import Decimal

class MockDataService:
    """Provides mock data when database is unavailable."""

    def __init__(self):
        self.mock_portfolio = self._generate_mock_portfolio()
        self.mock_positions = self._generate_mock_positions()
        self.mock_trades = self._generate_mock_trades()

    def _generate_mock_portfolio(self) -> Dict[str, Any]:
        """Generate realistic portfolio data"""
        return {
            "total_value": Decimal("125487.50"),
            "available_balance": Decimal("15420.25"),
            "total_pnl": Decimal("12487.50"),
            "daily_pnl": Decimal("2847.30"),
            "daily_pnl_pct": 2.32,
            "total_pnl_pct": 11.04,
            "margin_used": Decimal("45200.00"),
            "margin_available": Decimal("80287.50"),
            "risk_score": 6.8,
            "active_orders": 7
        }

    def _generate_mock_positions(self) -> List[Dict[str, Any]]:
        """Generate realistic trading positions"""
        positions = [
            {
                "symbol": "BTC",
                "name": "Bitcoin",
                "amount": 2.15,
                "value_usd": 67425.80,
                "entry_price": 29800.50,
                "current_price": 31350.25,
                "change_24h_pct": 3.45,
                "unrealized_pnl": 3333.23,
                "side": "long",
                "exchange": "binance"
            },
            {
                "symbol": "ETH",
                "name": "Ethereum",
                "amount": 15.75,
                "value_usd": 25200.15,
                "entry_price": 1580.25,
                "current_price": 1600.01,
                "change_24h_pct": 1.25,
                "unrealized_pnl": 311.49,
                "side": "long",
                "exchange": "binance"
            },
            {
                "symbol": "ADA",
                "name": "Cardano",
                "amount": 12000,
                "value_usd": 4800.00,
                "entry_price": 0.42,
                "current_price": 0.40,
                "change_24h_pct": -4.76,
                "unrealized_pnl": -240.00,
                "side": "long",
                "exchange": "kraken"
            },
            {
                "symbol": "SOL",
                "name": "Solana",
                "amount": 125.5,
                "value_usd": 18825.75,
                "entry_price": 148.20,
                "current_price": 150.00,
                "change_24h_pct": 1.21,
                "unrealized_pnl": 225.90,
                "side": "long",
                "exchange": "binance"
            },
            {
                "symbol": "LINK",
                "name": "Chainlink",
                "amount": 800,
                "value_usd": 9600.00,
                "entry_price": 12.50,
                "current_price": 12.00,
                "change_24h_pct": -4.00,
                "unrealized_pnl": -400.00,
                "side": "long",
                "exchange": "coinbase"
            }
        ]
        return positions

    def _generate_mock_trades(self) -> List[Dict[str, Any]]:
        """Generate realistic recent trades"""
        trades = []
        symbols = ["BTC", "ETH", "ADA", "SOL", "LINK", "DOT", "MATIC"]

        for i in range(15):
            symbol = random.choice(symbols)
            side = random.choice(["buy", "sell"])
            amount = round(random.uniform(0.1, 10.0), 3)
            price = round(random.uniform(100, 50000), 2)
            pnl = round(random.uniform(-500, 1200), 2)

            trade = {
                "id": i + 1,
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": price,
                "time": (datetime.now() - timedelta(hours=random.randint(1, 72))).isoformat(),
                "status": random.choice(["completed", "completed", "completed", "pending"]),
                "pnl": pnl
            }
            trades.append(trade)

        return sorted(trades, key=lambda x: x["time"], reverse=True)

    def get_portfolio_data(self, user_id: str) -> Dict[str, Any]:
        """Get mock portfolio data"""
        return {
            "success": True,
            **self.mock_portfolio,
            "positions": self.mock_positions
        }

    def get_credits_balance(self, user_id: str) -> Dict[str, Any]:
        """Get mock credits balance"""
        return {
            "success": True,
            "balance": Decimal("2500.00"),
            "used": Decimal("1247.50"),
            "available": Decimal("1252.50"),
            "transactions": [
                {
                    "id": 1,
                    "amount": Decimal("500.00"),
                    "type": "purchase",
                    "description": "Credit purchase",
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "id": 2,
                    "amount": Decimal("-247.50"),
                    "type": "usage",
                    "description": "Trading fees",
                    "timestamp": (datetime.now() - timedelta(hours=2)).isoformat()
                }
            ]
        }

    def get_recent_trades(self, user_id: str) -> List[Dict[str, Any]]:
        """Get mock recent trades"""
        return self.mock_trades

    def get_market_data(self) -> List[Dict[str, Any]]:
        """Get mock market data"""
        symbols = ["BTC", "ETH", "ADA", "SOL", "LINK", "DOT", "MATIC", "AVAX"]
        market_data = []

        for symbol in symbols:
            price = round(random.uniform(0.1, 50000), 2)
            change = round(random.uniform(-10, 15), 2)
            volume = f"{random.randint(10, 999)}M"

            market_data.append({
                "symbol": symbol,
                "price": price,
                "change": change,
                "volume": volume
            })

        return market_data

    def get_exchanges_list(self, user_id: str) -> List[Dict[str, Any]]:
        """Get mock exchanges list"""
        return [
            {
                "id": 1,
                "name": "Binance",
                "status": "connected",
                "balance_usd": 89650.25,
                "last_sync": datetime.now().isoformat()
            },
            {
                "id": 2,
                "name": "Kraken",
                "status": "connected",
                "balance_usd": 25420.75,
                "last_sync": (datetime.now() - timedelta(minutes=5)).isoformat()
            },
            {
                "id": 3,
                "name": "Coinbase",
                "status": "connected",
                "balance_usd": 10416.50,
                "last_sync": (datetime.now() - timedelta(minutes=2)).isoformat()
            }
        ]

# Global instance
mock_data_service = MockDataService()