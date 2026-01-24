import json
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pathlib import Path

def setup_logging(log_dir):
    log_path = Path(log_dir) / "sheet_update.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )

def get_drive_service(key_path):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(str(key_path), scope)
    client = gspread.authorize(creds)
    return client

def update_master_record(categorized_data_path, config):
    try:
        # Load Config Paths
        master_sheet_path = config["drive_paths"]["master_record"]
        # Extract filename (assuming it's a file path in G: drive, but we need the Sheet Names for API)
        # Note: For gspread, we typically access by Title or URL. The config has a file system path.
        # We will try to extract the base name "Ganesh_Expense_Master" or let the user define the TITLE in config.
        # For now, we'll assume the filename stem is the sheet title.
        sheet_title = Path(master_sheet_path).stem
        
        base_dir = Path(__file__).parent.parent
        key_path = base_dir / "data" / "keys" / "service_account.json"
        
        if not key_path.exists():
            logging.error(f"Service account key not found at {key_path}")
            return

        logging.info("Connecting to Google Drive...")
        client = get_drive_service(key_path)
        
        logging.info(f"Opening spreadsheet: {sheet_title}")
        sheet = client.open(sheet_title).sheet1 # Assumes first sheet
        
        # Load Data to Append
        with open(categorized_data_path, "r") as f:
            data = json.load(f)
            
        if not data:
            logging.info("No data to update.")
            return

        # Fetch Existing Data to Check IDs
        # We assume "ID" is the LAST column (or we can search for it).
        # Let's verify headers.
        
        # Schema Definition
        EXPECTED_HEADERS = ["Date", "Description", "Category", "Amount", "Sub-Category", "ID"]
        
        # Get all values
        all_values = sheet.get_all_values()
        
        if not all_values:
            # Empty sheet, set headers
            sheet.append_row(EXPECTED_HEADERS)
            existing_ids = set()
            header_map = {h.lower(): i for i, h in enumerate(EXPECTED_HEADERS)}
        else:
            current_headers = all_values[0]
            # REPAIR: If headers look broken or empty, fix them.
            if not current_headers or current_headers[0].strip() == "ID" or current_headers != EXPECTED_HEADERS:
                logging.warning("Detecting broken or out-of-order headers. Repairing...")
                sheet.update("A1:F1", [EXPECTED_HEADERS])
                header_map = {h.lower(): i for i, h in enumerate(EXPECTED_HEADERS)}
            else:
                 header_map = {h.lower(): i for i, h in enumerate(current_headers)}
            
            # If ID not in map, append it (fallback safety)
            if "id" not in header_map:
                logging.info("Appending ID column header...")
                col_idx = len(current_headers) + 1
                sheet.update_cell(1, col_idx, "ID")
                header_map["id"] = col_idx - 1
            
            # Extract IDs
            id_idx = header_map.get("id", 5)
            existing_ids = set()
            for row in all_values[1:]:
                if len(row) > id_idx:
                    val = str(row[id_idx]).strip()
                    if val: existing_ids.add(val)

        # Prepare rows to append
        rows_to_append = []
        skipped_count = 0
        
        for entry in data:
            tx_id = str(entry.get("id", ""))
            
            if tx_id in existing_ids:
                skipped_count += 1
                continue
            
            # Alignment: Date | Desc | Category | Amt | Sub | ID
            rows_to_append.append([
                entry.get("date"),
                entry.get("description"),
                entry.get("category"),
                entry.get("amount"),
                entry.get("sub_category"),
                tx_id
            ])
            
        if rows_to_append:
            logging.info(f"Appending {len(rows_to_append)} new rows (Skipped {skipped_count} duplicates)...")
            sheet.append_rows(rows_to_append)
            logging.info("Update successful!")
        else:
            logging.info(f"No new rows to append. Skipped {skipped_count} duplicates.")

    except Exception as e:
        logging.error(f"Failed to update Master Sheet: {e}")

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    log_dir = base_dir / "logs"
    setup_logging(log_dir)
    
    config_path = base_dir / "config.json"
    with open(config_path, "r") as f:
        config = json.load(f)

    categorized_data = log_dir / "categorized_results.json"
    update_master_record(categorized_data, config)
