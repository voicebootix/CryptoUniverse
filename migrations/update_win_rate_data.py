"""
Migration script to ensure win rate data consistency after standardization.

This script:
1. Identifies win_rate values that might be stored as fractions in the DB
2. Converts them to the expected 0-100% format for DB storage
3. Validates all win_rate values are within the 0-100 range
4. Reports any data inconsistencies found
"""

import asyncio
from decimal import Decimal
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_database
from app.models.market_data import StrategyPerformanceHistory, BacktestResult


async def validate_and_fix_win_rates():
    """Validate and fix win rate data in the database."""
    async for db in get_database():
        await validate_strategy_performance_history(db)
        await validate_backtest_results(db)
        print("✅ Win rate data validation and fixes completed")


async def validate_strategy_performance_history(db: AsyncSession):
    """Validate and fix StrategyPerformanceHistory win rates."""
    print("🔍 Checking StrategyPerformanceHistory win rates...")

    # Find all records with potentially problematic win rates
    stmt = select(StrategyPerformanceHistory).where(
        StrategyPerformanceHistory.win_rate.isnot(None)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    fixed_count = 0
    suspicious_count = 0

    for record in records:
        win_rate = float(record.win_rate)

        # If win_rate is between 0-1 (likely stored as fraction), convert to percentage
        if 0 < win_rate <= 1.0 and win_rate != 1.0:  # Exclude exactly 1.0 which could be 100%
            # This looks like a fraction that should be converted to percentage
            new_win_rate = Decimal(str(win_rate * 100))
            record.win_rate = new_win_rate
            fixed_count += 1
            print(f"  Fixed: {win_rate} → {new_win_rate}% for strategy {record.strategy_id}")

        # Flag values outside expected ranges
        elif win_rate > 100 or win_rate < 0:
            suspicious_count += 1
            print(f"  ⚠️  Suspicious value: {win_rate}% for strategy {record.strategy_id}")

    if fixed_count > 0:
        await db.commit()
        print(f"✅ Fixed {fixed_count} StrategyPerformanceHistory records")

    if suspicious_count > 0:
        print(f"⚠️  Found {suspicious_count} suspicious values that need manual review")


async def validate_backtest_results(db: AsyncSession):
    """Validate and fix BacktestResult win rates."""
    print("🔍 Checking BacktestResult win rates...")

    # Find all records with potentially problematic win rates
    stmt = select(BacktestResult).where(
        BacktestResult.win_rate.isnot(None)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    fixed_count = 0
    suspicious_count = 0

    for record in records:
        win_rate = float(record.win_rate)

        # If win_rate is between 0-1 (likely stored as fraction), convert to percentage
        if 0 < win_rate <= 1.0 and win_rate != 1.0:  # Exclude exactly 1.0 which could be 100%
            # This looks like a fraction that should be converted to percentage
            new_win_rate = Decimal(str(win_rate * 100))
            record.win_rate = new_win_rate
            fixed_count += 1
            print(f"  Fixed: {win_rate} → {new_win_rate}% for backtest {record.id}")

        # Flag values outside expected ranges
        elif win_rate > 100 or win_rate < 0:
            suspicious_count += 1
            print(f"  ⚠️  Suspicious value: {win_rate}% for backtest {record.id}")

    if fixed_count > 0:
        await db.commit()
        print(f"✅ Fixed {fixed_count} BacktestResult records")

    if suspicious_count > 0:
        print(f"⚠️  Found {suspicious_count} suspicious values that need manual review")


async def generate_validation_report():
    """Generate a report of current win rate distributions."""
    print("\n📊 Win Rate Distribution Report")
    print("=" * 50)

    async for db in get_database():
        # StrategyPerformanceHistory stats
        stmt = select(StrategyPerformanceHistory).where(
            StrategyPerformanceHistory.win_rate.isnot(None)
        )
        result = await db.execute(stmt)
        records = result.scalars().all()

        if records:
            win_rates = [float(r.win_rate) for r in records]
            print(f"\nStrategyPerformanceHistory ({len(win_rates)} records):")
            print(f"  Min: {min(win_rates):.2f}%")
            print(f"  Max: {max(win_rates):.2f}%")
            print(f"  Avg: {sum(win_rates)/len(win_rates):.2f}%")

            # Count distributions
            fraction_like = len([w for w in win_rates if 0 < w <= 1.0])
            normal_percent = len([w for w in win_rates if 1 < w <= 100])
            suspicious = len([w for w in win_rates if w > 100 or w < 0])

            print(f"  Fraction-like (0-1): {fraction_like}")
            print(f"  Normal percent (1-100): {normal_percent}")
            print(f"  Suspicious (>100 or <0): {suspicious}")

        # BacktestResult stats
        stmt = select(BacktestResult).where(
            BacktestResult.win_rate.isnot(None)
        )
        result = await db.execute(stmt)
        records = result.scalars().all()

        if records:
            win_rates = [float(r.win_rate) for r in records]
            print(f"\nBacktestResult ({len(win_rates)} records):")
            print(f"  Min: {min(win_rates):.2f}%")
            print(f"  Max: {max(win_rates):.2f}%")
            print(f"  Avg: {sum(win_rates)/len(win_rates):.2f}%")

            # Count distributions
            fraction_like = len([w for w in win_rates if 0 < w <= 1.0])
            normal_percent = len([w for w in win_rates if 1 < w <= 100])
            suspicious = len([w for w in win_rates if w > 100 or w < 0])

            print(f"  Fraction-like (0-1): {fraction_like}")
            print(f"  Normal percent (1-100): {normal_percent}")
            print(f"  Suspicious (>100 or <0): {suspicious}")


async def main():
    """Main migration function."""
    print("🚀 Starting Win Rate Data Migration")
    print("=" * 40)

    # First, generate a report of current state
    await generate_validation_report()

    # Ask for confirmation before making changes
    print("\n" + "=" * 40)
    print("This migration will:")
    print("1. Convert fraction values (0-1) to percentages (0-100)")
    print("2. Flag suspicious values for manual review")
    print("3. Preserve valid percentage values as-is")

    response = input("\nProceed with migration? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Migration cancelled")
        return

    # Perform the migration
    await validate_and_fix_win_rates()

    # Generate final report
    print("\n" + "=" * 40)
    print("📊 Post-Migration Report:")
    await generate_validation_report()

    print("\n✅ Migration completed successfully!")
    print("\nNext steps:")
    print("1. Review any suspicious values flagged above")
    print("2. Run tests: python -m pytest tests/test_win_rate_standardization.py")
    print("3. Deploy the updated code with standardized win rate handling")


if __name__ == "__main__":
    asyncio.run(main())