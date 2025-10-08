"""
Extraction Service for PPR and CEPLAN files
This service integrates the proven extraction logic into the existing Monitor PPR application.
"""

import pandas as pd
import re
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlmodel import Session, select
import logging

from app.models.ppr import PPR, Producto, Actividad, Subproducto
from app.models.programacion import ProgramacionPPR
from app.models.user import User

logger = logging.getLogger(__name__)


class PPRExtractorService:
    """Service for extracting PPR data from Excel files"""
    
    def __init__(self):
        """Initialize the extractor service"""
        self.months = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 
                      'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
    
    def extract_ppr_from_file(self, file_path: Path) -> Dict:
        """
        Extract complete hierarchical PPR data from Excel file
        Structure: PPR → Productos → Actividades → Subproductos → Unidad de Medida → Programación/Ejecución por mes
        """
        logger.info(f"Starting PPR extraction from file: {file_path}")
        
        try:
            df = pd.read_excel(file_path, header=None, engine='openpyxl')
            logger.info(f"Loaded Excel file with {len(df)} rows and {len(df.columns)} columns")
            
            ppr_info = self._extract_ppr_info(df)
            logger.info(f"Extracted PPR info: {ppr_info}")
            
            products, validation_logs = self._extract_hierarchical_structure(df)
            
            result = {
                "ppr": ppr_info,
                "productos": products,
                "logs": validation_logs
            }
            
            logger.info(f"PPR extraction completed. Found {len(products)} products.")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting PPR data from {file_path}: {str(e)}", exc_info=True)
            raise e
    
    def _extract_ppr_info(self, df: pd.DataFrame) -> Dict:
        """Extract PPR information from the file"""
        ppr_info = {
            "codigo": "",
            "nombre": "",
            "anio": datetime.now().year
        }
        
        # Load the PPR mapping from the reference file
        ppr_mapping = self._load_ppr_mapping()
        
        # Search in the first 10 rows for PPR code and name matches
        for i in range(min(10, len(df))):
            row_data = df.iloc[i].dropna()
            original_row_text = ' '.join(str(cell) for cell in row_data)
            normalized_row_text = self._normalize_text(original_row_text)
            
            # Look for PPR matches using the mapping
            for code, name in ppr_mapping.items():
                normalized_name = self._normalize_text(name)
                
                # Match the name in the row text (case-insensitive, accent-insensitive)
                if normalized_name in normalized_row_text:
                    ppr_info["codigo"] = code.zfill(3)
                    ppr_info["nombre"] = name  # Use original name format
                    return ppr_info  # Return immediately when a match is found
                
                # Also check if just the code appears in the row
                if code in original_row_text:
                    ppr_info["codigo"] = code.zfill(3)
                    ppr_info["nombre"] = name
                    # Try to find the name part in nearby cells if it's not fully matched
                    for cell in row_data:
                        cell_str = str(cell)
                        if code in cell_str:
                            # If the cell contains the code followed by text, use that as the name
                            parts = str(cell).split(code, 1)
                            if len(parts) > 1 and parts[1].strip():
                                potential_name = parts[1].strip()
                                if len(potential_name) > 2:  # Ensure it's a meaningful name
                                    ppr_info["nombre"] = potential_name
                                    break
                    return ppr_info
        
        # If still not found, check for the specific format you mentioned
        # Column A = "PROGRAMA PRESUPUESTAL", Column B = ":", Column C = "0017 NAME"
        for i in range(min(10, len(df))):
            row = df.iloc[i]
            if len(row) >= 3:
                col_a = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
                col_b = str(row.iloc[1]) if len(row) > 1 and pd.notna(row.iloc[1]) else ""
                col_c = str(row.iloc[2]) if len(row) > 2 and pd.notna(row.iloc[2]) else ""
                
                normalized_col_a = self._normalize_text(col_a)
                if 'programapresupuestal' in normalized_col_a and col_b.strip() == ':':
                    # Extract code and name from the third column
                    # Format: "0017 ENFERMEDADES METAXÉNICAS Y ZOONOSIS"
                    parts = col_c.split(' ', 1)  # Split on first space to separate code and name
                    if len(parts) >= 2:
                        code_part = parts[0].strip()
                        name_part = parts[1].strip()
                        
                        # Validate the code is 3-4 digits
                        if code_part.isdigit() and (3 <= len(code_part) <= 4):
                            ppr_info["codigo"] = code_part.zfill(3)  # Pad to 3 digits if needed
                            ppr_info["nombre"] = name_part
                            return ppr_info
        
        # If no match found by this point, return empty values
        return ppr_info
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison by removing accents and converting to lowercase"""
        import unicodedata
        # Convert to lowercase and normalize unicode characters
        text = text.lower()
        # Remove accents and special characters
        text = unicodedata.normalize('NFKD', text).encode('ascii', errors='ignore').decode()
        # Remove extra spaces and special characters, keep only alphanumeric characters
        import re
        text = re.sub(r'[^a-z0-9\s]', '', text)
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text
    
    def _load_ppr_mapping(self) -> Dict[str, str]:
        """Load PPR mapping from reference file"""
        mapping = {}
        try:
            reference_file = Path("ppr.txt")
            if reference_file.exists():
                with open(reference_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[1:]:  # Skip header
                        parts = line.strip().split(',', 1)
                        if len(parts) >= 2:
                            code = parts[0].strip()
                            name = parts[1].strip()
                            mapping[code] = name
        except Exception as e:
            logger.warning(f"Could not load PPR mapping from ppr.txt: {e}")
        
        # Add some known mappings as fallback
        if not mapping:
            mapping = {
                "002": "Salud materno neonatal",
                "0016": "TBC-VIH/SIDA",
                "0017": "Enfermedades metaxenicas y zoonosis",
                "0018": "Enfermedades no transmisibles",
                "0024": "Prevención y control del cáncer",
                "0068": "Reducción de vulnerabilidad y atención de emergencias por desastres",
                "0104": "Reducción de la mortalidad por emergencias y urgencias medica",
                "0129": "Prevención y manejo de condiciones secundarias de salud en personas con discapacidad",
                "0131": "Control y prevención en salud mental",
                "1001": "Productos Específicos para desarrollo infantil temprano (RS 023-2019-EF)",
                "1002": "Productos Específicos para la reducción de la violencia contra la mujer (RS 024-2019-EF)"
            }
        
        return mapping

    def _find_product_name(self, df: pd.DataFrame, row_idx: int) -> Optional[str]:
        """Searches for a plausible product name in the vicinity of the product code row."""
        search_coords = [
            (row_idx, 1), (row_idx, 2),
            (row_idx + 1, 1), (row_idx + 1, 2)
        ]
        
        for r, c in search_coords:
            if r < len(df) and c < len(df.columns):
                cell_value = df.iloc[r, c]
                if pd.notna(cell_value):
                    cell_str = str(cell_value).strip()
                    if not cell_str.isnumeric() and len(cell_str) > 4:
                        return cell_str
        return None

    def _extract_hierarchical_structure(self, df: pd.DataFrame) -> (List[Dict], List[str]):
        """Extract complete hierarchical structure from PPR data with dynamic column detection."""
        logger.info("Extracting hierarchical structure with dynamic column detection...")
        
        # Find header positions by scanning first 20 rows
        header_info = self._find_header_positions(df)
        
        if not header_info:
            logger.warning("Could not find expected headers, using default positions")
            # Fallback to original approach with default positions
            return self._extract_hierarchical_structure_default(df)
        
        # Extract position information
        prod_code_col = header_info.get('prod_code_col', 0)
        prod_name_col = header_info.get('prod_name_col', 1)
        act_code_col = header_info.get('act_code_col', 2)
        act_name_col = header_info.get('act_name_col', 3)
        subprod_code_col = header_info.get('subprod_code_col', 4)
        subprod_name_col = header_info.get('subprod_name_col', 5)
        unidad_medida_col = header_info.get('unidad_medida_col', 6)
        meta_col = header_info.get('meta_col', 7)
        programado_start_col = header_info.get('programado_start_col', 8)
        
        products = {}
        current_product_code = None
        current_activity_code = None
        
        # Start processing from the row after headers
        data_start_row = header_info.get('data_start_row', 10)  # Default fallback
        
        for row_idx in range(data_start_row, len(df)):
            row = df.iloc[row_idx]
            
            if row.isnull().all():
                continue

            # --- State Transition: Detect Product ---
            product_code_val = None
            if prod_code_col < len(row) and pd.notna(row.iloc[prod_code_col]):
                product_code_val = str(row.iloc[prod_code_col]).strip()
                # Check if it looks like a product code (not just any text)
                if product_code_val and (product_code_val.isdigit() or product_code_val.replace('.', '').replace('-', '').isdigit()):
                    current_product_code = product_code_val
                    product_name = str(row.iloc[prod_name_col]).strip() if prod_name_col < len(row) and pd.notna(row.iloc[prod_name_col]) else f"Producto {current_product_code}"
                    
                    if current_product_code not in products:
                        products[current_product_code] = {
                            "codigo_producto": current_product_code,
                            "nombre_producto": product_name,
                            "actividades": {}
                        }
                    current_activity_code = None
                    logger.debug(f"Row {row_idx}: CONTEXT CHANGE -> Product: {current_product_code} - {product_name}")

            # --- State Transition: Detect Activity ---
            activity_code_val = None
            if act_code_col < len(row) and pd.notna(row.iloc[act_code_col]):
                activity_code_val = str(row.iloc[act_code_col]).strip()
                if activity_code_val and current_product_code:
                    current_activity_code = activity_code_val
                    activity_name = str(row.iloc[act_name_col]).strip() if act_name_col < len(row) and pd.notna(row.iloc[act_name_col]) else f"Actividad {current_activity_code}"
                    if current_activity_code not in products[current_product_code]["actividades"]:
                        products[current_product_code]["actividades"][current_activity_code] = {
                            "codigo_actividad": current_activity_code,
                            "nombre_actividad": activity_name,
                            "subproductos": []
                        }
                    logger.debug(f"Row {row_idx}: CONTEXT CHANGE -> Activity: {current_activity_code}")

            # --- Subproduct Detection ---
            subproduct_data = None
            if subprod_code_col < len(row) and pd.notna(row.iloc[subprod_code_col]) and self._is_numeric_code(str(row.iloc[subprod_code_col])):
                # Use dynamic column positions to parse subproduct data
                subproduct_data = self._parse_subproduct_row_dynamic(row, subprod_code_col, subprod_name_col, unidad_medida_col, meta_col, programado_start_col)

            if subproduct_data:
                if current_product_code and current_activity_code:
                    try:
                        products[current_product_code]["actividades"][current_activity_code]["subproductos"].append(subproduct_data)
                        logger.debug(f"    Row {row_idx}: Added subproduct '{subproduct_data['codigo_subproducto']}' to activity '{current_activity_code}'")
                    except KeyError:
                        logger.warning(f"Row {row_idx}: Could not add subproduct. Context lost? Product: {current_product_code}, Activity: {current_activity_code}")
                else:
                    logger.warning(f"Row {row_idx}: Found subproduct '{subproduct_data['codigo_subproducto']}' but no current activity or product context.")

        validated_products, validation_logs = self._validate_and_clean_products(products)
        
        result_products = []
        for prod_code, product_data in validated_products.items():
            product_data['actividades'] = list(product_data['actividades'].values())
            result_products.append(product_data)
        
        logger.info(f"Hierarchical structure extraction completed. Found {len(result_products)} valid products.")
        return result_products, validation_logs
    
    def _find_header_positions(self, df: pd.DataFrame) -> Dict:
        """Find column positions for different data types by searching first 20 rows."""
        logger.info("Searching for header positions in the first 20 rows...")
        
        header_info = {}
        
        # Define search patterns for different column types
        patterns = {
            'prod_code': [r'cod\.?[\s_\-]*prod', r'codigo[\s_\-]*prod', r'prod[\s_\-]*cod', 'codprod'],
            'prod_name': [r'prod(?:ucto)?', r'nombre[\s_\-]*prod', 'producto'],
            'act_code': [r'cod\.?[\s_\-]*act', r'codigo[\s_\-]*act', r'act[\s_\-]*cod', 'codact'],
            'act_name': [r'act(?:ividad)?', r'nombre[\s_\-]*act', 'actividad'],
            'subprod_code': [r'cod\.?[\s_\-]*sub', r'codigo[\s_\-]*sub', r'sub[\s_\-]*cod', r'cod\.?[\s_\-]*subp', 'subproducto', 'subprod'],
            'subprod_name': [r'subp(?:roducto)?', 'subproducto', 'subprod'],
            'unidad_medida': [r'unidad[\s_\-]*med', r'umed', r'unid\.?', 'unidad'],
            'meta': [r'meta', r'indicador', r'cantidad'],
            'months_start': [r'ene', r'ene\.?', r'enero', r'ene[-:\s]', r'mes'],  # Start of monthly columns
            'programado': [r'p\b', r'programado', r'prog', r'programacion']  # Letter 'P' for programado
        }
        
        # Scan first 20 rows to find headers
        for row_idx in range(min(20, len(df))):
            row = df.iloc[row_idx]
            row_text = [str(cell).lower() if pd.notna(cell) else '' for cell in row]
            
            # Check each cell in the row for header patterns
            for col_idx, cell_text in enumerate(row_text):
                normalized_text = self._normalize_text(cell_text)
                
                # Check for product code column
                for pattern in patterns['prod_code']:
                    if re.search(pattern, normalized_text, re.IGNORECASE):
                        header_info['prod_code_col'] = col_idx
                        logger.debug(f"Found product code header at row {row_idx}, col {col_idx}: {cell_text}")
                        break
                
                # Check for product name column
                for pattern in patterns['prod_name']:
                    if re.search(pattern, normalized_text, re.IGNORECASE):
                        header_info['prod_name_col'] = col_idx
                        logger.debug(f"Found product name header at row {row_idx}, col {col_idx}: {cell_text}")
                        break
                
                # Check for activity code column
                for pattern in patterns['act_code']:
                    if re.search(pattern, normalized_text, re.IGNORECASE):
                        header_info['act_code_col'] = col_idx
                        logger.debug(f"Found activity code header at row {row_idx}, col {col_idx}: {cell_text}")
                        break
                
                # Check for activity name column
                for pattern in patterns['act_name']:
                    if re.search(pattern, normalized_text, re.IGNORECASE):
                        header_info['act_name_col'] = col_idx
                        logger.debug(f"Found activity name header at row {row_idx}, col {col_idx}: {cell_text}")
                        break
                
                # Check for subproduct code column
                for pattern in patterns['subprod_code']:
                    if re.search(pattern, normalized_text, re.IGNORECASE):
                        header_info['subprod_code_col'] = col_idx
                        logger.debug(f"Found subproduct code header at row {row_idx}, col {col_idx}: {cell_text}")
                        break
                
                # Check for subproduct name column
                for pattern in patterns['subprod_name']:
                    if re.search(pattern, normalized_text, re.IGNORECASE):
                        header_info['subprod_name_col'] = col_idx
                        logger.debug(f"Found subproduct name header at row {row_idx}, col {col_idx}: {cell_text}")
                        break
                
                # Check for unidad medida column
                for pattern in patterns['unidad_medida']:
                    if re.search(pattern, normalized_text, re.IGNORECASE):
                        header_info['unidad_medida_col'] = col_idx
                        logger.debug(f"Found unidad medida header at row {row_idx}, col {col_idx}: {cell_text}")
                        break
                
                # Check for meta column
                for pattern in patterns['meta']:
                    if re.search(pattern, normalized_text, re.IGNORECASE):
                        header_info['meta_col'] = col_idx
                        logger.debug(f"Found meta header at row {row_idx}, col {col_idx}: {cell_text}")
                        break
        
        # Now find the monthly column start (after 'ene' and first 'P' for programado)
        for row_idx in range(min(25, len(df))):  # Check more rows for monthly data
            row = df.iloc[row_idx]
            row_text = [str(cell).lower() if pd.notna(cell) else '' for cell in row]
            
            for col_idx, cell_text in enumerate(row_text):
                if pd.notna(cell_text):
                    normalized_text = self._normalize_text(cell_text)
                    
                    # Look for month start (ENE) and programado indicator (P)
                    if re.search(r'ene', normalized_text, re.IGNORECASE):
                        # Find the first 'P' after ENE which indicates Programado
                        for next_col_idx in range(col_idx, min(len(row), col_idx + 20)):  # Look ahead up to 20 columns
                            next_cell = str(row.iloc[next_col_idx]).lower() if pd.notna(row.iloc[next_col_idx]) else ''
                            if next_cell == 'p' or 'programado' in self._normalize_text(next_cell):
                                header_info['programado_start_col'] = next_col_idx
                                header_info['data_start_row'] = row_idx + 1  # Data starts after header row
                                logger.debug(f"Found monthly data start at row {row_idx}, col {next_col_idx}")
                                break
                        if 'programado_start_col' in header_info:
                            break
                if 'programado_start_col' in header_info:
                    break
            if 'programado_start_col' in header_info:
                break
        
        logger.info(f"Header positions found: {header_info}")
        return header_info

    def _parse_subproduct_row_dynamic(self, row: pd.Series, subprod_code_col: int, subprod_name_col: int, 
                                    unidad_medida_col: int, meta_col: int, programado_start_col: int) -> Optional[Dict]:
        """Parses a subproduct row using dynamic column positions."""
        try:
            subproduct_code = str(row.iloc[subprod_code_col]).strip() if subprod_code_col < len(row) and pd.notna(row.iloc[subprod_code_col]) else ""
            subproduct_name = str(row.iloc[subprod_name_col]).strip() if subprod_name_col < len(row) and pd.notna(row.iloc[subprod_name_col]) else f"Subproducto {subproduct_code}"
            unidad_medida = str(row.iloc[unidad_medida_col]).strip() if unidad_medida_col < len(row) and pd.notna(row.iloc[unidad_medida_col]) else "UNIDAD"
            
            meta_anual = 0
            if meta_col < len(row) and pd.notna(row.iloc[meta_col]):
                try:
                    meta_anual = int(round(float(str(row.iloc[meta_col]).replace(',', '.'))))
                except (ValueError, TypeError):
                    meta_anual = 0

            programacion = {}
            ejecucion = {}
            
            # Extract 12 months of programado and ejecutado values
            for i, month in enumerate(self.months):
                prog_col_idx = programado_start_col + (i * 2)  # Programado in even positions after start
                ejec_col_idx = programado_start_col + (i * 2) + 1  # Ejecutado in odd positions after start
                
                prog_value = 0
                if prog_col_idx < len(row) and pd.notna(row.iloc[prog_col_idx]):
                    try:
                        prog_value = int(round(float(str(row.iloc[prog_col_idx]).replace(',', '.'))))
                    except (ValueError, TypeError):
                        prog_value = 0
                programacion[month] = prog_value

                ejec_value = 0
                if ejec_col_idx < len(row) and pd.notna(row.iloc[ejec_col_idx]):
                    try:
                        ejec_value = int(round(float(str(row.iloc[ejec_col_idx]).replace(',', '.'))))
                    except (ValueError, TypeError):
                        ejec_value = 0
                ejecucion[month] = ejec_value

            warnings = self._create_validation_warnings(meta_anual, programacion, ejecucion)

            return {
                "codigo_subproducto": subproduct_code,
                "nombre_subproducto": subproduct_name,
                "unidad_medida": unidad_medida,
                "meta_anual": meta_anual,
                "programado": programacion,
                "ejecutado": ejecucion,
                "warnings": warnings
            }
        except (ValueError, TypeError, IndexError) as e:
            logger.error(f"Error parsing subproduct row with dynamic columns: {row}. Error: {e}")
            return None

    def _extract_hierarchical_structure_default(self, df: pd.DataFrame) -> (List[Dict], List[str]):
        """Default extraction method - fallback if dynamic detection fails."""
        logger.info("Using default extraction method (fixed positions)...")
        
        products = {}
        current_product_code = None
        current_activity_code = None
        
        data_start_row = 11
        
        for row_idx in range(data_start_row, len(df)):
            row = df.iloc[row_idx]
            
            if row.isnull().all():
                continue

            # --- State Transition: Detect Product ---
            product_code_val = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else None
            if product_code_val and product_code_val in df.iloc[:, 0].astype(str).unique():
                current_product_code = product_code_val
                product_name = self._find_product_name(df, row_idx) or f"Producto {current_product_code}"
                
                if current_product_code not in products:
                    products[current_product_code] = {
                        "codigo_producto": current_product_code,
                        "nombre_producto": product_name,
                        "actividades": {}
                    }
                current_activity_code = None
                logger.debug(f"Row {row_idx}: CONTEXT CHANGE -> Product: {current_product_code} - {product_name}")

            # --- State Transition: Detect Activity ---
            activity_code_val = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else None
            if activity_code_val and current_product_code:
                current_activity_code = activity_code_val
                activity_name = str(row.iloc[3]).strip() if len(row) > 3 and pd.notna(row.iloc[3]) else f"Actividad {current_activity_code}"
                if current_activity_code not in products[current_product_code]["actividades"]:
                    products[current_product_code]["actividades"][current_activity_code] = {
                        "codigo_actividad": current_activity_code,
                        "nombre_actividad": activity_name,
                        "subproductos": []
                    }
                logger.debug(f"Row {row_idx}: CONTEXT CHANGE -> Activity: {current_activity_code}")

            # --- Subproduct Detection (Standard and Shifted) ---
            subproduct_data = None
            if len(row) > 3 and pd.notna(row.iloc[3]) and self._is_numeric_code(str(row.iloc[3])):
                subproduct_data = self._parse_subproduct_row(row, shifted=True)
            elif len(row) > 4 and pd.notna(row.iloc[4]) and self._is_numeric_code(str(row.iloc[4])):
                subproduct_data = self._parse_subproduct_row(row, shifted=False)

            if subproduct_data:
                if current_product_code and current_activity_code:
                    try:
                        products[current_product_code]["actividades"][current_activity_code]["subproductos"].append(subproduct_data)
                        logger.debug(f"    Row {row_idx}: Added subproduct '{subproduct_data['codigo_subproducto']}' to activity '{current_activity_code}'")
                    except KeyError:
                        logger.warning(f"Row {row_idx}: Could not add subproduct. Context lost? Product: {current_product_code}, Activity: {current_activity_code}")
                else:
                    logger.warning(f"Row {row_idx}: Found subproduct '{subproduct_data['codigo_subproducto']}' but no current activity or product context.")

        validated_products, validation_logs = self._validate_and_clean_products(products)
        
        result_products = []
        for prod_code, product_data in validated_products.items():
            product_data['actividades'] = list(product_data['actividades'].values())
            result_products.append(product_data)
        
        logger.info(f"Default hierarchical structure extraction completed. Found {len(result_products)} valid products.")
        return result_products, validation_logs

    def _parse_subproduct_row(self, row: pd.Series, shifted: bool) -> Optional[Dict]:
        """Parses a row containing subproduct data, handling standard and shifted patterns."""
        try:
            if shifted:
                code_col, name_col, um_col, meta_col, prog_start_col = 3, 4, 5, 7, 8
            else:
                code_col, name_col, um_col, meta_col, prog_start_col = 4, 5, 6, 8, 9

            subproduct_code = str(row.iloc[code_col]).strip()
            subproduct_name = str(row.iloc[name_col]).strip() if len(row) > name_col and pd.notna(row.iloc[name_col]) else f"Subproducto {subproduct_code}"
            unidad_medida = str(row.iloc[um_col]).strip() if len(row) > um_col and pd.notna(row.iloc[um_col]) else "UNIDAD"
            
            meta_anual = 0
            if len(row) > meta_col and pd.notna(row.iloc[meta_col]):
                meta_anual = int(round(float(str(row.iloc[meta_col]).replace(',', '.'))))

            programacion = {}
            ejecucion = {}
            for i, month in enumerate(self.months):
                prog_col_idx = prog_start_col + (i * 2)
                ejec_col_idx = prog_start_col + (i * 2) + 1
                
                prog_value = 0
                if len(row) > prog_col_idx and pd.notna(row.iloc[prog_col_idx]):
                    prog_value = int(round(float(str(row.iloc[prog_col_idx]).replace(',', '.'))))
                programacion[month] = prog_value

                ejec_value = 0
                if len(row) > ejec_col_idx and pd.notna(row.iloc[ejec_col_idx]):
                    ejec_value = int(round(float(str(row.iloc[ejec_col_idx]).replace(',', '.'))))
                ejecucion[month] = ejec_value

            warnings = self._create_validation_warnings(meta_anual, programacion, ejecucion)

            return {
                "codigo_subproducto": subproduct_code,
                "nombre_subproducto": subproduct_name,
                "unidad_medida": unidad_medida,
                "meta_anual": meta_anual,
                "programado": programacion,
                "ejecutado": ejecucion,
                "warnings": warnings
            }
        except (ValueError, TypeError, IndexError) as e:
            logger.error(f"Error parsing subproduct row: {row}. Error: {e}")
            return None


    def _validate_and_clean_products(self, products: Dict) -> (Dict, List[str]):
        """Validate the extracted structure, cleaning out empty products/activities."""
        validated_products = {}
        logs = []
        
        for prod_code, product_data in products.items():
            if not prod_code or not product_data.get("nombre_producto"):
                logs.append(f"[Descartado] Producto sin código o nombre: {prod_code}")
                continue

            valid_activities = {}
            for act_code, activity_data in product_data.get("actividades", {}).items():
                if activity_data.get("subproductos"):
                    valid_activities[act_code] = activity_data
                else:
                    logs.append(f"[Descartado] Actividad '{act_code}' del producto '{prod_code}' no tiene subproductos.")

            if valid_activities:
                product_data["actividades"] = valid_activities
                validated_products[prod_code] = product_data
            else:
                logs.append(f"[Descartado] Producto '{prod_code}' no tiene actividades con subproductos.")
                
        logger.info(f"Validation complete. Discarded {len(products) - len(validated_products)} products.")
        return validated_products, logs

    
    def _is_numeric_code(self, code_str: str) -> bool:
        """Check if a string represents a numeric code (typically 5-7 digits)"""
        if not code_str or not isinstance(code_str, str):
            return False
        cleaned = code_str.strip()
        return cleaned.isdigit() and len(cleaned) >= 5 and len(cleaned) <= 7
    
    def _create_validation_warnings(self, meta_anual: float, programacion: dict, ejecucion: dict) -> List[str]:
        """Create validation warnings for subproduct data"""
        warnings = []
        
        if meta_anual == 0 and sum(programacion.values()) > 0:
            warnings.append(f"Meta anual es 0 pero hay valores programados")
        
        if any(v < 0 for v in programacion.values()):
            warnings.append(f"Se encontraron valores negativos en programación mensual")
        
        if any(v < 0 for v in ejecucion.values()):
            warnings.append(f"Se encontraron valores negativos en ejecución mensual")
        
        total_programmed = sum(programacion.values())
        if meta_anual > 0 and total_programmed > meta_anual * 1.2:
            warnings.append(f"Total programado ({total_programmed}) excede significativamente la meta anual ({meta_anual})")
        
        if sum(ejecucion.values()) > sum(programacion.values()):
            warnings.append(f"Total ejecutado ({sum(ejecucion.values())}) excede total programado ({sum(programacion.values())})")
        
        programmed_non_zero = sum(1 for v in programacion.values() if v != 0)
        executed_non_zero = sum(1 for v in ejecucion.values() if v != 0)
        
        if programmed_non_zero == 0:
            warnings.append("No se encontraron valores programados")
        
        if executed_non_zero == 0:
            warnings.append("No se encontraron valores ejecutados")
        
        return warnings


class CEPLANExtractorService:
    """Service for extracting CEPLAN data from Excel files"""
    
    def __init__(self):
        """Initialize the CEPLAN extractor service"""
        self.months = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 
                      'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
    
    def extract_ceplan_from_file(self, file_path: Path) -> Dict:
        """Extracts CEPLAN data based on a 2-row structure for each subproduct (Programado/Ejecutado)."""
        logger.info(f"Starting CEPLAN extraction with 2-row P/E logic from file: {file_path}")
        df = pd.read_excel(file_path, header=None, engine='openpyxl')
        
        subproducts = []
        # Use a while loop to manually control the index, as we process 2 rows at a time.
        row_idx = 0
        while row_idx < len(df) -1: # -1 to ensure we can read the next row
            row = df.iloc[row_idx]
            
            # --- 1. Find a subproduct row ---
            code_cell = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
            subproduct_code = self._extract_subproduct_code(code_cell)
            
            if not subproduct_code:
                row_idx += 1
                continue

            logger.debug(f"Found potential subproduct '{subproduct_code}' at row {row_idx}. Reading P/E rows.")

            # --- 2. This is the Programado row. The next row is Ejecutado. ---
            programado_row = row
            ejecutado_row = df.iloc[row_idx + 1]

            programado = {m: 0 for m in self.months}
            ejecutado = {m: 0 for m in self.months}

            # --- 3. Extract 12 monthly values from each row ---
            # Values are in columns 8 to 19 (12 columns)
            for i in range(12):
                col_idx = 8 + i
                month = self.months[i]

                # Extract Programado value
                try:
                    if len(programado_row) > col_idx and pd.notna(programado_row.iloc[col_idx]):
                        cell_str = str(programado_row.iloc[col_idx]).strip()
                        match = re.search(r'[\d,.]+', cell_str)
                        if match:
                            num_str = match.group(0).replace(',', '.')
                            programado[month] = int(round(float(num_str)))
                except (ValueError, TypeError, IndexError):
                    pass # Keep as 0

                # Extract Ejecutado value
                try:
                    if len(ejecutado_row) > col_idx and pd.notna(ejecutado_row.iloc[col_idx]):
                        cell_str = str(ejecutado_row.iloc[col_idx]).strip()
                        match = re.search(r'[\d,.]+', cell_str)
                        if match:
                            num_str = match.group(0).replace(',', '.')
                            ejecutado[month] = int(round(float(num_str)))
                except (ValueError, TypeError, IndexError):
                    pass # Keep as 0
            
            subproducts.append({
                "codigo_subproducto": subproduct_code,
                "nombre_subproducto": str(programado_row.iloc[3]) if len(programado_row) > 3 and pd.notna(programado_row.iloc[3]) else f"Subproducto {subproduct_code}",
                "unidad_medida": str(programado_row.iloc[5]) if len(programado_row) > 5 and pd.notna(programado_row.iloc[5]) else "UNIDAD",
                "programado": programado,
                "ejecutado": ejecutado,
                "meta_anual": sum(programado.values()),
                "warnings": []
            })

            # --- 4. Advance index by 2 to skip the executed row ---
            row_idx += 2

        result = {"subproductos": subproducts, "logs": []}
        logger.info(f"CEPLAN extraction completed. Found {len(subproducts)} subproducts.")
        return result

    def _extract_subproduct_code(self, code_string: str) -> str:
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


# Global instances for use in the application
ppr_extractor_service = PPRExtractorService()
ceplan_extractor_service = CEPLANExtractorService()
