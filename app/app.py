from flask import Flask, render_template, request
from mysqldb import DBConnector
from mysql.connector.errors import DatabaseError
import math

app = Flask(__name__)
application = app
app.config.from_pyfile('config.py')

db_connector = DBConnector(app)

from authorization import bp as authorization_bp, init_login_manager
app.register_blueprint(authorization_bp)
init_login_manager(app)

from books import bp as books_bp, form_book_data
app.register_blueprint(books_bp)

PAGE_COUNT = 5


if __name__ == 'main':
    app.run(debug=True)
   

@app.route('/', methods=["GET","POST"]) 
def books():
    books = []
    page_number = request.args.get('page_number', 1, type=int)
    try:
        query = ("SELECT * FROM books ORDER BY year_pub DESC "
                f"LIMIT {PAGE_COUNT} OFFSET {PAGE_COUNT*(page_number - 1)}")
        with db_connector.connect().cursor(named_tuple=True) as cursor:
            cursor.execute(query)
            books = cursor.fetchall()

            query2 = ("SELECT COUNT(*) AS count FROM books")
            cursor.execute(query2)
            total_count = cursor.fetchone().count  
            total_pages = math.ceil(total_count / PAGE_COUNT + 1)
            start_page = max(page_number - 3, 1)
            end_page = min(page_number + 3, total_pages)

        books_dict = []
        for book in books:
            book_dict = form_book_data(book)
            books_dict.append(book_dict)
        return render_template("index.html", books=books_dict, start_page=start_page, end_page=end_page, page_number=page_number)
    
    except DatabaseError as error:
        print(f"Произошла ошибка при получении данных: {error}") 
