import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Data"

DATA_DIR.mkdir(exist_ok=True)
(DATA_DIR / "backups").mkdir(exist_ok=True)
(DATA_DIR / "import").mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")


def get_database_uri():
    db_type = os.environ.get("DB_TYPE", "sqlite")
    db_name = os.environ.get("DB_NAME", "wms_data.db")
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5432")
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = os.environ.get("DB_PASSWORD", "")
    
    if db_type == "sqlite":
        return f"sqlite:///{DATA_DIR / db_name}"
    elif db_type == "postgresql":
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    elif db_type == "mysql":
        return f"mysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    return f"sqlite:///{DATA_DIR / db_name}"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    
    BASE_DIR = str(BASE_DIR)
    DATA_DIR = str(DATA_DIR)
    
    DB_TYPE = os.environ.get("DB_TYPE", "sqlite")
    DB_NAME = os.environ.get("DB_NAME", "wms_data.db")
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "5432")
    DB_USER = os.environ.get("DB_USER", "postgres")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    
    CSV_FILE = os.environ.get("CSV_FILE", "datos.csv")
    BACKUP_DIR = str(Path(DATA_DIR) / "backups")
    BACKUP_DIR_NAME = "backups"
    IMPORT_DIR = str(Path(DATA_DIR) / "import")
    
    AUDIT_USER = os.environ.get("AUDIT_USER", "ui_user")
    ALLOWED_EXTENSIONS = {"csv"}
    
    FLASK_PORT = int(os.environ.get("FLASK_PORT", "8050"))
    DASH_PORT = int(os.environ.get("DASH_PORT", "8051"))
    DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
    
    WORKERS = int(os.environ.get("WORKERS", "4"))
    TIMEOUT = int(os.environ.get("TIMEOUT", "120"))
    
    @property
    def DB_FILE(self):
        return str(Path(self.DATA_DIR) / self.DB_NAME)
    
    @property
    def CSV_FILE_PATH(self):
        return str(Path(self.BASE_DIR) / self.CSV_FILE)


class DevelopmentConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    TESTING = True
    DB_NAME = "test.db"
