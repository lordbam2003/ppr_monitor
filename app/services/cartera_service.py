"""
Service for handling Cartera de Servicios data
"""
import pandas as pd
import re
from pathlib import Path
from typing import Dict, List, Tuple
import logging
from sqlmodel import Session, select

from app.models.cartera_servicios import CarteraServicios
from app.services.extractor_service import PPRExtractorService

logger = logging.getLogger(__name__)


class CarteraService:
    """Service for handling Cartera de Servicios data from Excel files"""
    
    def __init__(self):
        self.columns_mapping = {
            'programa': ['programa', 'codigo programa', 'cod programa'],
            'producto': ['producto', 'codigo producto', 'cod producto'],
            'actividad': ['actividad', 'codigo actividad', 'cod actividad'],
            'sub_producto': ['sub producto', 'subproducto', 'codigo sub producto', 'cod sub producto'],
            'trazador': ['trazador', 'indicador'],
            'unidad_medida': ['unidad de medida', 'unidad medida', 'umed', 'u.m.']
        }
    
    def extract_cartera_from_file(self, file_path: Path) -> Dict:
        """
        Extract Cartera de Servicios data from Excel file
        Expected format: Programa;Producto;Actividad;Sub Producto;Trazador;Unidad de Medida
        Each field contains both code and name which will be separated
        """
        logger.info(f"Starting Cartera de Servicios extraction from file: {file_path}")
        
        try:
            # Determine the appropriate engine based on file extension
            file_extension = file_path.suffix.lower()
            
            if file_extension == '.xlsx':
                # For .xlsx files, use openpyxl engine (which is already in dependencies)
                df = pd.read_excel(file_path, header=None, engine='openpyxl')
                logger.info(f"Loaded .xlsx Excel file with openpyxl engine. Shape: {df.shape}")
            elif file_extension == '.xls':
                # For .xls files, try xlrd engine first
                try:
                    df = pd.read_excel(file_path, header=None, engine='xlrd')
                    logger.info(f"Loaded .xls Excel file with xlrd engine. Shape: {df.shape}")
                except ImportError:
                    # If xlrd is not available, warn and try default engine
                    logger.warning("xlrd not available, install it for better .xls support: pip install xlrd>=2.0.0")
                    logger.info("Trying default engine for .xls file...")
                    df = pd.read_excel(file_path, header=None)
                    logger.info(f"Loaded .xls Excel file with default engine. Shape: {df.shape}")
                except Exception as e:
                    # If xlrd fails for other reasons, try default engine
                    logger.warning(f"xlrd failed to read .xls file ({str(e)}), trying default engine...")
                    df = pd.read_excel(file_path, header=None)
                    logger.info(f"Loaded .xls Excel file with default engine after xlrd failure. Shape: {df.shape}")
            else:
                # For unknown extensions, try default engine
                df = pd.read_excel(file_path, header=None)
                logger.info(f"Loaded Excel file with default engine. Shape: {df.shape}")
            
            logger.info(f"Loaded Excel file with {len(df)} rows and {len(df.columns)} columns")
            
            # Find header row and column positions
            header_positions = self._find_cartera_header_positions(df)
            
            if not header_positions:
                logger.error("Could not find expected headers in the file")
                raise ValueError("No valid headers found. Expected columns: Programa, Producto, Actividad, Sub Producto, Trazador, Unidad de Medida")
            
            # Extract data starting from the row after headers
            cartera_data = self._extract_cartera_data(df, header_positions)
            
            result = {
                "cartera": cartera_data,
                "total_records": len(cartera_data)
            }
            
            logger.info(f"Cartera de Servicios extraction completed. Found {len(cartera_data)} records.")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting Cartera de Servicios data from {file_path}: {str(e)}", exc_info=True)
            raise e
    
    def _find_cartera_header_positions(self, df: pd.DataFrame) -> Dict[str, int]:
        """Find positions of Cartera headers in the Excel file"""
        logger.info("Searching for Cartera headers...")
        
        # Define comprehensive patterns for each column type
        column_patterns = {
            'programa': [
                'programa', 'codigo programa', 'cod programa', 'ppr', 'codigo ppr', 'cod ppr',
                'codprograma', 'codppr', 'codigo', 'cod', 'programa presupuestal', 'ppr.codigo'
            ],
            'producto': [
                'producto', 'codigo producto', 'cod producto', 'prod', 'codigo prod', 'cod prod',
                'codproducto', 'codprod', 'producto.codigo', 'prod.codigo'
            ],
            'actividad': [
                'actividad', 'codigo actividad', 'cod actividad', 'act', 'codigo act', 'cod act',
                'codactividad', 'codact', 'actividad.codigo', 'act.codigo'
            ],
            'sub_producto': [
                'subproducto', 'sub producto', 'subproducto.codigo', 'sub producto.codigo',
                'codigo subproducto', 'codigo sub producto', 'cod subproducto', 'cod sub producto',
                'subprod', 'codigo subprod', 'cod subprod'
            ],
            'trazador': [
                'trazador', 'indicador', 'traz', 'codigo trazador', 'cod trazador',
                'trazador.codigo', 'indicador.codigo'
            ],
            'unidad_medida': [
                'unidad de medida', 'unidad medida', 'umed', 'u.m.', 'unidad', 'medida',
                'umedida', 'unidad.medida', 'um'
            ]
        }
        
        for row_idx in range(min(10, len(df))):  # Check first 10 rows for headers
            row = df.iloc[row_idx]
            
            # Check each cell in the row
            for col_idx in range(len(row)):
                cell_value = row.iloc[col_idx]
                if pd.notna(cell_value):
                    cell_text = str(cell_value)
                    normalized_cell_text = self._normalize_text(cell_text)
                    
                    # Check if this cell matches any column type
                    for column_type, patterns in column_patterns.items():
                        for pattern in patterns:
                            # Use normalized text for comparison
                            normalized_pattern = self._normalize_text(pattern)
                            if normalized_pattern in normalized_cell_text:
                                # If we haven't already found this header type, record it
                                if column_type not in locals().get('header_positions', {}):
                                    if 'header_positions' not in locals():
                                        header_positions = {}
                                    header_positions[column_type] = col_idx
                                    logger.debug(f"Found {column_type} header at row {row_idx}, col {col_idx}: '{cell_text}' (matched: '{pattern}')")
                                    break  # Move to the next column type once a match is found
                        
            # Check if we found all required headers
            required_headers = ['programa', 'producto', 'actividad', 'sub_producto', 'trazador', 'unidad_medida']
            if 'header_positions' in locals() and all(header in header_positions for header in required_headers):
                header_positions['data_start_row'] = row_idx + 1
                logger.info(f"All required headers found: {header_positions}")
                return header_positions
        
        # If we didn't find all headers, log which ones are missing
        if 'header_positions' in locals():
            missing_headers = [h for h in required_headers if h not in header_positions]
        else:
            missing_headers = required_headers
        
        logger.warning(f"Could not find all required headers. Missing: {missing_headers}")
        return {}
    
    def _extract_cartera_data(self, df: pd.DataFrame, header_positions: Dict[str, int]) -> List[Dict]:
        """Extract Cartera data from the Excel file using header positions"""
        logger.info("Extracting Cartera data...")
        
        cartera_records = []
        
        data_start_row = header_positions.get('data_start_row', 0)
        
        for row_idx in range(data_start_row, len(df)):
            row = df.iloc[row_idx]
            
            if row.isnull().all():
                continue  # Skip empty rows
            
            # Extract values using header positions
            try:
                programa = str(row.iloc[header_positions['programa']]) if header_positions['programa'] < len(row) and pd.notna(row.iloc[header_positions['programa']]) else ""
                producto = str(row.iloc[header_positions['producto']]) if header_positions['producto'] < len(row) and pd.notna(row.iloc[header_positions['producto']]) else ""
                actividad = str(row.iloc[header_positions['actividad']]) if header_positions['actividad'] < len(row) and pd.notna(row.iloc[header_positions['actividad']]) else ""
                sub_producto = str(row.iloc[header_positions['sub_producto']]) if header_positions['sub_producto'] < len(row) and pd.notna(row.iloc[header_positions['sub_producto']]) else ""
                trazador = str(row.iloc[header_positions['trazador']]) if header_positions['trazador'] < len(row) and pd.notna(row.iloc[header_positions['trazador']]) else ""
                unidad_medida = str(row.iloc[header_positions['unidad_medida']]) if header_positions['unidad_medida'] < len(row) and pd.notna(row.iloc[header_positions['unidad_medida']]) else ""
                
                # Only add record if we have at least minimum required data
                if programa or producto or actividad or sub_producto:
                    # Extract code and name from each field
                    programa_codigo, programa_nombre = self._extract_code_name(programa)
                    producto_codigo, producto_nombre = self._extract_code_name(producto)
                    actividad_codigo, actividad_nombre = self._extract_code_name(actividad)
                    sub_producto_codigo, sub_producto_nombre = self._extract_code_name(sub_producto)
                    
                    record = {
                        "programa_codigo": programa_codigo,
                        "programa_nombre": programa_nombre,
                        "producto_codigo": producto_codigo,
                        "producto_nombre": producto_nombre,
                        "actividad_codigo": actividad_codigo,
                        "actividad_nombre": actividad_nombre,
                        "sub_producto_codigo": sub_producto_codigo,
                        "sub_producto_nombre": sub_producto_nombre,
                        "trazador": trazador.strip(),
                        "unidad_medida": unidad_medida.strip()
                    }
                    cartera_records.append(record)
                    
            except IndexError:
                logger.warning(f"Row {row_idx} doesn't have enough columns, skipping...")
                continue
        
        logger.info(f"Extracted {len(cartera_records)} records from Cartera data")
        return cartera_records
    
    def _extract_code_name(self, text: str) -> Tuple[str, str]:
        """
        Extract code and name from a combined field.
        Expected format: "0002 SALUD MATERNO NEONATAL" or "3000001 ACCIONES COMUNES"
        """
        if not text or not isinstance(text, str):
            return "", ""
        
        text = text.strip()
        if not text:
            return "", ""
        
        # Pattern to match code followed by name
        # Looks for digits followed by optional spaces and then the name
        match = re.match(r'^(\d+(?:\.\d+)?)\s+(.+)$', text.strip())
        if match:
            code = match.group(1).strip()
            name = match.group(2).strip()
            return code, name
        
        # Alternative pattern for longer codes like the example "3000001 ACCIONES COMUNES"
        match = re.match(r'^(\d{3,})\s+(.+)$', text.strip())
        if match:
            code = match.group(1).strip()
            name = match.group(2).strip()
            return code, name
        
        # If no match found, return empty code and full text as name
        return "", text

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison (same as in extractor_service)"""
        import unicodedata
        # Convert to lowercase and normalize unicode characters
        text = str(text).lower()
        # Remove accents and special characters
        text = unicodedata.normalize('NFKD', text).encode('ascii', errors='ignore').decode()
        # Remove common punctuation and special characters that might appear in headers
        import re
        # Replace common punctuation with spaces and remove special characters
        text = re.sub(r'[\\s\\-\\_\\.\\,\\:]+', ' ', text)  # Replace multiple spaces, hyphens, underscores, dots, commas, colons with single space
        # Remove non-alphanumeric characters but keep spaces
        text = re.sub(r'[^a-z0-9\\s]', '', text)
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove common words that might appear in headers
        text = re.sub(r'\\b(el|la|de|del|al|a|e|i|o|u)\\b', '', text)
        # Remove extra spaces again after removing common words
        text = ' '.join(text.split())
        return text

    def store_cartera_data(self, cartera_data: Dict, session: Session) -> Dict:
        """Store Cartera de Servicios data to database"""
        try:
            cartera_records = cartera_data.get("cartera", [])
            
            # Clear existing cartera data if needed or append
            # For now, we'll just add new records (you could implement a clear strategy based on requirements)
            
            stored_count = 0
            for record in cartera_records:
                new_cartera = CarteraServicios(
                    programa_codigo=record.get("programa_codigo", ""),
                    programa_nombre=record.get("programa_nombre", ""),
                    producto_codigo=record.get("producto_codigo", ""),
                    producto_nombre=record.get("producto_nombre", ""),
                    actividad_codigo=record.get("actividad_codigo", ""),
                    actividad_nombre=record.get("actividad_nombre", ""),
                    sub_producto_codigo=record.get("sub_producto_codigo", ""),
                    sub_producto_nombre=record.get("sub_producto_nombre", ""),
                    trazador=record.get("trazador", ""),
                    unidad_medida=record.get("unidad_medida", "")
                )
                
                session.add(new_cartera)
                stored_count += 1
            
            session.commit()
            logger.info(f"Successfully stored {stored_count} Cartera de Servicios records")
            
            return {
                "stored_count": stored_count,
                "message": f"Successfully stored {stored_count} service portfolio records"
            }
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing Cartera de Servicios data: {str(e)}", exc_info=True)
            raise e

# Global instance
cartera_service = CarteraService()