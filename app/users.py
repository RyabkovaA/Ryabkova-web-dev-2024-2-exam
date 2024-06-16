from flask import Blueprint, render_template, request, url_for, redirect, flash
from flask_login import current_user, login_required
from mysql.connector.errors import DatabaseError
from app import db_connector

bp = Blueprint('users', __name__, url_prefix='/users')

CREATE_USER_FIELDS = ['login', 'password', 'last_name', 'first_name', 'middle_name', 'role_id']
EDIT_USER_FIELDS = ['last_name', 'first_name', 'middle_name', 'role_id']
CHECK_USER_FIELDS = ['login', 'password', 'last_name', 'first_name', 'role_id']

def get_roles():
    query = "SELECT * FROM roles"

    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        roles = cursor.fetchall()
    return roles


@bp.route('/')
def index():
    query = 'SELECT users.*, roles.name as role_name FROM users LEFT JOIN roles ON users.role_id = roles.id'

    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        data = cursor.fetchall()
    
    return render_template("users.html", users=data)

def get_form_data(required_fields):
    user = {}
    for field in required_fields:
        user[field] = request.form.get(field) or None

    return user

@bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(user_id):
    query = ("SELECT * FROM users where id = %s")
    roles = get_roles()
    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (user_id, ))
        user = cursor.fetchone() 

    if request.method == "POST":
        user = get_form_data(EDIT_USER_FIELDS)

        if not current_user.can('assign_roles'):
            del user['role_id']

        columns = ','.join([f'{key}=%({key})s' for key in user])
        user['user_id'] = user_id

        query = (f"UPDATE users SET {columns} WHERE id=%(user_id)s ")

        try:
            with db_connector.connect().cursor(named_tuple=True) as cursor:
                cursor.execute(query, user)
                print(cursor.statement)
                db_connector.connect().commit()
            
            flash("Запись пользователя успешно обновлена", category="success")
            return redirect(url_for('users.index'))
        except DatabaseError as error:
            flash(f'Ошибка редактирования пользователя! {error}', category="danger")
            db_connector.connect().rollback()    

    return render_template("edit_user.html", user=user, roles=roles)

@bp.route('/user/<int:user_id>/delete', methods=["POST"])
@login_required
def delete(user_id):
    query = "DELETE FROM users WHERE id=%s"
    try:
        with db_connector.connect().cursor(named_tuple=True) as cursor:
            cursor.execute(query, (user_id, ))
            db_connector.connect().commit() 
        
        flash("Запись пользователя успешно удалена", category="success")
    except DatabaseError as error:
        flash(f'Ошибка удаления пользователя! {error}', category="danger")
        db_connector.connect().rollback()    
    
    return redirect(url_for('users.index'))

@bp.route('/<int:user_id>/show', methods=["GET","POST"])
def show(user_id):
    query = 'SELECT users.*, roles.name as role_name FROM users LEFT JOIN roles ON users.role_id = roles.id WHERE users.id=%s'
    try:
        with db_connector.connect().cursor(named_tuple=True) as cursor:
            cursor.execute(query, (user_id, ))
            user = cursor.fetchone()
        
    except DatabaseError as error:
        flash(f'Ошибка просмотра пользователя! {error}', category="danger")
        db_connector.connect().rollback()    
    
    return render_template("show_user.html", user=user)
