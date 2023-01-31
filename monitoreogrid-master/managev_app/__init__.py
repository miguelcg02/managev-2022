from flask import Flask
from flask_bootstrap import Bootstrap
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from managev_app.config import DevConfig, Config


db = SQLAlchemy()
bootstrap = Bootstrap()
migrate = Migrate()
login = LoginManager()
login.login_view = "dashboard.login"


def create_app(config_class):
    application = Flask(__name__)
    application.config.from_object(config_class)
    db.init_app(application)
    login.init_app(application)
    migrate.init_app(application, db)
    bootstrap.init_app(application)

    with application.app_context():
        from managev_app.api import bp as api_bp

        application.register_blueprint(api_bp, url_prefix="/api")

        from managev_app.routes import dashboard

        application.register_blueprint(dashboard)

        return application


app = create_app(Config)
