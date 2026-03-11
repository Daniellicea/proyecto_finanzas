import base64
import numpy as np
import cv2
import face_recognition
import json

from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify
from flask_login import login_user, current_user, logout_user, login_required

from app import db, bcrypt
from app.forms import RegistrationForm, LoginForm, DeudaForm, GastoForm
from app.models import User, Deuda, Banco, Gasto
from app.utils import generar_plan

main = Blueprint('main', __name__)

# ---------------------------------------------------------
# FUNCIONES PARA FACE ID
# ---------------------------------------------------------

def procesar_rostro_file(file_storage):
    try:
        file_bytes = np.frombuffer(file_storage.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(rgb_img)

        if len(encodings) > 0:
            return encodings[0].tolist()
        return None

    except Exception as e:
        print("Error FaceID:", e)
        return None


def procesar_rostro_base64(base64_str):

    try:

        if not base64_str:
            return None

        format, imgstr = base64_str.split(';base64,')
        data = base64.b64decode(imgstr)

        nparr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        encodings = face_recognition.face_encodings(rgb_img)

        if len(encodings) > 0:
            return encodings[0].tolist()

        return None

    except Exception as e:
        print("Error FaceID:", e)
        return None


# ---------------------------------------------------------
# RUTAS PUBLICAS
# ---------------------------------------------------------

@main.route("/")
def home():
    return render_template('home.html')


# ---------------------------------------------------------
# REGISTRO
# ---------------------------------------------------------

@main.route("/register", methods=['GET', 'POST'])
def register():

    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegistrationForm()

    if form.validate_on_submit():

        face_encoding_json = None

        if 'face_file' in request.files:

            file = request.files['face_file']

            encoding = procesar_rostro_file(file)

            if encoding:
                face_encoding_json = json.dumps(encoding)

        hashed_pw = bcrypt.generate_password_hash(
            form.password.data).decode('utf-8')

        user = User(
            nombre=form.nombre.data,
            apellidos=form.apellidos.data,
            edad=form.edad.data,
            telefono=form.telefono.data,
            email=form.email.data,
            password_hash=hashed_pw,
            face_encoding=face_encoding_json
        )

        db.session.add(user)
        db.session.commit()

        flash('Cuenta creada correctamente', 'success')

        return redirect(url_for('main.login'))

    return render_template('register.html', form=form)


# ---------------------------------------------------------
# LOGIN NORMAL
# ---------------------------------------------------------

@main.route("/login", methods=['GET', 'POST'])
def login():

    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()

    if form.validate_on_submit():

        user = User.query.filter_by(email=form.email.data).first()

        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):

            login_user(user)

            return redirect(url_for('main.dashboard'))

        else:

            flash("Correo o contraseña incorrectos", "danger")

    return render_template('login.html', form=form)


# ---------------------------------------------------------
# LOGIN FACE ID
# ---------------------------------------------------------

@main.route("/login_face_id", methods=['POST'])
def login_face_id():

    data = request.json.get("image")

    encoding_actual = procesar_rostro_base64(data)

    if not encoding_actual:

        return jsonify({
            "success": False,
            "message": "No se detectó rostro"
        })

    usuarios = User.query.filter(User.face_encoding != None).all()

    for user in usuarios:

        encoding_db = np.array(json.loads(user.face_encoding))

        match = face_recognition.compare_faces(
            [encoding_db],
            np.array(encoding_actual),
            tolerance=0.5
        )

        if match[0]:

            login_user(user)

            return jsonify({
                "success": True
            })

    return jsonify({
        "success": False,
        "message": "Rostro no reconocido"
    })


# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------

@main.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.home'))


# ---------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------

@main.route("/dashboard", methods=['GET', 'POST'])
@login_required
def dashboard():

    form = DeudaForm()

    bancos = Banco.query.all()

    form.banco_id.choices = [(b.id, b.nombre) for b in bancos]

    if form.validate_on_submit():

        deuda = Deuda(

            banco_id=form.banco_id.data,
            monto=form.monto.data,
            limite=form.limite.data,
            tasa=form.tasa.data,
            minimo=form.minimo.data,
            user_id=current_user.id

        )

        db.session.add(deuda)
        db.session.commit()

        flash("Crédito registrado", "success")

        return redirect(url_for('main.dashboard'))

    deudas = Deuda.query.filter_by(user_id=current_user.id).all()

    plan = generar_plan(deudas)

    return render_template(
        "dashboard.html",
        form=form,
        plan=plan
    )


# ---------------------------------------------------------
# GASTOS
# ---------------------------------------------------------

@main.route("/gastos", methods=['GET', 'POST'])
@login_required
def gastos():

    form = GastoForm()

    if form.validate_on_submit():

        gasto = Gasto(
            descripcion=form.descripcion.data,
            monto=form.monto.data,
            categoria=form.categoria.data,
            user_id=current_user.id
        )

        db.session.add(gasto)
        db.session.commit()

        flash("Gasto agregado", "success")

        return redirect(url_for('main.gastos'))

    mis_gastos = Gasto.query.filter_by(
        user_id=current_user.id).order_by(Gasto.fecha.desc()).all()

    total_hormiga = sum(g.monto for g in mis_gastos if g.categoria == "Hormiga")

    total_general = sum(g.monto for g in mis_gastos)

    return render_template(
        "gastos.html",
        form=form,
        gastos=mis_gastos,
        total_hormiga=total_hormiga,
        total_general=total_general
    )


# ---------------------------------------------------------
# ANALISIS
# ---------------------------------------------------------

@main.route("/analisis")
@login_required
def analisis():

    deudas = Deuda.query.filter_by(user_id=current_user.id).all()

    total_deuda = sum(d.monto for d in deudas)

    total_limite = sum(d.limite for d in deudas)

    if total_limite > 0:
        utilizacion = (total_deuda / total_limite) * 100
    else:
        utilizacion = 0

    score = 850

    if utilizacion > 80:
        score -= 250
    elif utilizacion > 50:
        score -= 150
    elif utilizacion > 30:
        score -= 50
    elif total_deuda == 0 and total_limite == 0:
        score = 0

    return render_template(
        "analisis.html",
        score=score,
        utilizacion=utilizacion,
        total_deuda=total_deuda,
        total_limite=total_limite,
        deudas=deudas
    )


# ---------------------------------------------------------
# EDUCACION
# ---------------------------------------------------------

@main.route("/educacion")
def educacion():
    return render_template("educacion.html")