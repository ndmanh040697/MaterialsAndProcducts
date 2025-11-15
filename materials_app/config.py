
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///materials.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Alert threshold for Page 4 (units producible)
    MIN_UNITS_ALERT = int(os.environ.get("MIN_UNITS_ALERT", "1000"))
