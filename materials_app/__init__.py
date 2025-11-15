
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .config import Config


db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from .routes.bom import bp as bom_bp
    from .routes.inventory import bp as inv_bp
    from .routes.issues import bp as issue_bp
    from .routes.projections import bp as proj_bp
    from .routes.fg_inventory import bp as fg_bp

    app.register_blueprint(bom_bp, url_prefix="/bom")
    app.register_blueprint(inv_bp, url_prefix="/inventory")
    app.register_blueprint(issue_bp, url_prefix="/issues")
    app.register_blueprint(proj_bp, url_prefix="/projections")
    app.register_blueprint(fg_bp, url_prefix="/fg")

    @app.route("/")
    def index():
        from flask import redirect, url_for
        return redirect(url_for("bom.bom_list"))

    return app
