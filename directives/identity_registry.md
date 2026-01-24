# Identity Registry Directive

## Purpose
This document outlines the standard operating procedure (SOP) for mapping raw bank transaction descriptions to core spending categories. This classification is crucial for accurately calculating the "Investable Surplus" (Income - Expenses).

## Mapping Logic
We use a combination of keyword matching and regular expressions to identify transaction types. Matches are prioritized from specific to general.

### Rules Table Structure
| Pattern (Regex/Keyword) | Category | Sub-Category | Notes |
| :--- | :--- | :--- | :--- |
| `GRAB*` | Transport | Rideshare | Examples: "GRAB* 12345", "GRAB RIDE" |
| `NETFLIX` | Entertainment | Subscription | |
| `SPOTIFY` | Entertainment | Subscription | |
| `NTUC` | Groceries | Supermarket | |
| `MCDONALDS` | Food & Dining | Fast Food | |

## Category List (Investable Surplus Calculation)

### Income
- Salary
- Dividends
- Interest
- Other Income

### Expenses
- **Needs**
    - Housing (Rent/Mortgage)
    - Utilities (Water, Electricity, Internet)
    - Groceries
    - Transport (Public, Rideshare, Fuel)
    - Insurance
    - Healthcare
- **Wants**
    - Food & Dining (Restaurants, Delivery)
    - Entertainment (Subscriptions, Movies, Games)
    - Shopping (Clothing, Gadgets)
    - Travel

### Savings & Investments
- Emergency Fund
- Stocks/ETFs
- Crypto
- Retirement (CPF/Super)

## Unclassified Transactions
Any transaction that does not match a known pattern should be flagged as `Unclassified`. The system should log these to a review file for manual inspection and rule updates.
