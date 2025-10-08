import pandas as pd
import re

def extract_subproduct_code(code_string: str) -> str:
    """
    Extract subproduct code from CEPLAN format:
    "AOI00162600455 - 0087901 - ADOLESCENTE CON SUPLEMENTO..."
    Returns "0087901" as the subproduct code
    """
    if ' - ' in code_string:
        parts = code_string.split(' - ')
        if len(parts) >= 2:
            potential_code = parts[1].strip()
            if potential_code.isdigit() and len(potential_code) >= 5:
                return potential_code
            else:
                code_match = re.search(r'(\d{5,7})', potential_code)
                if code_match:
                    return code_match.group(1)

    code_match = re.search(r'(\d{5,7})', code_string)
    if code_match:
        return code_match.group(1)

    return ""

file_path="/home/bitler/projects/IS/monitor_ppr/archivos_test/ceplan.xlsx"

df = pd.read_excel(file_path, header=None, engine='openpyxl')
subproduct_start_indices = {}
for idx, row in df.iterrows():
    code_cell = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
    subproduct_code = extract_subproduct_code(code_cell)
    if subproduct_code:
        subproduct_start_indices[idx] = {
            "code": subproduct_code,
            "name": str(row.iloc[3]) if len(row) > 3 and pd.notna(row.iloc[3]) else f"Subproducto {subproduct_code}",
            "um": str(row.iloc[5]) if len(row) > 5 and pd.notna(row.iloc[5]) else "UNIDAD"
        }

for start_idx, sub_info in subproduct_start_indices.items():    
    print(df.iloc[[start_idx,start_idx+1],8:20].head())

    