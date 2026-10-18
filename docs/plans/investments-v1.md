# Investments v1 - Plan

## Goal
Replace the investments spreadsheet with the app. Every number the spreadsheet shows
(balance, movement, profit, % per account per month, and the totals) comes from the API.

## Design

| Concept | Stored as |
|---|---|
| Investment | `Account` with `type="investment"` |
| Money in | `income` transaction on that account |
| Money out | `expense` transaction on that account |
| Opening balance | The account's first `BalancePoint` |
| Monthly closing (what the broker shows) | A `BalancePoint` on the last day of the month |

Calculated on read, never stored:

```
start     = previous month's closing
movement  = income − expense in the month
profit    = closing − start − movement
%         = profit ÷ start

Portfolio (per month): sum of closing, movement and profit across investment accounts
Portfolio %           = total profit ÷ total closing   (same as the spreadsheet's Net Worth row)
```

No new tables. No migration.

## What is reused
- `Broker` - the institution (BTG, Itaú, Rico...).
- `Account` and `AccountType.INVESTMENT` - CRUD, soft delete, `GET /accounts?type=investment`.
- `BalancePoint` table - `UNIQUE(account_id, date)` gives one closing per day.
- `create_opening_balance_point` - already runs on account creation.
- `Transaction` with `income` / `expense` - existing create, edit and bulk endpoints.
- `BalancePointUpsertIn` schema - request body for saving a closing.
- `MonthlyBalanceSummary` schema - response row for the monthly view.

## Tasks

### Phase 1: Balance rule

#### Task 1.1 - Current balance uses the latest balance point [x]
`calculate_account_balance_from_transactions` (balance_points/service.py):
latest balance point + transactions after its date.
Today it is first point + all transactions. Cash accounts only have their opening point,
so their balance does not change.

#### Task 1.2 - Repository queries [x]
- `get_latest_balance_point(account_id, user_id)`
- `get_account_balance_after_date(account_id, user_id, date)`

#### Task 1.3 - Timeline uses the same rule [x]
`calculate_balance_timeline` resets the running balance on each balance point date.

#### Task 1.4 - Opening date on account creation [x]
Optional `opening_date` on `AccountCreateIn`; `create_account` uses it instead of
`created_at.date()`. Needed to import past years.

### Phase 2: Monthly closing input

#### Task 2.1 - `PUT /balance_points/{account_id}/{date}` [x]
Body: `BalancePointUpsertIn` (`balance`). Creates or replaces the closing on that date.
Only for accounts with `type="investment"` (422 otherwise). Account must belong to the user.

#### Task 2.2 - `DELETE /balance_points/{account_id}/{date}` [x]
Removes a closing entered by mistake. The opening balance can't be deleted.

### Phase 3: Investments domain (no models)

#### Task 3.1 - Create `app/domains/investments/` [x]
`schemas.py`, `service.py`, `router.py`. Register the router at `/investments`.
Move `MonthlyBalanceSummary` here from balance_points/schemas.py.

#### Task 3.2 - Math as pure functions [x]
Input: opening, closings by month, income/expense by month.
Output: one `MonthlyBalanceSummary` per month. A month without a closing returns `has_data=false`.

#### Task 3.3 - `GET /investments/{account_id}/monthly?from=YYYY-MM&to=YYYY-MM` [x]
Per-account rows: start, movement, closing, profit, %. (Spreadsheet images 1 and 2.)

#### Task 3.4 - `GET /investments/portfolio?from=YYYY-MM&to=YYYY-MM` [x]
Every investment account's monthly rows plus one totals row per month.
(Spreadsheet images 3, 4 and 5.)

### Phase 4: Remove broken leftovers

#### Task 4.1 - Remove `POST /accounts/{account_id}/update-balance` [x]
Calls `create_balance_snapshot_from_transactions`, which no longer exists. Replaced by Task 2.1.

#### Task 4.2 - Remove `reports/accounts` [x]
Its queries filter on `BalancePoint.user_id`, a removed column. Replaced by Task 3.4.

#### Task 4.3 - Remove calls to `mark_balance_points_stale_after_transaction_change` [x]
Three calls in transactions/service.py to a method that no longer exists.

### Phase 5: Tests

#### Task 5.1 - Math tests with spreadsheet numbers [x]
- Previdência: opening 11,036 → Jan 11,196 → Feb 11,451 → Mar 11,007, no movement.
  Expect profit 160 / 1.45%, 255 / 2.28%, −444 / −3.88%.
- Itaú Renda Fixa Jan: start 251,567.20, income 4,000, closing 257,523.
  Expect profit 1,955.80 / 0.78%.
- Portfolio Jan totals: closing 585,635, movement −1,735, profit 5,510.80, 0.94%.

#### Task 5.2 - Balance rule tests [x]
- Cash account balance is unchanged (opening + transactions).
- Investment balance = latest closing + transactions after it.

#### Task 5.3 - Endpoint tests [x]
- PUT closing creates, then replaces; rejects non-investment accounts.
- Monthly and portfolio endpoints return the rows above.

## Expected Result
- Monthly routine: type each account's closing, add income/expense when money moved.
- The monthly and portfolio endpoints reproduce every cell of the spreadsheet.
