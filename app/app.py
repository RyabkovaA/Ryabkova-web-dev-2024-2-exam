from flask import Flask, render_template
from mysqldb import DBConnector


app = Flask(__name__)
application = app
app.config.from_pyfile('config.py')

db_connector = DBConnector(app)

from authorization import bp as authorization_bp, init_login_manager
app.register_blueprint(authorization_bp)
init_login_manager(app)

from books import bp as books_bp
app.register_blueprint(books_bp)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == 'main':
    app.run(debug=True)

   
