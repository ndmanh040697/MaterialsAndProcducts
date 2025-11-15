# myproject/__init__.py
from flask import Flask
def create_app():
    app = Flask(__name__)
    # init db, register_blueprints: inventory, fg, ...
    return app

app = create_app()   # 👈 để Procfile có thể trỏ myproject:app
