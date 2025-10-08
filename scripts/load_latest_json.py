#!/usr/bin/env python3
"""
Utility to load the most recent JSON file from temp/uploads to the database
This can be run after the preview to commit the data directly to the database
"""

import json
import sys
from pathlib import Path
import glob

# Add the project root to the Python path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.load_json_to_db import load_json_to_db


def load_latest_json():
    """Load the most recent JSON file from temp/uploads directory"""
    temp_dir = Path("temp/uploads")
    
    if not temp_dir.exists():
        print(f"Error: Directory {temp_dir} does not exist")
        return False
    
    # Get all JSON files in the directory
    json_files = list(temp_dir.glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {temp_dir}")
        return False
    
    # Get the most recently created file
    latest_file = max(json_files, key=lambda x: x.stat().st_ctime)
    
    print(f"Found most recent JSON file: {latest_file}")
    print(f"Created on: {latest_file.stat().st_ctime}")
    
    # Load the file to the database
    try:
        result = load_json_to_db(str(latest_file))
        print(f"Successfully loaded data from {latest_file.name}")
        return True
    except Exception as e:
        print(f"Error loading {latest_file.name}: {str(e)}")
        return False


def load_specific_json(filename):
    """Load a specific JSON file from temp/uploads directory"""
    temp_dir = Path("temp/uploads")
    file_path = temp_dir / filename
    
    if not file_path.exists():
        print(f"Error: File {file_path} does not exist")
        return False
    
    try:
        result = load_json_to_db(str(file_path))
        print(f"Successfully loaded data from {filename}")
        return True
    except Exception as e:
        print(f"Error loading {filename}: {str(e)}")
        return False


def list_json_files():
    """List all JSON files in the temp/uploads directory"""
    temp_dir = Path("temp/uploads")
    
    if not temp_dir.exists():
        print(f"Error: Directory {temp_dir} does not exist")
        return
    
    json_files = list(temp_dir.glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {temp_dir}")
        return
    
    print(f"JSON files in {temp_dir}:")
    for file_path in sorted(json_files, key=lambda x: x.stat().st_ctime, reverse=True):
        print(f"  {file_path.name} (created: {file_path.stat().st_ctime})")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python load_latest_json.py list                    # List all JSON files")
        print("  python load_latest_json.py latest                  # Load most recent JSON file")
        print("  python load_latest_json.py <filename>              # Load specific JSON file")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        list_json_files()
    elif command == "latest":
        success = load_latest_json()
        if not success:
            sys.exit(1)
    else:
        filename = command
        success = load_specific_json(filename)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()