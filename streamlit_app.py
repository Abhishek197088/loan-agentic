import sys
from pathlib import Path

# Ensure root directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Run the primary Streamlit application located in frontend/app.py
target_file = BASE_DIR / "frontend" / "app.py"
with open(target_file, "r", encoding="utf-8") as f:
    code = compile(f.read(), str(target_file), "exec")
    exec(code, globals())
