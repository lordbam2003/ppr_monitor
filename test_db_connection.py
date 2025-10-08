import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.core.database import engine

def test_database_connection():
    """Test if the database connection works"""
    print(f"Database URL: {settings.database_url}")
    
    try:
        # Try to connect to the database
        with engine.connect() as connection:
            print("[SUCCESS] Database connection successful!")
            # Try a simple query
            from sqlalchemy import text
            result = connection.execute(text("SELECT 1"))
            print(f"[SUCCESS] Query executed successfully: {result.fetchone()}")
            return True
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing database connection...")
    success = test_database_connection()
    if success:
        print("\nDatabase connection test passed!")
    else:
        print("\nDatabase connection test failed!")
        sys.exit(1)