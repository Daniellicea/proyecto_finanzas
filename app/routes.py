import base64
import numpy as np
import cv2
import face_recognition
import json

from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify
from flask_login import login_user, current_user, logout_user, login_required
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

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
# API ROUTES (Para la App Móvil)
# ---------------------------------------------------------

@main.route('/api/register', methods=['POST'])
@main.route('/usuarios/', methods=['POST'])
@main.route('/usuarios', methods=['POST'])
def api_register():
    data = request.get_json() or {}
    nombre = data.get('nombre')
    apellidos = data.get('apellidos')
    edad = data.get('edad')
    telefono = data.get('telefono')
    email = data.get('email')
    password = data.get('password') or data.get('password_hash')

    if not nombre or not email or not password:
        return jsonify({"msg": "Faltan campos obligatorios", "detail": "Faltan campos obligatorios"}), 400

    existing_user = User.query.filter_by(email=email.strip().lower()).first()
    if existing_user:
        return jsonify({"msg": "El correo ya está registrado", "detail": "El correo ya está registrado"}), 400

    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

    user = User(
        nombre=nombre.strip(),
        apellidos=apellidos.strip() if apellidos else '',
        edad=int(edad) if edad else 18,
        telefono=telefono.strip() if telefono else '',
        email=email.strip().lower(),
        password_hash=hashed_pw
    )
    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        "msg": "Usuario creado exitosamente",
        "access_token": access_token,
        "usuario": {
            "id": user.id,
            "nombre": user.nombre,
            "apellidos": user.apellidos,
            "email": user.email,
            "edad": user.edad
        }
    }), 201


@main.route('/usuarios/', methods=['GET'])
@main.route('/usuarios', methods=['GET'])
def api_get_usuarios():
    users = User.query.all()
    return jsonify({
        "usuarios": [
            {
                "id": u.id,
                "nombre": f"{u.nombre} {u.apellidos}".strip(),
                "edad": u.edad,
                "email": u.email
            } for u in users
        ]
    }), 200

@main.route('/api/usuarios/<int:user_id>', methods=['GET'])
@main.route('/usuarios/<int:user_id>', methods=['GET'])
def api_get_usuario_detail(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404
    return jsonify({
        "usuario": {
            "id": user.id,
            "nombre": user.nombre,
            "apellidos": user.apellidos,
            "nombre_completo": f"{user.nombre} {user.apellidos}".strip(),
            "edad": user.edad,
            "email": user.email,
            "telefono": user.telefono or ""
        }
    }), 200

@main.route('/api/usuarios/<int:user_id>', methods=['PUT'])
@main.route('/usuarios/<int:user_id>', methods=['PUT'])
@jwt_required()
def api_update_usuario(user_id):
    current_user = get_jwt_identity()
    if str(current_user) != str(user_id):
        return jsonify({"msg": "No autorizado"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"msg": "Datos no enviados"}), 400

    if 'nombre' in data and data['nombre'].strip():
        user.nombre = data['nombre'].strip()
    if 'apellidos' in data and data['apellidos'].strip():
        user.apellidos = data['apellidos'].strip()
    if 'edad' in data:
        try:
            user.edad = int(data['edad'])
        except (ValueError, TypeError):
            pass
    if 'telefono' in data:
        user.telefono = str(data['telefono']).strip()
    if 'email' in data and data['email'].strip():
        new_email = data['email'].strip()
        existing = User.query.filter(User.email == new_email, User.id != user_id).first()
        if existing:
            return jsonify({"msg": "Este correo ya está registrado por otra cuenta"}), 409
        user.email = new_email

    if 'password' in data and data['password'].strip():
        user.password_hash = bcrypt.generate_password_hash(data['password'].strip()).decode('utf-8')

    db.session.commit()

    return jsonify({
        "msg": "Perfil actualizado exitosamente",
        "usuario": {
            "id": user.id,
            "nombre": user.nombre,
            "apellidos": user.apellidos,
            "nombre_completo": f"{user.nombre} {user.apellidos}".strip(),
            "edad": user.edad,
            "telefono": user.telefono or "",
            "email": user.email
        }
    }), 200


@main.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"msg": "Faltan credenciales"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"msg": "Credenciales inválidas"}), 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        "access_token": access_token,
        "usuario": {
            "id": user.id,
            "nombre": user.nombre,
            "apellidos": user.apellidos,
            "email": user.email
        }
    }), 200


@main.route('/api/perfil', methods=['GET'])
@jwt_required()
def api_perfil():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404
        
    return jsonify({
        "id": user.id,
        "nombre": user.nombre,
        "apellidos": user.apellidos,
        "email": user.email,
        "edad": user.edad,
        "telefono": user.telefono
    }), 200


# ---------------------------------------------------------
# API GASTOS
# ---------------------------------------------------------

@main.route('/api/gastos/usuario/<int:user_id>', methods=['GET'])
@main.route('/gastos/usuario/<int:user_id>', methods=['GET'])
@jwt_required()
def api_get_gastos(user_id):
    current_user = get_jwt_identity()
    if str(current_user) != str(user_id):
        return jsonify({"msg": "No autorizado"}), 403
        
    gastos = Gasto.query.filter_by(user_id=user_id).order_by(Gasto.fecha.desc()).all()
    total_monto = sum(float(g.monto) for g in gastos) if gastos else 0.0
    return jsonify({
        "gastos": [{
            "id": g.id,
            "descripcion": g.descripcion,
            "monto": g.monto,
            "categoria": g.categoria,
            "categoria_id": 1 if g.categoria == "Hormiga" else (2 if g.categoria == "Fijo" else 3),
            "fecha": g.fecha.isoformat()
        } for g in gastos],
        "monto_total": total_monto,
        "total": len(gastos)
    }), 200

@main.route('/api/gastos', methods=['POST'])
@main.route('/gastos', methods=['POST'])
@jwt_required()
def api_post_gastos():
    data = request.get_json()
    user_id = data.get('usuario_id')
    
    current_user = get_jwt_identity()
    if str(current_user) != str(user_id):
        return jsonify({"msg": "No autorizado"}), 403
        
    cat_id = data.get('categoria_id', 3)
    cat_str = "Hormiga" if cat_id == 1 else ("Fijo" if cat_id == 2 else "Variable")
    
    nuevo = Gasto(
        descripcion=data.get('descripcion'),
        monto=float(data.get('monto')),
        categoria=cat_str,
        user_id=user_id
    )
    db.session.add(nuevo)
    db.session.commit()
    
    return jsonify({"msg": "Gasto agregado", "id": nuevo.id}), 201

@main.route('/api/gastos/<int:gasto_id>', methods=['DELETE'])
@main.route('/gastos/<int:gasto_id>', methods=['DELETE'])
@jwt_required()
def api_delete_gasto(gasto_id):
    gasto = Gasto.query.get(gasto_id)
    if not gasto:
        return jsonify({"msg": "Gasto no encontrado"}), 404
        
    current_user = get_jwt_identity()
    if str(current_user) != str(gasto.user_id):
        return jsonify({"msg": "No autorizado"}), 403
        
    db.session.delete(gasto)
    db.session.commit()
    return jsonify({"msg": "Gasto eliminado"}), 200

@main.route('/api/gastos/<int:gasto_id>', methods=['PUT'])
@main.route('/gastos/<int:gasto_id>', methods=['PUT'])
@jwt_required()
def api_update_gasto(gasto_id):
    gasto = Gasto.query.get(gasto_id)
    if not gasto:
        return jsonify({"msg": "Gasto no encontrado"}), 404
        
    current_user = get_jwt_identity()
    if str(current_user) != str(gasto.user_id):
        return jsonify({"msg": "No autorizado"}), 403
        
    data = request.get_json()
    if 'descripcion' in data:
        gasto.descripcion = data['descripcion']
    if 'monto' in data:
        gasto.monto = float(data['monto'])
    if 'categoria_id' in data:
        cat_id = data['categoria_id']
        gasto.categoria = "Hormiga" if cat_id == 1 else ("Fijo" if cat_id == 2 else "Variable")
    elif 'categoria' in data:
        gasto.categoria = data['categoria']
        
    db.session.commit()
    return jsonify({"msg": "Gasto actualizado"}), 200

@main.route('/api/gastos/categorias', methods=['GET'])
@main.route('/gastos/categorias', methods=['GET'])
def api_get_categorias():
    return jsonify({
        "categorias": [
            {"id": 1, "nombre": "Hormiga"},
            {"id": 2, "nombre": "Fijo"},
            {"id": 3, "nombre": "Variable"}
        ]
    }), 200

# ---------------------------------------------------------
# API IA (MOCK)
# ---------------------------------------------------------

@main.route('/api/ia/clasificar-gasto', methods=['POST'])
@main.route('/ia/clasificar-gasto', methods=['POST'])
def api_ia_clasificar_gasto():
    data = request.get_json()
    if not data:
        return jsonify({"categoria_detectada": "Variable", "confianza": 0.5}), 200
        
    desc = data.get('descripcion', '').lower()
    
    # Mock AI logic
    cat = "Variable"
    if any(word in desc for word in ['uber', 'cafe', 'café', 'starbucks', 'cine', 'snack', 'papas']):
        cat = "Hormiga"
    elif any(word in desc for word in ['renta', 'luz', 'agua', 'internet', 'seguro', 'colegiatura']):
        cat = "Fijo"
        
    return jsonify({
        "categoria_detectada": cat,
        "confianza": 0.85
    }), 200

@main.route('/api/chat', methods=['POST'])
@main.route('/chat', methods=['POST'])
@jwt_required()
def api_chat():
    data = request.get_json()
    pregunta = data.get('mensaje', '').lower()
    
    respuesta = "Soy el asistente virtual de Widata. (Esta es una versión mock). ¿En qué más puedo ayudarte con tus finanzas?"
    
    if 'ahorrar' in pregunta:
        respuesta = "Para ahorrar, te recomiendo analizar tus gastos hormiga. Suelen representar hasta el 15% de los ingresos."
    elif 'score' in pregunta or 'buro' in pregunta:
        respuesta = "Tu score crediticio depende en gran medida de tu índice de utilización. ¡Mantenlo debajo del 30%!"
    elif 'hola' in pregunta:
        respuesta = "¡Hola! Bienvenido a la IA de Widata. ¿En qué te ayudo hoy?"
    
    return jsonify({
        "respuesta": respuesta
    }), 200

# ---------------------------------------------------------
# API CREDITOS
# ---------------------------------------------------------
@main.route('/api/creditos/usuario/<int:user_id>', methods=['GET'])
@main.route('/creditos/usuario/<int:user_id>', methods=['GET'])
@jwt_required()
def api_get_creditos(user_id):
    current_user = get_jwt_identity()
    if str(current_user) != str(user_id):
        return jsonify({"msg": "No autorizado"}), 403
        
    deudas = Deuda.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        "creditos": [{
            "id": d.id,
            "deuda_actual": d.monto,
            "limite_credito": d.limite,
            "tasa_anual": d.tasa,
            "pago_minimo": d.minimo,
            "institucion_id": d.banco_id
        } for d in deudas],
        "total": len(deudas)
    }), 200

@main.route('/api/creditos', methods=['POST'])
@main.route('/creditos', methods=['POST'])
@jwt_required()
def api_post_creditos():
    data = request.get_json() or {}
    user_id = data.get('usuario_id')
    
    current_user = get_jwt_identity()
    if user_id is None:
        user_id = current_user
    elif str(current_user) != str(user_id):
        return jsonify({"msg": "No autorizado"}), 403
        
    try:
        banco_id = int(data.get('institucion_id', 1))
        # Asegurar que la institución bancaria existe en la BD
        banco = Banco.query.get(banco_id)
        if not banco:
            banco = Banco.query.first()
            if not banco:
                banco = Banco(
                    id=1,
                    nombre="BBVA México",
                    pais_origen="México",
                    emite_tarjeta_credito=True,
                    otorga_prestamos=True,
                    tipo_institucion="Banco"
                )
                db.session.add(banco)
                db.session.commit()
            banco_id = banco.id

        nuevo = Deuda(
            monto=float(data.get('deuda_actual', 0)),
            limite=float(data.get('limite_credito', 0)),
            tasa=float(data.get('tasa_anual', 15.0)),
            minimo=float(data.get('pago_minimo', 0)),
            banco_id=banco_id,
            user_id=int(user_id)
        )
        db.session.add(nuevo)
        db.session.commit()
        return jsonify({"msg": "Crédito agregado exitosamente", "id": nuevo.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error al guardar crédito: {str(e)}"}), 500

@main.route('/api/creditos/<int:credito_id>', methods=['DELETE'])
@main.route('/creditos/<int:credito_id>', methods=['DELETE'])
@jwt_required()
def api_delete_credito(credito_id):
    deuda = Deuda.query.get(credito_id)
    if not deuda:
        return jsonify({"msg": "Crédito no encontrado"}), 404
        
    current_user = get_jwt_identity()
    if str(current_user) != str(deuda.user_id):
        return jsonify({"msg": "No autorizado"}), 403
        
    db.session.delete(deuda)
    db.session.commit()
    return jsonify({"msg": "Crédito eliminado"}), 200

@main.route('/api/creditos/<int:credito_id>', methods=['PUT'])
@main.route('/creditos/<int:credito_id>', methods=['PUT'])
@jwt_required()
def api_update_credito(credito_id):
    deuda = Deuda.query.get(credito_id)
    if not deuda:
        return jsonify({"msg": "Crédito no encontrado"}), 404
        
    current_user = get_jwt_identity()
    if str(current_user) != str(deuda.user_id):
        return jsonify({"msg": "No autorizado"}), 403
        
    data = request.get_json()
    if 'deuda_actual' in data:
        deuda.monto = float(data['deuda_actual'])
    if 'limite_credito' in data:
        deuda.limite = float(data['limite_credito'])
    if 'tasa_anual' in data:
        deuda.tasa = float(data['tasa_anual'])
    if 'pago_minimo' in data:
        deuda.minimo = float(data['pago_minimo'])
    if 'institucion_id' in data:
        deuda.banco_id = int(data['institucion_id'])
        
    db.session.commit()
    return jsonify({"msg": "Crédito actualizado"}), 200

@main.route('/api/instituciones', methods=['GET'])
@main.route('/instituciones', methods=['GET'])
def api_get_instituciones():
    bancos = Banco.query.all()
    if not bancos:
        bancos = [
            Banco(id=1, nombre='BBVA México', pais_origen='México', emite_tarjeta_credito=True, otorga_prestamos=True, tipo_institucion='Banco'),
            Banco(id=2, nombre='Nu México', pais_origen='México', emite_tarjeta_credito=True, otorga_prestamos=True, tipo_institucion='Sofipo'),
            Banco(id=3, nombre='Santander', pais_origen='México', emite_tarjeta_credito=True, otorga_prestamos=True, tipo_institucion='Banco'),
            Banco(id=4, nombre='Citibanamex', pais_origen='México', emite_tarjeta_credito=True, otorga_prestamos=True, tipo_institucion='Banco'),
            Banco(id=5, nombre='Banorte', pais_origen='México', emite_tarjeta_credito=True, otorga_prestamos=True, tipo_institucion='Banco'),
            Banco(id=6, nombre='Mercado Pago', pais_origen='México', emite_tarjeta_credito=True, otorga_prestamos=True, tipo_institucion='Fintech'),
            Banco(id=7, nombre='Hey Banco', pais_origen='México', emite_tarjeta_credito=True, otorga_prestamos=True, tipo_institucion='Banco Digital')
        ]
        try:
            db.session.add_all(bancos)
            db.session.commit()
            bancos = Banco.query.all()
        except Exception:
            db.session.rollback()
    return jsonify({
        "instituciones": [{
            "id": b.id,
            "nombre": b.nombre
        } for b in bancos]
    }), 200



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