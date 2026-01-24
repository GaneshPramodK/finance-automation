import abc
import json
import logging
import re
import hashlib
from pathlib import Path
import pdfplumber

class BankParser(abc.ABC):
    def normalize_transaction(self, date_str, description, amount):
        clean_desc = description.strip().replace("\n", " ")
        clean_amt = amount.strip().replace(",", "")
        # Create ID based on the FULL date string
        tx_id = hashlib.md5(f"{date_str}|{clean_desc}|{clean_amt}".encode()).hexdigest()[:16]
        return {
            "id": tx_id,
            "date": date_str,
            "description": clean_desc,
            "amount": clean_amt 
        }

    @abc.abstractmethod
    def detect(self, text: str) -> bool: pass
    @abc.abstractmethod
    def parse(self, path: Path) -> list: pass
    @abc.abstractmethod
    def get_bank_label(self) -> str: pass
    @abc.abstractmethod
    def get_statement_date(self, path: Path) -> str: pass

class MaybankParser(BankParser):
    def detect(self, text: str) -> bool:
        return "MAYBANK" in text.upper() or "MALAYAN BANKING" in text.upper()
    
    def get_bank_label(self) -> str: return "maybank2u"
    
    def get_statement_date(self, pdf_path: Path) -> str:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = pdf.pages[0].extract_text()
                # Try DD/MM/YY first
                m1 = re.search(r'(\d{2})/(\d{2})/(\d{2})', text)
                if m1:
                    d, m, y = m1.groups()
                    return f"20{y}{m}{d}"
                
                # Try DD MMM YY (e.g., 03 DEC 25)
                m2 = re.search(r'(\d{2})\s+([A-Z]{3})\s+(\d{2})', text)
                if m2:
                    d, m_str, y = m2.groups()
                    months = {'JAN':'01','FEB':'02','MAR':'03','APR':'04','MAY':'05','JUN':'06',
                              'JUL':'07','AUG':'08','SEP':'09','OCT':'10','NOV':'11','DEC':'12'}
                    m = months.get(m_str.upper(), '01')
                    return f"20{y}{m}{d}"
        except: pass
        return "20250101" # Defensive default

    def parse(self, pdf_path: Path) -> list:
        stmt_date = self.get_statement_date(pdf_path)
        s_year = int(stmt_date[:4])
        s_month = int(stmt_date[4:6])
        
        results = []
        # Regex to find START of transaction: Date Date ...
        start_pattern = re.compile(r'^(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.*)')
        # Regex to find Amount at END of a line
        amt_pattern = re.compile(r'([\d,]+\.\d{2})(CR)?\s*$')
        
        current_tx = None
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # strict layout to avoid column merging
                text = page.extract_text(x_tolerance=1) 
                if not text: continue
                
                for line in text.split("\n"):
                    line = line.strip()
                    if not line: continue
                    
                    # 1. Check if line starts with Date (New Transaction)
                    start_match = start_pattern.match(line)
                    if start_match:
                        # If we had an open previous transaction, save it (even if incomplete, we can't do much)
                        # Or checking if it had amount? If not, we drop it or log warning.
                        if current_tx and current_tx.get('amount'):
                            results.append(self.finalize_tx(current_tx, s_year, s_month))
                        
                        d_val, v_val, rest = start_match.groups()
                        current_tx = {
                            "date_str": d_val, 
                            "desc": rest, 
                            "amount": None, 
                            "cr": None
                        }
                        
                        # Check if extraction is complete on this line
                        amt_match = amt_pattern.search(rest)
                        if amt_match:
                            amt_val, cr_flag = amt_match.groups()
                            current_tx["amount"] = amt_val
                            current_tx["cr"] = cr_flag
                            # Strip amount from desc
                            current_tx["desc"] = rest[:amt_match.start()].strip()
                            
                    # 2. Check if continuation (No Date start) -> Append to previous
                    elif current_tx and current_tx["amount"] is None:
                        # Append text to description
                        current_tx["desc"] += " " + line
                        # Check for amount again
                        amt_match = amt_pattern.search(line)
                        if amt_match:
                            amt_val, cr_flag = amt_match.groups()
                            current_tx["amount"] = amt_val
                            current_tx["cr"] = cr_flag
                            # Remove amount from added line part
                            clean_line = line[:amt_match.start()].strip()
                            # Fix the appended part
                            # We added " " + line. Replace with " " + clean_line.
                            # Actually easier: current_tx["desc"] = current_tx["desc"][:-(len(line)+1)] + " " + clean_line
                            # Let's simple robust way:
                            # Re-extract full desc from start? No.
                            # Just strip amount from end of current desc string?
                            # amt_match was on 'line'.
                            # current_tx["desc"] ends with 'line'.
                            new_desc_len = len(current_tx["desc"]) - len(line) + amt_match.start()
                            current_tx["desc"] = current_tx["desc"][:new_desc_len].strip()

        # Add last one
        if current_tx and current_tx.get('amount'):
            results.append(self.finalize_tx(current_tx, s_year, s_month))
            
        return results

    def finalize_tx(self, tx, s_year, s_month):
        d, m = tx["date_str"].split("/")
        m_int = int(m)
        year = s_year
        if s_year > 0 and s_month == 1 and m_int == 12:
            year -= 1
        
        full_date = f"{year}-{m}-{d}" if s_year > 0 else tx["date_str"]
        
        amt = tx["amount"].replace(",", "")
        final_amt = amt if tx["cr"] else f"-{amt}"
        
        return self.normalize_transaction(full_date, tx["desc"], final_amt)

class ParserFactory:
    def __init__(self):
        self.parsers = [MaybankParser()]
    def get_parser(self, path: Path):
        with pdfplumber.open(path) as pdf:
            text = pdf.pages[0].extract_text() or ""
            for p in self.parsers:
                if p.detect(text): return p
        return None

def main():
    base_dir = Path(__file__).parent.parent
    config = json.loads(open(base_dir / "config.json").read())
    inbox = Path(config["drive_paths"]["inbox"])
    archive = Path(config["drive_paths"]["archive"])
    
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    factory = ParserFactory()
    final_data = []
    
    for pdf in inbox.glob("*.pdf"):
        if pdf.name == "stub_statement.pdf": continue
        parser = factory.get_parser(pdf)
        if parser:
            txs = parser.parse(pdf)
            if txs:
                print(f"Parsed {len(txs)} from {pdf.name}. First Date: {txs[0]['date']}")
                final_data.extend(txs)
                # Archive
                sd = parser.get_statement_date(pdf)
                dest = archive / f"{sd}-maybank.pdf"
                pdf.rename(dest)
                break

    if final_data:
        out = base_dir / "data" / "stubs" / "extracted_transactions.csv"
        import csv
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "date", "description", "amount"])
            writer.writeheader()
            writer.writerows(final_data)
        print(f"Written to {out}")

if __name__ == "__main__":
    main()
