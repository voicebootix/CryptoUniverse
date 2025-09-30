# Credit System & Platform Audit Summary

This document captures the key findings from the automated review of the CryptoUniverse platform and deployed Render instance.

## Observations

1. The FastAPI credit balance endpoint returns balances, but profit-potential and transaction-history endpoints surface inconsistencies: profit potential returns `0` despite a non-zero balance, and transaction history fails because the database schema is missing the `provider` column expected by the ORM model.
2. Several backend services (credit purchase allocation, profit-sharing, Telegram bot) expect `CreditAccount.total_purchased_credits`/`total_used_credits`, yet the model defines only `total_credits` and `used_credits`, leading to runtime errors and inconsistent metrics.
3. The unified chat service enforces a apparently static 10-credit requirement but never deducts credits for chat-initiated operations, so credit usage for chats/signals is not implemented.
4. The frontend credit dashboard relies on static subscription/credit pack data and assumes backend fields (`total_purchased_credits`, `total_used_credits`) that are unavailable, so the UI cannot reflect real credit consumption.
5. Database migrations (e.g., provider column) appear out of sync with the deployed database, indicating that migration execution must be revisited before relying on the credit transaction ledger.

## Recommendations

- Align the `CreditAccount` schema and migrations with the fields that the services and frontend require (e.g., `total_purchased_credits`, `total_used_credits`).
- Rebuild the profit-potential calculations to derive values from actual credit purchases/usage, and ensure migrations add the missing columns used in those calculations.
- Extend the unified chat workflow to log and deduct credits for chargeable interactions, and integrate that logic with both API and Telegram flows.
- Replace static frontend credit center data with live responses from `/credits/balance`, `/credits/purchase-options`, and `/credits/transaction-history` once backend responses are accurate.
- Audit and replay Alembic migrations on the production database so that ORM expectations match the persisted schema, preventing 500-level errors on credit APIs.

