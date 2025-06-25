
#from bs4 import Beautifulpip Soup
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for # ¡Añadir flash, redirect, url_for!
import sympy as sp
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats as scipy_stats
import io # Necesario para la gráfica
import base64 # Necesario para la gráfica
import re
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime # <--- ¡Añadir esto!
from sqlalchemy.sql import func # <--- Para la fecha/hora por defecto
import os

from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField # ¡Añadir BooleanField!
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required



# Importa funciones y clases de sympy necesarias
from sympy import sin, cos, tan, exp, log, sqrt, symbols, pi, E, Add, Mul, Pow, Function, Integer, Rational, Float
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application

# --- Configuración ---
TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')
# Crear la carpeta 'instance' si no existe
os.makedirs(instance_path, exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_path, "project.db")}'
# Desactivar una característica de seguimiento de SQLAlchemy que no necesitamos y consume recursos
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# ¡Importante! Necesitamos una clave secreta para manejar sesiones más adelante (aunque aún no las usemos)
app.config['SECRET_KEY'] = 'tu-clave-secreta-muy-dificil-de-adivinar' # ¡Cambia esto por algo seguro!

# --- ¡NUEVO! Inicializar la extensión SQLAlchemy ---
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # A dónde redirigir si se intenta acceder a una página protegida sin login
login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.' # Mensaje flash
login_manager.login_message_category = 'info' # Categoría para el mensaje flash

ALLOWED_SYMBOLS = {
    'x': symbols('x'),
    'sin': sin, 'cos': cos, 'tan': tan,
    'exp': exp, 'ln': log, 'log': log,
    'sqrt': sqrt, 'pi': pi,'e': E
}
NUMPY_MODULES = [{'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
                  'exp': np.exp, 'log': np.log, 'sqrt': np.sqrt},
                 "numpy", {'builtins': None}]

# --- Función auxiliar para formatear pasos ---
def format_step(description, before_expr=None, after_expr=None):
    """Crea un string HTML para un paso, incluyendo opcionalmente expresiones LaTeX."""
    step_html = f"<p><strong>{description}</strong></p>"

    # Formatear expresión ANTES (si existe)
    if before_expr is not None:
        if hasattr(before_expr, '_sympy_'):
            try:
                latex_before = sp.latex(before_expr)
                step_html += f"<p>\\[ \\frac{{d}}{{dx}} \\left[ {latex_before} \\right] \\]</p>"
            except Exception as e_latex_before:
                print(f"ERROR format_step: generando LaTeX para before_expr: {e_latex_before}")
                step_html += f"<p>Operando sobre: [Error LaTeX] {str(before_expr)}</p>"
        else:
             step_html += f"<p>Operando sobre: {before_expr}</p>"

    # Formatear expresión DESPUÉS (si existe)
    if after_expr is not None:
        if hasattr(after_expr, '_sympy_'):
            try:
                latex_after = sp.latex(after_expr)
                step_html += f"<p>Resultado intermedio: \\[{latex_after}\\]</p>"
            except Exception as e_latex_after:
                print(f"ERROR format_step: generando LaTeX para after_expr: {e_latex_after}")
                step_html += f"<p>Resultado intermedio: [Error LaTeX] {str(after_expr)}</p>"
        else:
             step_html += f"<p>Resultado intermedio: {after_expr}</p>"

    return step_html

# --- Derivación Recursiva con Pasos ---
def derivar_con_pasos(expr, var):
    """
    Calcula la derivada de expr con respecto a var, devolviendo
    la expresión derivada y una lista de pasos en HTML.
    """
    pasos = []

    # Casos Base
    if expr.is_number:
        descripcion = f"La derivada de la constante \\({sp.latex(expr)}\\) es 0."
        pasos.append(f"<p>{descripcion}</p>")
        return Integer(0), pasos
    if isinstance(expr, sp.Symbol) and expr == var:
        descripcion = f"La derivada de \\({sp.latex(expr)}\\) con respecto a sí misma es 1."
        pasos.append(f"<p>{descripcion}</p>")
        return Integer(1), pasos
    if isinstance(expr, sp.Symbol) and expr != var:
        descripcion = f"La derivada del símbolo \\({sp.latex(expr)}\\) (considerado constante respecto a \\({sp.latex(var)}\\)) es 0."
        pasos.append(f"<p>{descripcion}</p>")
        return Integer(0), pasos

    # Regla del Cociente
    numerador, denominador = expr.as_numer_denom()
    if denominador != 1 and denominador.has(var):
        u = numerador
        v = denominador
        pasos.append(format_step(
            f"Aplicando la regla del cociente a \\(\\frac{{{sp.latex(u)}}}{{{sp.latex(v)}}}\\): \\(\\frac{{d}}{{dx}} [\\frac{{u}}{{v}}] = \\frac{{(\\frac{{d}}{{dx}}u) \\cdot v - u \\cdot (\\frac{{d}}{{dx}}v)}}{{v^2}}\\)",
            before_expr=None
        ))
        pasos.append(f"<p>Donde \\(u = {sp.latex(u)}\\) (numerador) y \\(v = {sp.latex(v)}\\) (denominador).</p>")

        pasos.append(f"<p>1. Calculando \\(\\frac{{d}}{{dx}}u = \\frac{{d}}{{dx}}({sp.latex(u)})\\):</p>")
        deriv_u, pasos_u = derivar_con_pasos(u, var)
        pasos.extend([f"<div style='margin-left: 20px;'>{p}</div>" for p in pasos_u])
        pasos.append(format_step(f"Resultado \\(\\frac{{d}}{{dx}}u\\):", after_expr=deriv_u))
        u_prime = deriv_u

        pasos.append(f"<p>2. Calculando \\(\\frac{{d}}{{dx}}v = \\frac{{d}}{{dx}}({sp.latex(v)})\\):</p>")
        deriv_v, pasos_v = derivar_con_pasos(v, var)
        pasos.extend([f"<div style='margin-left: 20px;'>{p}</div>" for p in pasos_v])
        pasos.append(format_step(f"Resultado \\(\\frac{{d}}{{dx}}v\\):", after_expr=deriv_v))
        v_prime = deriv_v

        pasos.append(f"<p>3. Construyendo el numerador de la derivada \\((\\frac{{d}}{{dx}}u) \\cdot v - u \\cdot (\\frac{{d}}{{dx}}v)\\):</p>")
        term_num1 = Mul(u_prime, v)
        term_num2 = Mul(u, v_prime)
        pasos.append(f"<p>Término \\((\\frac{{d}}{{dx}}u) \\cdot v\\): \\[{sp.latex(term_num1)}\\]</p>")
        pasos.append(f"<p>Término \\(u \\cdot (\\frac{{d}}{{dx}}v)\\): \\[{sp.latex(term_num2)}\\]</p>")
        numerador_deriv = Add(term_num1, Mul(Integer(-1), term_num2))
        pasos.append(format_step(f"Resultado del numerador \\(u'v - uv'\\):", after_expr=numerador_deriv))

        pasos.append(f"<p>4. Calculando el denominador de la derivada \\(v^2\\):</p>")
        denominador_deriv = Pow(v, Integer(2))
        pasos.append(format_step(f"Resultado del denominador \\(v^2\\):", after_expr=denominador_deriv))

        pasos.append(f"<p>5. Combinando numerador y denominador \\(\\frac{{u'v - uv'}}{{v^2}}\\):</p>")
        derivada_final = numerador_deriv / denominador_deriv
        pasos.append(format_step("Resultado de la regla del cociente:", after_expr=derivada_final))
        return derivada_final, pasos

    # Regla de la Suma
    if isinstance(expr, Add):
        pasos.append(format_step(f"Aplicando la regla de la suma a \\({sp.latex(expr)}\\): \\(\\frac{{d}}{{dx}} [f+g] = \\frac{{d}}{{dx}}f + \\frac{{d}}{{dx}}g\\)", before_expr=None))
        derivadas_args = []
        pasos_args = []
        for arg in expr.args:
            pasos.append(f"<p>Derivando término: \\({sp.latex(arg)}\\)</p>")
            deriv_arg, pasos_arg = derivar_con_pasos(arg, var)
            derivadas_args.append(deriv_arg)
            pasos_args.extend([f"<div style='margin-left: 20px;'>{p}</div>" for p in pasos_arg])
        derivada_final = Add(*derivadas_args)
        pasos.extend(pasos_args)
        pasos.append(format_step(f"Combinando las derivadas de los términos:", after_expr=derivada_final))
        return derivada_final, pasos

    # Regla del Producto
    if isinstance(expr, Mul):
        args = expr.args
        constantes = [arg for arg in args if arg.is_number]
        funciones = [arg for arg in args if not arg.is_number]

        # Caso: Constante por Función (c*f)
        if len(funciones) == 1:
            constante_total = Mul(*constantes) if constantes else Integer(1)
            funcion_unica = funciones[0]
            pasos.append(format_step(f"Aplicando regla de constante por función a \\({sp.latex(expr)}\\): \\(\\frac{{d}}{{dx}} [c \\cdot f] = c \\cdot \\frac{{d}}{{dx}}f\\)", before_expr=None))
            pasos.append(f"<p>Derivando la parte funcional: \\({sp.latex(funcion_unica)}\\)</p>")
            deriv_func, pasos_func = derivar_con_pasos(funcion_unica, var)
            pasos.extend([f"<div style='margin-left: 20px;'>{p}</div>" for p in pasos_func])
            derivada_final = constante_total * deriv_func
            pasos.append(format_step(f"Multiplicando por la constante \\({sp.latex(constante_total)}\\):", after_expr=derivada_final))
            return derivada_final, pasos

        # Caso: Regla del Producto General (u*v)
        elif len(funciones) >= 2:
            u = funciones[0]
            v = Mul(*funciones[1:])
            constante_global = Mul(*constantes) if constantes else Integer(1)
            expr_funcional = u * v

            pasos.append(format_step(f"Aplicando la regla del producto a \\({sp.latex(expr_funcional)}\\): \\(\\frac{{d}}{{dx}} [u \\cdot v] = (\\frac{{d}}{{dx}}u) \\cdot v + u \\cdot (\\frac{{d}}{{dx}}v)\\)", before_expr=None))
            pasos.append(f"<p>Donde \\(u = {sp.latex(u)}\\) y \\(v = {sp.latex(v)}\\).</p>")

            pasos.append(f"<p>1. Calculando \\(\\frac{{d}}{{dx}}u = \\frac{{d}}{{dx}}({sp.latex(u)})\\):</p>")
            deriv_u, pasos_u = derivar_con_pasos(u, var)
            pasos.extend([f"<div style='margin-left: 20px;'>{p}</div>" for p in pasos_u])
            pasos.append(format_step(f"Resultado \\(\\frac{{d}}{{dx}}u\\):", after_expr=deriv_u))
            u_prime = deriv_u

            pasos.append(f"<p>2. Calculando \\(\\frac{{d}}{{dx}}v = \\frac{{d}}{{dx}}({sp.latex(v)})\\):</p>")
            deriv_v, pasos_v = derivar_con_pasos(v, var)
            pasos.extend([f"<div style='margin-left: 20px;'>{p}</div>" for p in pasos_v])
            pasos.append(format_step(f"Resultado \\(\\frac{{d}}{{dx}}v\\):", after_expr=deriv_v))
            v_prime = deriv_v

            pasos.append(f"<p>3. Aplicando la fórmula \\((\\frac{{d}}{{dx}}u) \\cdot v + u \\cdot (\\frac{{d}}{{dx}}v)\\):</p>")
            termino1 = Mul(u_prime, v)
            termino2 = Mul(u, v_prime)

            pasos.append(f"<p>Término \\((\\frac{{d}}{{dx}}u) \\cdot v\\): \\[{sp.latex(termino1)}\\]</p>")
            pasos.append(f"<p>Término \\(u \\cdot (\\frac{{d}}{{dx}}v)\\): \\[{sp.latex(termino2)}\\]</p>")

            derivada_parcial = Add(termino1, termino2)
            pasos.append(format_step(f"Sumando los términos:", after_expr=derivada_parcial))

            if constante_global != 1:
                 derivada_final = constante_global * derivada_parcial
                 pasos.append(format_step(f"Multiplicando por la constante global \\({sp.latex(constante_global)}\\):", after_expr=derivada_final))
            else:
                 derivada_final = derivada_parcial
            return derivada_final, pasos

        else: # Solo constantes
             print(f"WARN: Caso Mul inesperado (solo constantes?): {expr}")
             return Integer(0), [format_step("La expresión es un producto de constantes, la derivada es 0.")]

    # Regla de la Potencia
    if isinstance(expr, Pow):
        base, exponente = expr.args

        # Exponente Cero
        if exponente.is_zero:
             descripcion = f"La expresión \\({sp.latex(base)}\\) está elevada a 0, lo cual es 1. La derivada de la constante 1 es 0."
             pasos.append(f"<p>{descripcion}</p>")
             return Integer(0), pasos

        # Exponente Constante Numérica
        if exponente.is_number:
            n = exponente
            f = base
            # Base es la variable (x^n)
            if isinstance(f, sp.Symbol) and f == var:
                pasos.append(format_step(f"Aplicando la regla de la potencia simple a \\({sp.latex(expr)}\\): \\(\\frac{{d}}{{dx}} [x^n] = n \\cdot x^{{n-1}}\\)", before_expr=None))
                derivada_final = n * var**(n - 1)
                pasos.append(format_step(f"Resultado:", after_expr=derivada_final))
                return derivada_final, pasos
            # Base es función (f(x)^n)
            else:
                pasos.append(format_step(f"Aplicando la regla de la cadena (potencia) a \\({sp.latex(expr)}\\): \\(\\frac{{d}}{{dx}} [f^n] = n \\cdot f^{{n-1}} \\cdot \\frac{{d}}{{dx}}f\\)", before_expr=None))
                pasos.append(f"<p>Donde \\(f = {sp.latex(f)}\\) y \\(n = {sp.latex(n)}\\)</p>")
                pasos.append(f"<p>Calculando la derivada de la base \\(\\frac{{d}}{{dx}}f = \\frac{{d}}{{dx}}({sp.latex(f)})\\):</p>")
                deriv_f, pasos_f = derivar_con_pasos(f, var)
                pasos.extend([f"<div style='margin-left: 20px;'>{p}</div>" for p in pasos_f])
                pasos.append(format_step(f"Resultado \\(\\frac{{d}}{{dx}}f\\):", after_expr=deriv_f))
                termino_potencia = n * f**(n - 1)
                derivada_final = termino_potencia * deriv_f
                pasos.append(format_step(f"Aplicando la fórmula \\(n \\cdot f^{{n-1}} \\cdot \\frac{{d}}{{dx}}f\\):", after_expr=derivada_final))
                return derivada_final, pasos

        # Base Constante, Exponente Función (a^g(x))
        elif base.is_number and not exponente.is_number:
             a = base
             g = exponente
             pasos.append(format_step(f"Aplicando la regla de la cadena (exponencial) a \\({sp.latex(expr)}\\): \\(\\frac{{d}}{{dx}} [a^g] = a^g \\cdot \\ln(a) \\cdot \\frac{{d}}{{dx}}g\\)", before_expr=None))
             pasos.append(f"<p>Donde \\(a = {sp.latex(a)}\\) y \\(g = {sp.latex(g)}\\)</p>")
             pasos.append(f"<p>Calculando la derivada del exponente \\(\\frac{{d}}{{dx}}g = \\frac{{d}}{{dx}}({sp.latex(g)})\\):</p>")
             deriv_g, pasos_g = derivar_con_pasos(g, var)
             pasos.extend([f"<div style='margin-left: 20px;'>{p}</div>" for p in pasos_g])
             pasos.append(format_step(f"Resultado \\(\\frac{{d}}{{dx}}g\\):", after_expr=deriv_g))
             derivada_final = expr * sp.log(a) * deriv_g # expr es a^g
             pasos.append(format_step(f"Aplicando la fórmula \\(a^g \\cdot \\ln(a) \\cdot \\frac{{d}}{{dx}}g\\):", after_expr=derivada_final))
             return derivada_final, pasos

        # Base y Exponente Funciones (f(x)^g(x)) - Fallback
        else:
             pasos.append(format_step(f"Caso potencia \\(f(x)^{{g(x)}}\\) detectado (requiere derivación logarítmica). Calculando directamente:", before_expr=expr))
             derivada_fallback = sp.diff(expr, var)
             pasos.append(format_step("Resultado (calculado directamente):", after_expr=derivada_fallback))
             return derivada_fallback, pasos

    # Regla de la Cadena (Funciones)
    if isinstance(expr, Function):
        func_type = type(expr)
        if len(expr.args) == 1:
            g = expr.args[0]
            try:
                 func_con_var = func_type(var)
                 f_prime_func_form = sp.diff(func_con_var, var)
                 f_prime_g = sp.Subs(f_prime_func_form, var, g).doit()
            except Exception as e_fprime:
                 print(f"WARN: No se pudo calcular f' para {func_type}. Usando fallback. Error: {e_fprime}")
                 derivada_fallback = sp.diff(expr, var)
                 pasos.append(format_step(f"Error al procesar f' para {func_type}. Calculando directamente:", before_expr=expr, after_expr=derivada_fallback))
                 return derivada_fallback, pasos

            pasos.append(format_step(f"Aplicando la regla de la cadena a \\({sp.latex(expr)}\\): \\(\\frac{{d}}{{dx}} [f(g)] = f'(g) \\cdot \\frac{{d}}{{dx}}g\\)", before_expr=None))
            pasos.append(f"<p>Donde la derivada de la función externa \\(f'\\) evaluada en \\(g={sp.latex(g)}\\) es \\(f'(g) = {sp.latex(f_prime_g)}\\).</p>")
            pasos.append(f"<p>Calculando la derivada del argumento interno \\(\\frac{{d}}{{dx}}g = \\frac{{d}}{{dx}}({sp.latex(g)})\\):</p>")
            deriv_g, pasos_g = derivar_con_pasos(g, var)
            pasos.extend([f"<div style='margin-left: 20px;'>{p}</div>" for p in pasos_g])
            pasos.append(format_step(f"Resultado \\(\\frac{{d}}{{dx}}g\\):", after_expr=deriv_g))
            derivada_final = f_prime_g * deriv_g
            pasos.append(format_step(f"Aplicando la fórmula \\(f'(g) \\cdot \\frac{{d}}{{dx}}g\\):", after_expr=derivada_final))
            return derivada_final, pasos
        else: # Fallback para funciones con múltiples argumentos
            pasos.append(format_step(f"Función con {len(expr.args)} argumentos detectada. Calculando directamente:", before_expr=expr))
            derivada_fallback = sp.diff(expr, var)
            pasos.append(format_step("Resultado (calculado directamente):", after_expr=derivada_fallback))
            return derivada_fallback, pasos

    # Fallback General
    pasos.append(format_step(f"No se aplicó una regla específica o es un caso base complejo. Calculando directamente:", before_expr=expr))
    print(f"WARN: Usando sp.diff como fallback para tipo: {type(expr)}, expr: {expr}")
    derivada_fallback = sp.diff(expr, var)
    pasos.append(format_step("Resultado (calculado directamente):", after_expr=derivada_fallback))
    return derivada_fallback, pasos

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    history_entries = db.relationship('CalculationHistory', backref='user', lazy=True, cascade="all, delete-orphan")


    def __repr__(self):
        return f'<User {self.username}>'
class CalculationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expression = db.Column(db.String(500), nullable=False) # Expresión original
    derivative = db.Column(db.String(500), nullable=False) # Derivada resultante (como string)
    timestamp = db.Column(DateTime(timezone=True), server_default=func.now()) # Fecha y hora
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Clave foránea al usuario

    def __repr__(self):
        return f'<History {self.id} Expr: {self.expression[:20]}>'
# --- ¡NUEVO! Formulario de Registro ---
class RegistrationForm(FlaskForm):
    username = StringField('Usuario',
                           validators=[DataRequired(message="El usuario es obligatorio."),
                                       Length(min=4, max=25, message="El usuario debe tener entre 4 y 25 caracteres.")])
    password = PasswordField('Contraseña',
                             validators=[DataRequired(message="La contraseña es obligatoria."),
                                         Length(min=6, message="La contraseña debe tener al menos 6 caracteres.")])
    confirm_password = PasswordField('Confirmar Contraseña',
                                     validators=[DataRequired(message="Confirma la contraseña."),
                                                 EqualTo('password', message="Las contraseñas deben coincidir.")])
    submit = SubmitField('Registrarse')

    # Validación personalizada para asegurar que el usuario no exista ya
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Ese nombre de usuario ya está en uso. Por favor, elige otro.')
@login_manager.user_loader
def load_user(user_id):
    # Flask-Login guarda el ID del usuario en la sesión,
    # esta función usa ese ID para obtener el objeto User de la BD
    return User.query.get(int(user_id))

# --- Formularios (RegistrationForm sin cambios) ---
class RegistrationForm(FlaskForm):
    username = StringField('Usuario',
                           validators=[DataRequired(message="El usuario es obligatorio."),
                                       Length(min=4, max=25, message="El usuario debe tener entre 4 y 25 caracteres.")])
    password = PasswordField('Contraseña',
                             validators=[DataRequired(message="La contraseña es obligatoria."),
                                         Length(min=6, message="La contraseña debe tener al menos 6 caracteres.")])
    confirm_password = PasswordField('Confirmar Contraseña',
                                     validators=[DataRequired(message="Confirma la contraseña."),
                                                 EqualTo('password', message="Las contraseñas deben coincidir.")])
    submit = SubmitField('Registrarse')

    # Validación personalizada para asegurar que el usuario no exista ya
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Ese nombre de usuario ya está en uso. Por favor, elige otro.')
    # ... (tu RegistrationForm como estaba) ...

# --- ¡NUEVO! Formulario de Login ---
class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(message="Ingresa tu usuario.")])
    password = PasswordField('Contraseña', validators=[DataRequired(message="Ingresa tu contraseña.")])
    remember = BooleanField('Recuérdame') # Checkbox "Recordarme"
    submit = SubmitField('Iniciar Sesión')   

# --- Ruta principal ---
@app.route('/')
@login_required # Solo usuarios logueados pueden acceder a la calculadora
def inicio():
    return render_template('calculadora.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit(): # Se ejecuta solo si es POST y pasa las validaciones
        # Verificar si el usuario ya existe (doble chequeo, aunque el validador del form ya lo hace)
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Ese nombre de usuario ya existe. Por favor, elige otro.', 'danger')
            return redirect(url_for('register')) # Redirigir de nuevo a registro

        # Hashear la contraseña
        hashed_password = generate_password_hash(form.password.data)
        # Crear nuevo usuario
        new_user = User(username=form.username.data, password_hash=hashed_password)
        # Añadir a la base de datos
        db.session.add(new_user)
        db.session.commit()
        # Mensaje de éxito y redirigir a login (¡crearemos esta ruta después!)
        flash(f'¡Cuenta creada para {form.username.data}! Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login')) # Asumimos que tendremos una ruta 'login'
    # Si es GET o la validación falla, mostrar el formulario
    return render_template('register.html', title='Registro', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: # Si ya está logueado, redirigir a inicio
        return redirect(url_for('inicio'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        # Verificar si el usuario existe y la contraseña es correcta
        if user and check_password_hash(user.password_hash, form.password.data):
            # Usuario válido, iniciar sesión
            login_user(user, remember=form.remember.data)
            # Redirigir a la página siguiente (si existe) o a inicio
            next_page = request.args.get('next')
            flash('¡Inicio de sesión exitoso!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('inicio'))
        else:
            # Usuario inválido o contraseña incorrecta
            flash('Inicio de sesión fallido. Verifica usuario y contraseña.', 'danger')
    return render_template('login.html', title='Iniciar Sesión', form=form)
@app.route('/logout')
def logout():
    logout_user() # Cierra la sesión del usuario
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('login')) # Redirigir a la página de login


# --- Ruta para calcular la derivada ---
@app.route('/derivar', methods=['POST'])
@login_required
def derivar():
    data = request.get_json()
    expresion_str = data.get('expresion')

    if not expresion_str:
        return jsonify({'error': 'La expresión no puede estar vacía.'}), 400

    x = ALLOWED_SYMBOLS['x']

    # Preprocesamiento
    processed_expr = ""
    try:
        processed_expr_step1 = expresion_str.replace('^', '**')
        try:
            temp_parsed = parse_expr(processed_expr_step1, transformations=TRANSFORMATIONS, local_dict={'x': x})
            processed_expr = str(temp_parsed)
        except Exception:
            try:
                processed_expr = re.sub(r'(?<=[0-9])(?=[x])(?<![a-zA-Z0-9\.\*\/])', r'*', processed_expr_step1)
            except Exception:
                processed_expr = processed_expr_step1
    except Exception as general_preproc_error:
         print(f"FATAL: Error general en preprocesamiento: {general_preproc_error}")
         processed_expr = expresion_str # Usar original como último recurso

    print(f"--- Calculando Derivada con Pasos ---")
    print(f"Input Original: {expresion_str}")
    print(f"Expresión Procesada FINAL para Sympify: {processed_expr}")

    try:
        # Parseo
        funcion = sp.sympify(processed_expr, locals=ALLOWED_SYMBOLS)
        print(f"Expresión Parseada por SymPy: {funcion}")

        # Validación de Variables
        free_vars = funcion.free_symbols
        allowed_vars = {x}
        unexpected_vars = free_vars - allowed_vars
        if unexpected_vars:
              raise ValueError(f"La expresión solo debe contener 'x'. Se encontraron: {unexpected_vars}")

        # Llamada a la función de derivación por pasos
        derivada_obj, pasos_lista = derivar_con_pasos(funcion, x)
        print(f"Derivada Calculada por Pasos (Objeto): {repr(derivada_obj)}")

        # Simplificación (cancelar fracciones)
        try:
            derivada_simplificada = sp.cancel(derivada_obj)
            if derivada_simplificada != derivada_obj:
                pasos_lista.append(format_step("Simplificando el resultado final (cancelando):", after_expr=derivada_simplificada))
                derivada_final = derivada_simplificada
            else:
                derivada_final = derivada_obj
        except Exception as e_simpl:
            print(f"WARN: Error durante simplificación final ({e_simpl}). Usando resultado sin simplificar.")
            derivada_final = derivada_obj

        print(f"Derivada Procesada y Simplificada Final: {derivada_final}")

        # Generación de LaTeX y Pasos HTML
        latex_funcion = sp.latex(funcion)
        latex_derivada_final = sp.latex(derivada_final)
        derivada_final_str = str(derivada_final)

        pasos_html = f"<p><strong>Función Original:</strong></p>\\[ f(x) = {latex_funcion} \\]"
        pasos_html += "".join(pasos_lista)
        pasos_html += f"<hr><p><strong>Resultado Final Simplificado:</strong></p>\\[ f'(x) = {latex_derivada_final} \\]"

        if current_user.is_authenticated:
            try:
                hist_entry = CalculationHistory(
                    expression=expresion_str, # O usa 'processed_expr' si prefieres
                    derivative=derivada_final_str,
                    user_id=current_user.id
                )
                db.session.add(hist_entry)
                db.session.commit()
                print(f"Historial guardado para usuario {current_user.id}")
            except Exception as e_hist:
                db.session.rollback() # Deshacer si hay error al guardar
                print(f"!!! Error al guardar historial en BD: {e_hist}")
        # --- Fin de Guardar en Historial ---

        # Respuesta JSON (sin datos de PDF)
        return jsonify({
            'resultado': latex_derivada_final,
            'pasos': pasos_html,
            'derivada_str': str(derivada_final) # Para la gráfica
        })

    except (SyntaxError, TypeError, ValueError, AttributeError, Exception) as e:
         print(f"!!! Error procesando '{processed_expr}': {type(e).__name__} - {e}")
         import traceback
         traceback.print_exc()
         error_msg = f"Error al procesar: {e}"
         return jsonify({'error': error_msg}), 400
    
@app.route('/get_history')
@login_required
def get_history():
    try:
        # Obtener las últimas N entradas del usuario actual, ordenadas por fecha descendente
        history_limit = 15 # Puedes ajustar cuántas mostrar
        user_history = CalculationHistory.query.filter_by(user_id=current_user.id)\
                                               .order_by(CalculationHistory.timestamp.desc())\
                                               .limit(history_limit).all()

        # Convertir las entradas a un formato JSON simple
        history_data = [
            {
                'expression': entry.expression,
                'derivative': entry.derivative,
                'timestamp': entry.timestamp.isoformat() # Formato estándar ISO 8601
            }
            for entry in user_history
        ]
        return jsonify(history_data)
    except Exception as e:
        print(f"!!! Error en /get_history para usuario {current_user.id}: {e}")
        # Devuelve un error genérico en formato JSON
        return jsonify({'error': 'No se pudo obtener el historial'}), 500
    
    
@app.route('/clear_history', methods=['POST'])
@login_required # Solo usuarios logueados pueden borrar su historial
def clear_history():
    """
    Elimina todas las entradas del historial para el usuario actual.
    """
    try:
        # Filtrar por el ID del usuario actual y eliminar esas entradas
        num_deleted = CalculationHistory.query.filter_by(user_id=current_user.id).delete()
        # Confirmar los cambios en la base de datos
        db.session.commit()
        print(f"Historial limpiado para usuario {current_user.id}. Entradas eliminadas: {num_deleted}")
        # Devolver una respuesta de éxito en formato JSON
        return jsonify({'message': f'Historial limpiado exitosamente. {num_deleted} entradas eliminadas.'}), 200
    except Exception as e:
        # Si ocurre un error, deshacer cambios y registrar el error
        db.session.rollback()
        print(f"!!! Error al limpiar historial para usuario {current_user.id}: {e}")
        # Devolver una respuesta de error en formato JSON
        return jsonify({'error': 'Ocurrió un error al intentar limpiar el historial.'}), 500

# <<<--- FIN DEL CÓDIGO PEGADO --- >>>

    
    
    except Exception as e:
        print(f"!!! Error en /get_history: {e}")
        return jsonify({'error': 'No se pudo obtener el historial'}), 500
# --- Ruta /graficar ---
@app.route('/graficar', methods=['POST'])
@login_required
def graficar():
    data = request.get_json()
    expresion_derivada_str = data.get('expresion')
    if not expresion_derivada_str: return jsonify({'error': 'No se proporcionó expresión para graficar.'}), 400
    print(f"--- Generando Gráfica ---")
    print(f"Expresión recibida: {expresion_derivada_str}")
    x = ALLOWED_SYMBOLS['x']
    try:
        derivada_expr = sp.sympify(expresion_derivada_str, locals=ALLOWED_SYMBOLS)
        print(f"Expresión de derivada parseada: {repr(derivada_expr)}")
        f_numeric = sp.lambdify(x, derivada_expr, modules=NUMPY_MODULES)
        print(f"Función lambdify creada: {f_numeric}")
        x_vals = np.linspace(-10, 10, 400)
        y_vals = np.empty_like(x_vals)
        numeric_errors_count = 0
        for i, val in enumerate(x_vals):
            try:
                y_calc = f_numeric(val)
                if isinstance(y_calc, complex): y_vals[i] = y_calc.real
                else: y_vals[i] = y_calc
            except Exception:
                 numeric_errors_count += 1
                 y_vals[i] = np.nan
        if numeric_errors_count > 0: print(f"Advertencia: {numeric_errors_count} errores numéricos al evaluar.")
        y_vals[np.isinf(y_vals)] = np.nan
        finite_mask = np.isfinite(y_vals)
        x_finite = x_vals[finite_mask]
        y_finite = y_vals[finite_mask]
        print(f"Puntos finitos para graficar: {len(y_finite)}")
        fig, ax = plt.subplots(figsize=(6, 4))
        if len(y_finite) > 1:
            y_median = np.median(y_finite)
            mad = scipy_stats.median_abs_deviation(y_finite, scale='normal') if len(y_finite) > 1 else 0
            if mad < 1e-6: mad = 1.0
            y_min_limit = y_median - 5 * mad
            y_max_limit = y_median + 5 * mad
            if np.isclose(y_min_limit, y_max_limit): y_min_limit -= 1; y_max_limit += 1
            ax.set_ylim(y_min_limit, y_max_limit)
            ax.plot(x_finite, y_finite, label="f'(x)")
        elif len(y_finite) == 1:
            ax.plot(x_finite, y_finite, 'o', label="f'(x) (un punto)")
            ax.set_ylim(y_finite[0] - 5, y_finite[0] + 5)
        else:
            print("Advertencia: No se encontraron puntos finitos para graficar.")
            ax.set_ylim(-10, 10)
        ax.set_xlabel("x"); ax.set_ylabel("f'(x)"); ax.set_title("Gráfica de la Derivada")
        ax.grid(True); ax.axhline(0, color='black', linewidth=0.5); ax.axvline(0, color='black', linewidth=0.5)
        buf = io.BytesIO(); plt.savefig(buf, format='png', bbox_inches='tight'); buf.seek(0); plt.close(fig)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        print(f"Imagen Base64 generada (primeros 60 chars): {img_base64[:60]}...")
        return jsonify({'image_base64': img_base64})
    except Exception as e:
        print(f"!!! Error graficando '{expresion_derivada_str}': {type(e).__name__} - {e}")
        import traceback; traceback.print_exc()
        error_msg = f"No se pudo generar la gráfica: {e}"
        return jsonify({'error': error_msg}), 400

# --- Ruta /descargar_pdf (ELIMINADA) ---
# La ruta /descargar_pdf y la clase PDF han sido completamente eliminadas.

# --- Bloque de ejecución ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Asegúrate de que host='0.0.0.0' está aquí
    app.run(host='0.0.0.0', debug=True)