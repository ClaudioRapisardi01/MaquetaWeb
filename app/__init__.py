from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # Configurazione
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-this')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'mysql+pymysql://claudio:Superrapa22@localhost/discografica_db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

    # Inizializzazione estensioni
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Effettua il login per accedere a questa pagina.'
    login_manager.login_message_category = 'warning'

    # Registrazione blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.main import main_bp
    from app.blueprints.artisti import artisti_bp
    from app.blueprints.dischi import dischi_bp
    from app.blueprints.singoli import singoli_bp
    from app.blueprints.eventi import eventi_bp
    from app.blueprints.servizi import servizi_bp
    from app.blueprints.staff import staff_bp
    from app.blueprints.documenti import documenti_bp
    from app.blueprints.news import news_bp
    from app.ruoli import ruoli

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(artisti_bp, url_prefix='/artisti')
    app.register_blueprint(dischi_bp, url_prefix='/dischi')
    app.register_blueprint(singoli_bp, url_prefix='/singoli')
    app.register_blueprint(eventi_bp, url_prefix='/eventi')
    app.register_blueprint(servizi_bp, url_prefix='/servizi')
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(documenti_bp, url_prefix='/documenti')
    app.register_blueprint(news_bp, url_prefix='/news')
    app.register_blueprint(ruoli)

    return app
