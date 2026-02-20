from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, SelectField, IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Regexp, NumberRange, ValidationError
from app.models import User

class RegistrationForm(FlaskForm):
    # Solo letras, espacios y acentos válidos en español. Máximo 50 caracteres.
    nombre = StringField('Nombre(s)', validators=[
        DataRequired(message="El nombre es obligatorio."),
        Length(min=2, max=50, message="El nombre debe tener entre 2 y 50 caracteres."),
        Regexp(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', message="El nombre solo puede contener letras y espacios.")
    ])
    
    # Igual que el nombre, pero permite hasta 100 caracteres.
    apellidos = StringField('Apellidos', validators=[
        DataRequired(message="Los apellidos son obligatorios."),
        Length(min=2, max=100, message="Los apellidos deben tener entre 2 y 100 caracteres."),
        Regexp(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', message="Los apellidos solo pueden contener letras y espacios.")
    ])
    
    edad = IntegerField('Edad', validators=[
        DataRequired(message="Ingresa tu edad."),
        NumberRange(min=18, max=120, message="Debes tener entre 18 y 120 años para usar el sistema.")
    ])
    
    # Obliga a que sean exactamente 10 dígitos numéricos (sin guiones ni espacios)
    telefono = StringField('Teléfono Celular', validators=[
        DataRequired(message="El teléfono es obligatorio."),
        Regexp(r'^\d{10}$', message="El teléfono debe tener exactamente 10 números.")
    ])
    
    # Máximo 120 caracteres (como en la base de datos)
    email = StringField('Correo Electrónico', validators=[
        DataRequired(message="El correo es obligatorio."), 
        Email(message="Ingresa un correo electrónico válido."),
        Length(max=120, message="El correo no puede exceder los 120 caracteres.")
    ])
    
    # Contraseña segura con límite para evitar ataques de desbordamiento
    password = PasswordField('Contraseña', validators=[
        DataRequired(message="La contraseña es obligatoria."), 
        Length(min=8, max=50, message="La contraseña debe tener entre 8 y 50 caracteres.")
    ])
    
    confirm_password = PasswordField('Confirmar Contraseña', validators=[
        DataRequired(message="Por favor, confirma tu contraseña."), 
        EqualTo('password', message='Las contraseñas no coinciden.')
    ])
    
    submit = SubmitField('Comenzar mi transformación')

    # Validador personalizado: Evita que se caiga la app si el correo ya existe
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Este correo ya está registrado. Por favor, inicia sesión o usa uno diferente.')

class LoginForm(FlaskForm):
    email = StringField('Correo Electrónico', validators=[
        DataRequired(message="Ingresa tu correo."), 
        Email(message="Formato de correo inválido.")
    ])
    password = PasswordField('Contraseña', validators=[DataRequired(message="Ingresa tu contraseña.")])
    submit = SubmitField('Ingresar')

class DeudaForm(FlaskForm):
    banco_id = SelectField('Institución Financiera', coerce=int, validators=[
        DataRequired(message="Selecciona una institución.")
    ])
    
    # Validamos que los montos financieros no sean negativos ni letras
    limite = FloatField('Límite de Crédito Total ($)', validators=[
        DataRequired(message="Necesitamos tu límite para calcular tu Score."),
        NumberRange(min=1, message="El límite debe ser mayor a cero.")
    ])
    monto = FloatField('Deuda Actual ($)', validators=[
        DataRequired(message="Ingresa el monto que debes actualmente."),
        NumberRange(min=0, message="El monto no puede ser negativo.")
    ])
    tasa = FloatField('Tasa Anual (%)', validators=[
        DataRequired(message="Ingresa la tasa de interés."),
        NumberRange(min=0, max=200, message="La tasa debe estar entre 0% y 200%.")
    ])
    minimo = FloatField('Pago Mínimo ($)', validators=[
        DataRequired(message="Ingresa tu pago mínimo requerido."),
        NumberRange(min=0, message="El pago mínimo no puede ser negativo.")
    ])
    submit = SubmitField('Agregar Crédito')

class GastoForm(FlaskForm):
    # Protegemos el campo descripción para que no exceda la base de datos (100)
    descripcion = StringField('¿En qué gastaste?', validators=[
        DataRequired(message="Describe tu gasto."), 
        Length(min=2, max=100, message="La descripción debe tener entre 2 y 100 caracteres.")
    ])
    monto = FloatField('Monto ($)', validators=[
        DataRequired(message="Ingresa cuánto gastaste."),
        NumberRange(min=0.1, message="El monto debe ser mayor a cero.")
    ])
    categoria = SelectField('Categoría de Gasto', choices=[
        ('Hormiga', 'Gasto Hormiga (Snacks, antojos, apps)'), 
        ('Fijo', 'Gasto Fijo (Renta, Luz, Agua)'), 
        ('Variable', 'Gasto Variable (Ropa, Salidas)')
    ], validators=[DataRequired(message="Selecciona una categoría.")])
    submit = SubmitField('Registrar Gasto')