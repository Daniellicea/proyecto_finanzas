from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
jwt = JWTManager()
login_manager.login_view = 'main.login'
login_manager.login_message_category = 'info'

def create_app():
    app = Flask(__name__)
    CORS(app) # Permitir peticiones desde la app móvil
    app.config['SECRET_KEY'] = 'clave_secreta_integrador_123'
    app.config['JWT_SECRET_KEY'] = 'clave_jwt_integrador_456' # Clave para firmar JWT
    
    # Conexión a MySQL Workbench
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:bd2025+@localhost/bancos_mexico'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)

    from app.routes import main
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()

    return app