import os
from pathlib import Path

from app import create_app, db
from app.dashboard import create_dashboard

app = create_app(os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    print("\n=== Instrucciones para ejecutar ===")
    print("1. Ejecutar Flask (CRUD): python run.py")
    print("2. Ejecutar Dashboard en otra terminal: python -m app.dashboard")
    print("   O simplemente presiona Ctrl+C y ejecuta: python -m app.dashboard")
    print("======================================\n")
    
    app.run(debug=False, port=8050, use_reloader=False)
