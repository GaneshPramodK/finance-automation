# Resolution Log & Regression Tests

This document tracks resolved issues to prevent recurrence.

## 1. Date Standardization
*   **Issue**: Dates were mixed formats (DD/MM vs ISO).
*   **Fix**: Rewrote `execution/parse_statement.py` to enforce `YYYY-MM-DD`.
*   **Check**: Output CSV must always have `20XX-XX-XX` format.

## 2. Text Extraction & Regex
*   **Issue**: "RTL MGMT CHRG RATE =" parsed incorrectly as expense.
*   **Issue**: User suspected missing transactions.
*   **Fix**: 
    *   Implemented multi-line parsing with `x_tolerance=1` to fix column merging.
    *   Regex now enforces amount at End-Of-Line, correctly dropping "RTL... 17.00%" which is non-monetary.
    *   **Verification**: Sum of extracted debits (32.70 + 55.08 + 263.33 + 10.00 + 30.90 = **392.01**) matches statement "TOTAL DEBIT THIS MONTH 392.01". Data is complete.
*   **Check**:
    *   Verify count of transactions matches visual inspection.
    *   Verify "RTL MGMT CHRG" description captures full text and correct amount.

## 3. Categorization
*   **Issue**: "Unclassified" transactions due to LLM errors.
*   **Fix**: Implemented `GeminiCategorizer` with batching and `gemini-flash-latest`.
*   **Check**: `categorized_results.json` should have `Sub-Category` field.
