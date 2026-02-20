from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Banco(db.Model):
    __tablename__ = 'bancos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    pais_origen = db.Column(db.String(100))
    emite_tarjeta_credito = db.Column(db.Boolean, nullable=False)
    otorga_prestamos = db.Column(db.Boolean, nullable=False)
    tipo_institucion = db.Column(db.String(50))
    deudas = db.relationship('Deuda', backref='institucion', lazy=True)

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    # Ya no hay username, ahora usamos nombre y apellidos
    nombre = db.Column(db.String(50), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    edad = db.Column(db.Integer, nullable=False)
    telefono = db.Column(db.String(10), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    ingreso_mensual = db.Column(db.Float, default=0.0)
    gastos_fijos = db.Column(db.Float, default=0.0)
    estrategia_preferida = db.Column(db.String(20), default='avalancha')
    deudas = db.relationship('Deuda', backref='author', lazy=True)
    gastos = db.relationship('Gasto', backref='author', lazy=True)

class Deuda(db.Model):
    __tablename__ = 'deuda'
    id = db.Column(db.Integer, primary_key=True)
    monto = db.Column(db.Float, nullable=False)
    limite = db.Column(db.Float, nullable=False, default=0.0)
    tasa = db.Column(db.Float, nullable=False)
    minimo = db.Column(db.Float, nullable=False)
    banco_id = db.Column(db.Integer, db.ForeignKey('bancos.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Gasto(db.Model):
    __tablename__ = 'gasto'
    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(100), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)