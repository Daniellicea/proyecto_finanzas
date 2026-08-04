from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from datetime import timedelta

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
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15) # Tokens validos por 15 minutos
    
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
        try:
            from app.models import Banco
            if Banco.query.count() == 0:
                bancos_default = [
                    Banco(id=1, nombre='BBVA México', pais_origen='México', emite_tarjeta_credito=True, otorga_prestamos=True, tipo_institucion='Banco'),
                    Banco(id=2, nombre='Nu México', pais_origen='México', emite_tarjeta_credito=True, otorga_prestamos=True, tipo_institucion='Sofipo'),
                    Banco(id=3, nombre='Santander', pais_origen='México', emite_tarjeta_credito=True, otorga_prestamos=True, tipo_institucion='Banco'),
                    Banco(id=4, nombre='Citibanamex', pais_origen='México', emite_tarjeta_credito=True, otorga_prestamos=True, tipo_institucion='Banco'),
                    Banco(id=5, nombre='Banorte', pais_origen='México', emite_tarjeta_credito=True, otorga_prestamos=True, tipo_institucion='Banco'),
                    Banco(id=6, nombre='Mercado Pago', pais_origen='México', emite_tarjeta_credito=True, otorga_prestamos=True, tipo_institucion='Fintech'),
                    Banco(id=7, nombre='Hey Banco', pais_origen='México', emite_tarjeta_credito=True, otorga_prestamos=True, tipo_institucion='Banco Digital')
                ]
                db.session.add_all(bancos_default)
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print("Error sembrando bancos:", e)

    return app