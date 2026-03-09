import sys
import os

# Ensure src is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data.db_config import init_db

print("Running init_db() to create new tables if they don't exist...")
init_db()
print("Done!")
