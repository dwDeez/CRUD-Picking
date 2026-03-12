import os
from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app(config_name: str = "development") -> Flask:
    app = Flask(__name__)
    
    config_map = {
        "development": "DevelopmentConfig",
        "production": "ProductionConfig",
        "testing": "TestingConfig",
    }
    config_class = config_map.get(config_name.lower(), "DevelopmentConfig")
    app.config.from_object(f"app.config.{config_class}")
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        print(f"Base de datos inicializada en: {app.config.get('DATA_DIR')}")
    
    from app.routes import register_routes
    register_routes(app)
    
    return app
