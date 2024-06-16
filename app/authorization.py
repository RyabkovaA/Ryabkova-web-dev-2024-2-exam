from flask import Blueprint, render_template, request, url_for, redirect, flash, current_app
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from app import db_connector
from users_policy import UsersPolicy
from functools import wraps

bp = Blueprint('auth', __name__, url_prefix='/auth')

class User(UserMixin):
    def __init__(self, user_id, login, role_id, full_name):
        self.id = user_id
        self.login = login
        self.role_id = role_id
        self.full_name = full_name

    def is_admin(self):
       return self.role_id == current_app.config['ADMIN_ROLE_ID']
    
    def is_moderator(self):
        return self.role_id == current_app.config['MODERATOR_ROLE_ID']

    def can(self, action, user=None):
        self.users_policy = UsersPolicy(user)
        method = getattr(self.users_policy, action, lambda: False)
        return method()
    
    def get_name(self):
        return self.full_name
    
def can_user(action):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = None
            user_id = kwargs.get('user_id')
            if user_id:
                with db_connector.connect().cursor(named_tuple=True) as cursor:
                    cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
                    user = cursor.fetchone()

            if not current_user.can(action, user):
                flash("У вас недостаточно прав для выполнения данного действия", category='warning')
                return redirect(url_for("books.books"))
            return func(*args, **kwargs)
        return wrapper
    return decorator


def init_login_manager(app):
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Для выполнения данного действия необходимо пройти процедуру аутентификации"
    login_manager.login_message_category = 'warning'
    login_manager.user_loader(load_user)

def load_user(user_id):
    query = ("SELECT id, login, role_id, CONCAT(last_name, ' ', "
            "first_name, ' ', COALESCE(middle_name, '')) AS full_name FROM users WHERE id=%s")

    with db_connector.connect().cursor(named_tuple=True) as cursor:

        cursor.execute(query, (user_id,))

        user = cursor.fetchone()

    if user:
        return User(user_id, user.login, user.role_id, user.full_name)

    return None


@bp.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template('auth.html')
    
    login = request.form.get("login", "")
    password = request.form.get("pass", "")
    remember = request.form.get("remember") == "on"

    query = ("SELECT id, login, role_id, CONCAT(last_name, ' ', "
            "first_name, ' ', COALESCE(middle_name, '')) AS full_name "
            "FROM users WHERE login=%s AND password_hash=SHA2(%s, 256)")
    
    with db_connector.connect().cursor(named_tuple=True) as cursor:
        
        cursor.execute(query, (login, password))

        #print(cursor.statement)

        user = cursor.fetchone()
        print(user)

    if user is not None:
        login_user(User(user.id, user.login, user.role_id, user.full_name), remember=remember)
        flash("Авторизация прошла успешно", category='success')
        target_page = request.args.get("next", url_for('books.books'))
        return redirect(target_page)
                  
    flash("Невозможно аутентифицироваться с указанными логином и паролем", category='danger')
    return render_template("auth.html")

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('books.books'))