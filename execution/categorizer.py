import os
import json
import logging
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class GeminiCategorizer:
    def __init__(self, map_file="data/category_map.json"):
        # Load Environment
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-flash-latest')
        
        # Load Cache
        self.map_file = Path(map_file)
        self.category_map = self._load_map()
        
        # Define Categories (Could be loaded from external file too)
        self.valid_categories = [
            "Food & Dining", "Transportation", "Shopping", "Utilities", 
            "Health & Wellness", "Entertainment", "Travel", "Insurance", 
            "Education", "Investments", "Transfers", "Misc"
        ]

    def _load_map(self):
        if self.map_file.exists():
            try:
                with open(self.map_file, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_map(self):
        self.map_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.map_file, "w") as f:
            json.dump(self.category_map, f, indent=4)

    def categorize_dataframe(self, df: pd.DataFrame, description_col="description") -> pd.DataFrame:
        """
        Takes a DataFrame, checks for existing categories in map, 
        batches new descriptions for LLM, and returns updated DataFrame.
        """
        if description_col not in df.columns:
            raise ValueError(f"Column '{description_col}' not found in DataFrame")

        # Create columns if not exists
        if "Category" not in df.columns: df["Category"] = None
        if "Sub-Category" not in df.columns: df["Sub-Category"] = None

        # 1. Apply Cache
        df["_lookup_key"] = df[description_col].astype(str).str.strip().str.upper()
        
        # Check if map has simple string or dict value
        # If dict: {"Category": "...", "Sub-Category": "..."}
        # We assume map structure is consistent.
        
        def get_cat(k):
            val = self.category_map.get(k)
            if isinstance(val, dict): return val.get("Category")
            return val
            
        def get_sub(k):
            val = self.category_map.get(k)
            if isinstance(val, dict): return val.get("Sub-Category")
            return "General" if val else None

        df["Category"] = df["_lookup_key"].apply(get_cat)
        df["Sub-Category"] = df["_lookup_key"].apply(get_sub)
        
        # 2. Identify missing (Category is Null)
        missing_mask = df["Category"].isna()
        unique_missing = df.loc[missing_mask, "_lookup_key"].unique()
        
        if len(unique_missing) > 0:
            logging.info(f"Categorizing {len(unique_missing)} unique descriptions via Gemini...")
            new_mappings = self._batch_categorize(unique_missing)
            
            # Update Map and Save
            self.category_map.update(new_mappings)
            self._save_map()
            
            # Re-map DataFrame
            df.loc[missing_mask, "Category"] = df.loc[missing_mask, "_lookup_key"].apply(get_cat)
            df.loc[missing_mask, "Sub-Category"] = df.loc[missing_mask, "_lookup_key"].apply(get_sub)
            
        else:
            logging.info("All descriptions found in cache.")

        # Cleanup
        df.drop(columns=["_lookup_key"], inplace=True)
        # Fill remaining NaNs
        df["Category"].fillna("Unclassified", inplace=True)
        df["Sub-Category"].fillna("General", inplace=True)
        
        return df

    def _batch_categorize(self, descriptions):
        """
        Sends a batch of descriptions to Gemini and returns a dict mapping.
        """
        mapping = {}
        
        prompt = f"""
        You are a financial transaction classifier. 
        Map the following transaction descriptions to these Main Categories: {self.valid_categories}.
        Also provide a specific Sub-Category based on the context (e.g., 'Groceries', 'Taxi', 'Subscription').
        
        Return ONLY a raw JSON object (no markdown) where the keys are the Descriptions and values are objects like:
        {{ "Description": {{ "Category": "MainCategory", "Sub-Category": "SpecificSubCategory" }} }}
        
        Descriptions to classify:
        {json.dumps(list(descriptions))}
        """
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            # print(f"DEBUG LLM RAW: {text}")
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
                
            batch_result = json.loads(text)
            
            # Normalize keys and values
            for k, v in batch_result.items():
                clean_key = k.strip().upper()
                if isinstance(v, dict):
                    mapping[clean_key] = {
                        "Category": v.get("Category", "Unclassified"),
                        "Sub-Category": v.get("Sub-Category", "General")
                    }
                else:
                    # Fallback if LLM returns string (old behavior protection)
                    mapping[clean_key] = {"Category": str(v), "Sub-Category": "General"}
                
        except Exception as e:
            print(f"LLM Batch Error: {e}")
            import traceback
            traceback.print_exc()
            
        return mapping

# --- TDD Test Section ---
def test_categorizer():
    print("\n--- Running TDD Test ---")
    
    # Test Data
    data = {
        'description': ['TNG*VILLAGE GROCER', 'GRAB*FOOD', 'PETRONAS-PJS', 'RENEWAL FEE IBKR', 'TNG*VILLAGE GROCER', 'UNK_TXN_123']
    }
    df = pd.DataFrame(data)
    
    print("Input DataFrame:")
    print(df)
    
    # Initialize Wrapper
    categorizer = GeminiCategorizer(map_file="data/test_category_map.json")
    
    # Clear test map to force API call
    if categorizer.map_file.exists():
        os.remove(categorizer.map_file)
    categorizer.category_map = {}
        
    # Run
    df_result = categorizer.categorize_dataframe(df)
    
    print("\nOutput DataFrame:")
    print(df_result)
    
    # Assertions
    assert "Category" in df_result.columns
    assert "Sub-Category" in df_result.columns
    # Check basics
    assert df_result.loc[0, "Category"] == "Food & Dining"
    assert df_result.loc[0, "Sub-Category"] != "General" # Should be something like Groceries
    
    # Check consistency
    assert df_result.loc[0, "Category"] == df_result.loc[4, "Category"] 
    
    print("\nTest Map Content:")
    print(json.dumps(categorizer.category_map, indent=2))
    
    # Clean up
    if categorizer.map_file.exists():
        os.remove(categorizer.map_file)
        
    print("\n--- Test Passed ---")

if __name__ == "__main__":
    test_categorizer()
