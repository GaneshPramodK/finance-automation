# Financial Category Library

This document defines the standard categories for transaction classification. The LLM should map bank descriptions to exactly one of these categories.

## Expense Categories
- **Food & Dining** (Restaurants, hawker centers, fast food, cafe, delivery services like GrabFood)
- **Groceries** (Supermarkets, convenience stores, fresh markets)
- **Transport** (Public transport, ride-hailing/Grab, taxi, petrol, parking, tolls)
- **Shopping** (Clothing, electronics, gifts, online shopping like Shopee/Lazada)
- **Utilities** (Electricity, water, internet, phone bills)
- **Health & Wellness** (Pharmacy, doctor, gym, spa, sports equipment)
- **Entertainment** (Movies, streaming subscriptions like Netflix/Spotify, games)
- **Housing** (Rent, maintenance fee, furniture, repairs)
- **Education** (Courses, books, school fees)
- **Insurance** (Life, medical, car insurance premiums)
- **Travel** (Flights, hotels, overseas spending)
- **Misc** (Charity, unidentifiable expenses, one-off odd items)

## Income Categories
- **Salary** (Payroll, monthly wages)
- **Reimbursement** (Claims, refunds)
- **Investment** (Dividends, interest, capital gains)
- **Transfer** (Transfers between own accounts)

## Exclusion
- **Payment** (Credit card bill payments - these are transfers, not expenses)
