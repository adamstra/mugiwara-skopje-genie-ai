import os, sys, json, re, math
from pathlib import Path
from collections import Counter
import pandas as pd
import numpy as np

STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 
    'by', 'from', 'up', 'about', 'into', 'over', 'after', 'is', 'are', 'was', 'were', 
    'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'can', 'could', 
    'will', 'would', 'shall', 'should', 'may', 'might', 'must', 'that', 'which', 'who', 
    'whom', 'this', 'these', 'those', 'it', 'its', 'they', 'them', 'their', 'what', 
    'which', 'where', 'when', 'how', 'why', 'all', 'any', 'both', 'each', 'few', 'more', 
    'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 
    'than', 'too', 'very', 's', 't', 'just', 'don', 'now', 'there', 'here', 'use', 'using',
    'give', 'calculate', 'check', 'checking', 'explain', 'compare', 'between', 'table'
}

def extract_pdf_bm25(pdf_path, query, max_pages=3):
    import pypdf
    try:
        reader = pypdf.PdfReader(pdf_path)
    except Exception as e:
        return f"[Error reading PDF {Path(pdf_path).name}: {e}]", []
        
    page_texts = [p.extract_text() or '' for p in reader.pages]
    n_pages = len(page_texts)
    if n_pages == 0:
        return "[Empty PDF]", []
        
    q_tokens = [w.lower() for w in re.findall(r'\b[a-zA-Z0-9_-]+\b', query) if w.lower() not in STOP_WORDS]
    token_dfs = {}
    page_tokens_list = []
    for txt in page_texts:
        tokens = set(re.findall(r'\b[a-zA-Z0-9_-]+\b', txt.lower()))
        page_tokens_list.append(tokens)
        for t in set(q_tokens):
            if t in tokens:
                token_dfs[t] = token_dfs.get(t, 0) + 1
                
    idfs = {}
    for t in set(q_tokens):
        df = token_dfs.get(t, 0)
        idfs[t] = math.log((n_pages - df + 0.5) / (df + 0.5) + 1.0)
        
    # check explicit numbers or table references
    numbers_in_query = re.findall(r'\b\d{2,}\b', query)
    
    scores = []
    for idx, (txt, tokens) in enumerate(zip(page_texts, page_tokens_list)):
        txt_lower = txt.lower()
        score = sum(idfs[t] for t in q_tokens if t in tokens)
        
        # Exact number bonus
        for num in numbers_in_query:
            if num in txt:
                score += 8.0
        # Table reference bonus
        for tm in re.findall(r'table\s*\d+', query.lower()):
            if tm in txt_lower:
                score += 15.0
                
        scores.append((score, idx))
        
    scores.sort(key=lambda x: x[0], reverse=True)
    best_indices = [idx for score, idx in scores[:max_pages] if score > 0]
    if not best_indices:
        best_indices = list(range(min(max_pages, n_pages)))
    best_indices.sort()
    
    chunks = []
    locators = []
    for idx in best_indices:
        p_text = page_texts[idx].strip()
        chunks.append(f"--- PAGE {idx+1} OF {n_pages} ---\n{p_text}")
        locators.append(f"Page {idx+1}")
        
    return "\n\n".join(chunks), locators

def extract_excel_ods(file_path, query, context=""):
    combined_q = (query + " " + context).lower()
    suffix = Path(file_path).suffix.lower()
    chunks = []
    locators = []
    
    try:
        if suffix == ".ods":
            # Read with pandas odf engine
            excel_file = pd.ExcelFile(file_path, engine="odf")
        else:
            excel_file = pd.ExcelFile(file_path)
            
        sheet_names = excel_file.sheet_names
        chunks.append(f"Spreadsheet {Path(file_path).name} Sheets: {sheet_names}")
        
        # Check if query specifically names a sheet
        target_sheets = [s for s in sheet_names if s.lower() in combined_q]
        if not target_sheets:
            target_sheets = sheet_names[:3] # default first 3 sheets
            
        for sname in target_sheets:
            df = excel_file.parse(sname)
            chunks.append(f"Sheet '{sname}' ({len(df)} rows, {len(df.columns)} cols):")
            chunks.append(f"Columns: {list(df.columns)}")
            
            # Look for specific cell references in query (e.g., AA9, Z9, H23, C26)
            cell_refs = re.findall(r'\b([A-Z]{1,2})(\d{1,3})\b', query + " " + context)
            if cell_refs and suffix != ".ods":
                try:
                    import openpyxl
                    wb = openpyxl.load_workbook(file_path, data_only=True)
                    if sname in wb.sheetnames:
                        ws = wb[sname]
                        found_cells = []
                        for col_letter, row_idx in cell_refs:
                            coord = f"{col_letter}{row_idx}"
                            val = ws[coord].value
                            found_cells.append(f"Cell {coord}: {val}")
                            locators.append(f"sheet {sname}, cell {coord}")
                        if found_cells:
                            chunks.append("Explicit Referenced Cells:\n" + "\n".join(found_cells))
                except Exception:
                    pass
                    
            # Search for rows containing query keywords (e.g. Helsinki, Espoo, Vantaa, Residential, 2023, 2024, etc.)
            key_terms = [w for w in re.findall(r'\b[a-zA-Z0-9_-]{3,}\b', combined_q) if w not in STOP_WORDS]
            matched_rows = []
            for r_idx, row in df.iterrows():
                row_str = " ".join(str(v) for v in row.values)
                match_count = sum(1 for term in key_terms if term in row_str.lower())
                if match_count >= 2:
                    matched_rows.append((match_count, r_idx, row_str[:200]))
            
            matched_rows.sort(key=lambda x: x[0], reverse=True)
            if matched_rows:
                chunks.append("Key matching rows from sheet:")
                for _, r_idx, r_str in matched_rows[:8]:
                    chunks.append(f"Row {r_idx+2}: {r_str}")
            else:
                chunks.append("Preview (first 10 rows):\n" + df.head(10).to_string(index=False))
                
    except Exception as e:
        chunks.append(f"[Error reading spreadsheet {Path(file_path).name}: {e}]")
        
    return "\n\n".join(chunks), locators

def extract_csv_tabular(file_path, query, context=""):
    combined_q = (query + " " + context).lower()
    path = Path(file_path)
    chunks = []
    locators = []
    
    # Try UTF-8, then latin1
    for enc in ["utf-8", "latin1", "cp1252"]:
        try:
            # check delimiter
            with open(path, "r", encoding=enc) as f:
                head = [f.readline() for _ in range(5)]
            sep = ";" if head and ";" in head[0] else ("," if head and "," in head[0] else "\t")
            df = pd.read_csv(path, encoding=enc, sep=sep, low_memory=False)
            break
        except Exception:
            df = None
            
    if df is None:
        return f"[Error loading CSV {path.name}]", []
        
    chunks.append(f"CSV {path.name}: {len(df):,} rows, {len(df.columns)} columns")
    chunks.append(f"Columns: {list(df.columns)}")
    
    # Detect entity mentions in query (e.g. trip_id, tpo_number, borough, street)
    # Search text columns for exact entity mentions
    entity_candidates = re.findall(r'\b[A-Z0-9_\-\.]{3,}\b', query + " " + context)
    entity_matches = []
    for cand in entity_candidates:
        if cand.lower() in STOP_WORDS or len(cand) < 4:
            continue
        # Check against object/string columns
        for col in df.select_dtypes(include=['object']).columns:
            m = df[df[col].astype(str) == cand]
            if len(m) > 0 and len(m) <= 10:
                entity_matches.append((col, cand, m))
                locators.append(f"{path.name}, row where {col}={cand}")
                
    if entity_matches:
        chunks.append("Matched entities found in CSV:")
        for col, cand, m in entity_matches[:5]:
            chunks.append(f"Match on {col} = '{cand}':\n" + m.to_string(index=False))
            
    # Check if query asks about diameter/DHP/zeros/negatives/nulls
    if any(k in combined_q for k in ["dhp", "diameter", "zero", "positive", "negative", "blank", "null"]):
        for col in df.columns:
            if "dhp" in col.lower() or "diam" in col.lower():
                s = df[col].astype(str).str.replace(',', '.')
                nums = pd.to_numeric(s, errors='coerce')
                null_cnt = nums.isna().sum()
                zero_cnt = (nums == 0).sum()
                neg_cnt = (nums < 0).sum()
                pos_cnt = (nums > 0).sum()
                min_val = nums.min()
                max_val = nums.max()
                chunks.append(
                    f"Numeric stats for column '{col}': Total={len(df)}, Nulls={null_cnt}, "
                    f"Zeros={zero_cnt}, Negatives={neg_cnt}, Strictly Positive={pos_cnt}, "
                    f"Min={min_val}, Max={max_val}"
                )
                locators.append(f"{path.name}, column {col}")
                
    # Check if query asks for group counts or breakdown (e.g. location_type, species, status)
    if any(k in combined_q for k in ["breakdown", "count", "genus", "latin", "most common", "share", "percentage", "type"]):
        for col in df.columns:
            if any(term in col.lower() for term in ["type", "genus", "art", "species", "essence", "stat", "sever"]):
                vc = df[col].value_counts(dropna=False).head(8)
                chunks.append(f"Top values in column '{col}':\n{vc.to_string()}")
                
    # Check if query asks for pair duplicates or distinct count (e.g. RAD_TYPE / RAD_EMP_NO)
    pair_cols = re.findall(r'([A-Za-z0-9_]+)\s*/\s*([A-Za-z0-9_]+)', query)
    for col1, col2 in pair_cols:
        if col1 in df.columns and col2 in df.columns:
            distinct_pairs = len(df[[col1, col2]].drop_duplicates())
            chunks.append(f"Distinct pairs for ({col1}, {col2}): {distinct_pairs:,} distinct pairs across {len(df):,} total rows.")
            locators.append(f"{path.name}, columns {col1} and {col2}")
            
    # If chunks only has headers, add sample head
    if len(chunks) <= 2:
        chunks.append("Sample head:\n" + df.head(5).to_string(index=False))
        
    return "\n\n".join(chunks), locators

def extract_geojson_gis(file_path, query, context=""):
    import geopandas as gpd
    path = Path(file_path)
    combined_q = (query + " " + context).lower()
    chunks = []
    locators = []
    
    try:
        gdf = gpd.read_file(path)
        chunks.append(f"GIS Layer {path.name}: {len(gdf):,} features, CRS: {gdf.crs}")
        chunks.append(f"Columns: {[c for c in gdf.columns if c != 'geometry']}")
        
        # Check if query asks about area of a specific zone/feature (e.g. Liverpool 1912/A1)
        zone_matches = re.findall(r'\b(\d{3,4}/[A-Z0-9]+|\d{4}-\d{2}-\d{2})\b', query)
        for zone in zone_matches:
            for col in gdf.select_dtypes(include=['object']).columns:
                m = gdf[gdf[col].astype(str) == zone]
                if len(m) > 0:
                    geom = m.geometry.iloc[0]
                    # Calculate area
                    # If British National Grid or projected:
                    if gdf.crs and "27700" in str(gdf.crs):
                        area_m2 = geom.area
                    elif "british national grid" in combined_q:
                        # Reproject to EPSG:27700
                        gdf_bng = gdf.to_crs(epsg=27700)
                        geom_bng = gdf_bng[gdf_bng[col].astype(str) == zone].geometry.iloc[0]
                        area_m2 = geom_bng.area
                    else:
                        area_m2 = geom.area
                    area_ha = area_m2 / 10000.0
                    chunks.append(
                        f"Zone match for {col}='{zone}':\n"
                        f"Geometry Type: {geom.geom_type}\n"
                        f"Area: {area_m2:.2f} m² = {area_ha:.2f} hectares"
                    )
                    locators.append(f"{path.name}, properties.{col}={zone}")
                    
        # Check for Latin genus / species distribution (e.g. Berlin trees anlagenbaeume)
        for col in gdf.columns:
            if col.lower() in ["art_bot", "gattung", "species", "essence_latin"]:
                vc = gdf[col].value_counts().head(5)
                total = len(gdf)
                res = []
                for val, cnt in vc.items():
                    res.append(f"  {val}: {cnt} trees ({cnt/total*100:.2f}%)")
                chunks.append(f"Top Latin genus/species in '{col}' (Total trees = {total:,}):\n" + "\n".join(res))
                locators.append(f"{path.name}, column {col}")
                
    except Exception as e:
        chunks.append(f"[Error reading GIS file {path.name}: {e}]")
        
    return "\n\n".join(chunks), locators
