"""
Data Export Module
Handles exporting scraped data to various formats (CSV, JSON, Excel).
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import pandas as pd


class DataExporter:
    """Handles data export functionality"""
    
    def __init__(self, output_dir: Path, base_filename: str):
        # Initialize the DataExporter with output directory and base filename
        self.output_dir = Path(output_dir)
        self.base_filename = base_filename
        self.logger = logging.getLogger(__name__)
        
        # Ensure output directory exists by creating it if necessary
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_to_csv(self, data: List[Dict[str, Any]]) -> Path:
        """Export data to CSV format"""
        # Check if there's data to export
        if not data:
            self.logger.warning("No data to export to CSV")
            return None
        
        # Construct the output file path
        csv_file = self.output_dir / f"{self.base_filename}.csv"
        
        try:
            # Flatten nested dictionaries (like item_specifics) for CSV compatibility
            flattened_data = []
            for item in data:
                flattened_item = self._flatten_dict(item)
                flattened_data.append(flattened_item)
            
            # Create DataFrame from flattened data and export to CSV
            df = pd.DataFrame(flattened_data)
            df.to_csv(csv_file, index=False, encoding='utf-8')
            
            # Log successful export
            self.logger.info(f"Successfully exported {len(data)} items to CSV: {csv_file}")
            return csv_file
            
        except Exception as e:
            # Log and re-raise any export errors
            self.logger.error(f"Error exporting to CSV: {str(e)}")
            raise
    
    def export_to_json(self, data: List[Dict[str, Any]]) -> Path:
        """Export data to JSON format"""
        # Check if there's data to export
        if not data:
            self.logger.warning("No data to export to JSON")
            return None
        
        # Construct the output file path
        json_file = self.output_dir / f"{self.base_filename}.json"
        
        try:
            # Add metadata to the JSON output for better documentation
            export_data = {
                'metadata': {
                    'exported_at': datetime.now().isoformat(),
                    'total_items': len(data),
                    'scraper_version': '1.0.0'
                },
                'items': data
            }
            
            # Write JSON data with pretty formatting and UTF-8 encoding
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            # Log successful export
            self.logger.info(f"Successfully exported {len(data)} items to JSON: {json_file}")
            return json_file
            
        except Exception as e:
            # Log and re-raise any export errors
            self.logger.error(f"Error exporting to JSON: {str(e)}")
            raise
    
    def export_to_excel(self, data: List[Dict[str, Any]]) -> Path:
        """Export data to Excel format"""
        # Check if there's data to export
        if not data:
            self.logger.warning("No data to export to Excel")
            return None
        
        # Construct the output file path
        excel_file = self.output_dir / f"{self.base_filename}.xlsx"
        
        try:
            # Flatten nested dictionaries for Excel compatibility
            flattened_data = []
            for item in data:
                flattened_item = self._flatten_dict(item)
                flattened_data.append(flattened_item)
            
            # Create DataFrame from flattened data
            df = pd.DataFrame(flattened_data)
            
            # Export to Excel with formatting options
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # Write main data to worksheet
                df.to_excel(writer, sheet_name='eBay_Products', index=False)
                
                # Auto-adjust column widths for better readability
                worksheet = writer.sheets['eBay_Products']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    # Set column width with reasonable maximum
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Log successful export
            self.logger.info(f"Successfully exported {len(data)} items to Excel: {excel_file}")
            return excel_file
            
        except Exception as e:
            # Log and re-raise any export errors
            self.logger.error(f"Error exporting to Excel: {str(e)}")
            raise
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
        """Flatten nested dictionaries for CSV export"""
        items = []
        
        # Process each key-value pair in the dictionary
        for k, v in d.items():
            # Create new key with parent key prefix if exists
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                # Recursively flatten nested dictionaries
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Convert lists to semicolon-separated strings
                items.append((new_key, '; '.join(str(item) for item in v)))
            else:
                # Add regular key-value pair
                items.append((new_key, v))
        
        # Return flattened dictionary
        return dict(items)
    
    def create_summary_report(self, data: List[Dict[str, Any]]) -> Path:
        """Create a summary report of the scraped data"""
        # Check if there's data to summarize
        if not data:
            return None
        
        # Construct the output file path
        summary_file = self.output_dir / f"{self.base_filename}_summary.txt"
        
        try:
            with open(summary_file, 'w', encoding='utf-8') as f:
                # Write report header
                f.write("eBay Scraping Summary Report\n")
                f.write("=" * 40 + "\n\n")
                
                # Basic statistics
                f.write(f"Total items scraped: {len(data)}\n")
                f.write(f"Scraping completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Price analysis section
                prices = []
                for item in data:
                    price_str = item.get('price', '')
                    if price_str:
                        # Extract numeric price using regex
                        import re
                        price_match = re.search(r'[\d,]+\.?\d*', price_str.replace(',', ''))
                        if price_match:
                            try:
                                prices.append(float(price_match.group().replace(',', '')))
                            except ValueError:
                                pass
                
                # Write price statistics if available
                if prices:
                    f.write("Price Analysis:\n")
                    f.write(f"  Average price: ${sum(prices) / len(prices):.2f}\n")
                    f.write(f"  Minimum price: ${min(prices):.2f}\n")
                    f.write(f"  Maximum price: ${max(prices):.2f}\n\n")
                
                # Condition analysis section
                conditions = {}
                for item in data:
                    condition = item.get('condition', 'Unknown')
                    conditions[condition] = conditions.get(condition, 0) + 1
                
                # Write condition distribution if available
                if conditions:
                    f.write("Condition Distribution:\n")
                    for condition, count in sorted(conditions.items(), key=lambda x: x[1], reverse=True):
                        f.write(f"  {condition}: {count} items\n")
                    f.write("\n")
                
                # Top sellers analysis section
                sold_items = [(item.get('title', 'Unknown'), item.get('quantity_sold', 0)) 
                            for item in data if item.get('quantity_sold')]
                sold_items.sort(key=lambda x: x[1], reverse=True)
                
                # Write top selling items if available
                if sold_items:
                    f.write("Top Selling Items:\n")
                    for title, qty in sold_items[:10]:
                        # Truncate long titles for readability
                        f.write(f"  {qty} sold: {title[:60]}{'...' if len(title) > 60 else ''}\n")
            
            # Log successful report creation
            self.logger.info(f"Summary report created: {summary_file}")
            return summary_file
            
        except Exception as e:
            # Log any errors during report creation
            self.logger.error(f"Error creating summary report: {str(e)}")
            return None