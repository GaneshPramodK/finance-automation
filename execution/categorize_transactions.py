import json
import logging
import pandas as pd
from pathlib import Path
from categorizer import GeminiCategorizer

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    base_dir = Path(__file__).parent.parent
    input_csv = base_dir / "data" / "stubs" / "extracted_transactions.csv"
    output_json = base_dir / "logs" / "categorized_results.json"
    review_csv = base_dir / "logs" / "review_needed.csv"

    if not input_csv.exists():
        logging.error(f"Input file not found: {input_csv}")
        return

    # Load Transactions
    try:
        df = pd.read_csv(input_csv)
        logging.info(f"Loaded {len(df)} transactions from {input_csv.name}")
    except Exception as e:
        logging.error(f"Failed to read CSV: {e}")
        return

    if df.empty:
        logging.warning("DataFrame is empty. Nothing to categorize.")
        return

    # Initialize Categorizer
    # We use the persistent map in data/
    categorizer = GeminiCategorizer(map_file=base_dir / "data" / "category_map.json")
    
    # Run Categorization
    try:
        df_result = categorizer.categorize_dataframe(df, description_col="description")
    except Exception as e:
        logging.error(f"Categorization failed: {e}")
        return

    # Format Output for update_master_sheet.py
    # Schema expected: date, description, amount, category, sub_category, id
    # DataFrame has: id, date, description, amount, Category, Sub-Category
    
    records = []
    for _, row in df_result.iterrows():
        record = {
            "id": str(row.get("id", "")),
            "date": str(row.get("date", "")),
            "description": str(row.get("description", "")),
            "amount": str(row.get("amount", "")),
            "category": str(row.get("Category", "Unclassified")),
            "sub_category": str(row.get("Sub-Category", "General"))
        }
        records.append(record)

    # Save JSON
    with open(output_json, "w") as f:
        json.dump(records, f, indent=4)
    logging.info(f"Saved {len(records)} categorized records to {output_json}")

    # Save Review CSV (Backup/Audit)
    # We save the whole enriched dataframe for review
    backup_csv = base_dir / "02_Archive" / "csv_backups" / "latest_categorized.csv"
    backup_csv.parent.mkdir(parents=True, exist_ok=True)
    df_result.to_csv(backup_csv, index=False)
    logging.info(f"Saved backup to {backup_csv}")

    # Check for Unclassified
    unclassified = df_result[df_result["Category"] == "Unclassified"]
    if not unclassified.empty:
        unclassified.to_csv(review_csv, index=False)
        logging.warning(f"Detected {len(unclassified)} unclassified items. Saved to {review_csv}")

if __name__ == "__main__":
    main()
