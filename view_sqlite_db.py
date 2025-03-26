#!/usr/bin/env python3
"""
SQLite Database Viewer
-----------------------
A simple script to explore the structure and contents of a SQLite database.
Usage: python view_sqlite_db.py path/to/database.db
"""

import sqlite3
import sys
import json
from pathlib import Path

def print_header(text, width=80):
    """Print a formatted header."""
    print("\n" + "=" * width)
    print(f" {text} ".center(width, "="))
    print("=" * width)

def print_subheader(text, width=80):
    """Print a formatted subheader."""
    print("\n" + "-" * width)
    print(f" {text} ".center(width, "-"))
    print("-" * width)

def format_value(value):
    """Format a value for display, handling JSON, large text, etc."""
    if value is None:
        return "NULL"
    
    # Convert to string
    str_val = str(value)
    
    # Try to parse as JSON for nicer formatting
    if isinstance(value, str) and (str_val.startswith('{') or str_val.startswith('[')):
        try:
            parsed = json.loads(value)
            return json.dumps(parsed, indent=2)
        except:
            pass
    
    # Truncate long values
    if len(str_val) > 100:
        return str_val[:97] + "..."
    
    return str_val

def view_database(db_path):
    """View the contents of a SQLite database."""
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall()]
        
        print_header(f"Database: {db_path}")
        print(f"Found {len(tables)} tables: {', '.join(tables)}")
        
        # For each table, show schema and data
        for table in tables:
            print_subheader(f"Table: {table}")
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table});")
            columns = cursor.fetchall()
            print("\nSchema:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})" + (" PRIMARY KEY" if col[5] else ""))
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            row_count = cursor.fetchone()[0]
            print(f"\nTotal rows: {row_count}")
            
            # Show data (limited to first 20 rows)
            if row_count > 0:
                print("\nData (up to 20 rows):")
                cursor.execute(f"SELECT * FROM {table} LIMIT 20;")
                rows = cursor.fetchall()
                
                # Get column names
                column_names = [col[1] for col in columns]
                
                # Print data in a readable format
                for row in rows:
                    print("\n  Row:")
                    for i, value in enumerate(row):
                        formatted_value = format_value(value)
                        # Add indentation for multi-line values
                        if "\n" in formatted_value:
                            formatted_value = "\n    " + formatted_value.replace("\n", "\n    ")
                        print(f"    {column_names[i]}: {formatted_value}")
                
                if row_count > 20:
                    print(f"\n  ... and {row_count - 20} more rows")
            
        conn.close()
        print("\nDatabase inspection complete.")
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python view_sqlite_db.py path/to/database.db")
        sys.exit(1)
    
    db_path = sys.argv[1]
    if not Path(db_path).exists():
        print(f"Error: Database file {db_path} not found")
        sys.exit(1)
    
    view_database(db_path)