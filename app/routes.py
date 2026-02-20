from flask import Blueprint, render_template, url_for, flash, redirect, request
from app import db, bcrypt
from app.forms import RegistrationForm, LoginForm, DeudaForm, GastoForm
from app.models import User, Deuda, Banco, Gasto
from app.utils import generar_plan
from flask_login import login_user, current_user, logout_user, login_required

main = Blueprint('main', __name__)

@main.route("/")
def home():
    return render_template('home.html', title='Inicio')

@main.route("/educacion")
def educacion():
    return render_template('educacion.html', title='Academia Financiera')

@main.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        # Guardamos sin username
        user = User(
            nombre=form.nombre.data,
            apellidos=form.apellidos.data,
            edad=form.edad.data,
            telefono=form.telefono.data,
            email=form.email.data, 
            password=hashed_pw
        )
        db.session.add(user)
        db.session.commit()
        flash('Cuenta creada exitosamente. Ya puedes iniciar sesión en Widata.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Registro', form=form)

@main.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Error de inicio de sesión. Por favor verifica tu correo y contraseña.', 'danger')
    return render_template('login.html', title='Login', form=form)

@main.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.home'))

@main.route("/dashboard", methods=['GET', 'POST'])
@login_required
def dashboard():
    form = DeudaForm()
    bancos_disp = Banco.query.filter((Banco.emite_tarjeta_credito == True) | (Banco.otorga_prestamos == True)).all()
    form.banco_id.choices = [(b.id, b.nombre) for b in bancos_disp]
    
    if form.validate_on_submit():
        deuda = Deuda(banco_id=form.banco_id.data, monto=form.monto.data, limite=form.limite.data, tasa=form.tasa.data, minimo=form.minimo.data, author=current_user)
        db.session.add(deuda)
        db.session.commit()
        flash('Crédito registrado exitosamente.', 'success')
        return redirect(url_for('main.dashboard'))
        
    deudas = Deuda.query.filter_by(user_id=current_user.id).all()
    plan = generar_plan(deudas)
    return render_template('dashboard.html', title='Pilar 1: Estrategias', form=form, plan=plan)

@main.route("/gastos", methods=['GET', 'POST'])
@login_required
def gastos():
    form = GastoForm()
    if form.validate_on_submit():
        nuevo_gasto = Gasto(descripcion=form.descripcion.data, monto=form.monto.data, categoria=form.categoria.data, author=current_user)
        db.session.add(nuevo_gasto)
        db.session.commit()
        flash('Gasto registrado. ¡Mantén el control de tu dinero!', 'success')
        return redirect(url_for('main.gastos'))
    
    mis_gastos = Gasto.query.filter_by(user_id=current_user.id).order_by(Gasto.fecha.desc()).all()
    total_hormiga = sum(g.monto for g in mis_gastos if g.categoria == 'Hormiga')
    total_general = sum(g.monto for g in mis_gastos)
    
    return render_template('gastos.html', title='Pilar 2: Fugas', form=form, gastos=mis_gastos, total_hormiga=total_hormiga, total_general=total_general)

@main.route("/analisis")
@login_required
def analisis():
    deudas = Deuda.query.filter_by(user_id=current_user.id).all()
    total_deuda = sum(d.monto for d in deudas)
    total_limite = sum(d.limite for d in deudas)
    
    utilizacion = 0
    if total_limite > 0:
        utilizacion = (total_deuda / total_limite) * 100
        
    score = 850
    if utilizacion > 80: score -= 250   
    elif utilizacion > 50: score -= 150 
    elif utilizacion > 30: score -= 50  
    elif total_deuda == 0 and total_limite == 0: score = 0 
    
    return render_template('analisis.html', title='Pilar 3: Score', score=score, utilizacion=utilizacion, total_deuda=total_deuda, total_limite=total_limite, deudas=deudas)