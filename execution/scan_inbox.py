import json
import logging
import os
from pathlib import Path

def setup_logging(log_dir):
    """Sets up logging to both file and console."""
    log_path = Path(log_dir) / "inbox_scan.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )

def load_config(config_path):
    """Loads the main configuration file."""
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found at {config_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from {config_path}")
        return None

def scan_inbox():
    """Scans the configured inbox for PDF files."""
    base_dir = Path(__file__).parent.parent
    config_path = base_dir / "config.json"
    
    config = load_config(config_path)
    if not config:
        return

    inbox_path_str = config["drive_paths"].get("inbox")
    if not inbox_path_str:
        logging.error("Inbox path not defined in config.json")
        return

    inbox_path = Path(inbox_path_str)
    log_dir = base_dir / "logs"
    setup_logging(log_dir)

    logging.info(f"Scanning inbox: {inbox_path}")

    if not inbox_path.exists():
        logging.error(f"Inbox path does not exist: {inbox_path}")
        return

    pdf_files = [f for f in inbox_path.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"]

    if not pdf_files:
        logging.info("No new PDF files detected.")
    else:
        logging.info(f"Detected {len(pdf_files)} PDF file(s):")
        for pdf in pdf_files:
            logging.info(f" - {pdf.name}")

if __name__ == "__main__":
    scan_inbox()
