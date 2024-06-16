from flask import Blueprint, render_template, request, url_for, redirect, flash
from flask_login import current_user, login_required
from mysql.connector.errors import DatabaseError
from app import db_connector
import math
import bleach
import markdown

bp = Blueprint('books', __name__, url_prefix='/books')
ADD_BOOK_FIELDS = ['', '', '', '']
PAGE_COUNT = 10
EDIT_BOOK_FIELDS = ['name', 'author', 'year_pub', 'publishment', 'pages', 'description']
CHECK_BOOK_FIELDS = ['name', 'author', 'year_pub', 'publishment', 'pages', 'description']
SCORE_NAMES = ['ужасно', 'плохо', 'неудовлетворительно', 'удовлетворительно', 'хорошо', 'отлично']

def get_reviews_count(book_id):
    with db_connector.connect().cursor(named_tuple=True, buffered=True) as cursor:
        query = ("SELECT COUNT(*) AS review_counter FROM reviews LEFT JOIN books "
                              "ON books.id=reviews.book_id WHERE reviews.book_id = %s "
                              "GROUP BY reviews.book_id")
        cursor.execute(query, (book_id, ))
        book_reviews_count = cursor.fetchone()
    if book_reviews_count:
        return book_reviews_count.review_counter
    return 0

def get_average_score(book_id):
    with db_connector.connect().cursor(named_tuple=True, buffered=True) as cursor:
        query = ("SELECT AVG(reviews.score) AS avg_score FROM reviews LEFT JOIN books "
                "ON books.id=reviews.book_id WHERE reviews.book_id = %s "
                "GROUP BY reviews.book_id")
        cursor.execute(query, (book_id, ))
        score = cursor.fetchone()
    if score:
        return round(score.avg_score, 2)
    return 0

def get_reviews(book_id):
    reviews = []
    query = ("SELECT reviews.*, CONCAT(users.last_name, ' ', "
            "users.first_name, ' ', COALESCE(users.middle_name, '')) AS full_name "
            "FROM  reviews LEFT JOIN users ON reviews.user_id = users.id WHERE reviews.book_id=%s")
    with db_connector.connect().cursor(named_tuple=True, buffered=True) as cursor:
        cursor.execute(query, (book_id, ))
        reviews = cursor.fetchall()
    return reviews

def get_user_review(user_id, book_id):
    review = []
    query = ("SELECT * FROM reviews WHERE book_id=%s AND user_id=%s")
    with db_connector.connect().cursor(named_tuple=True, buffered=True) as cursor:
        cursor.execute(query, (book_id, user_id))
        review = cursor.fetchone()
    return review

@bp.route('/<int:book_id>/review', methods=["GET","POST"]) 
def add_review(book_id):
    error = None
    if request.method == 'POST':
        review_text = get_form_data(['review_text'])['review_text']
        score = request.form.get('score')

        if review_text == None:
            flash('Добавьте текст рецензии!', category="danger")
            return render_template("review_form.html", score_names=SCORE_NAMES, error=error)
        
        query = ("INSERT INTO reviews (book_id, user_id, score, review_text) "
                 "VALUES (%s, %s, %s, %s)")
        try:
            with db_connector.connect().cursor(named_tuple=True) as cursor:
                cursor.execute(query, (book_id, current_user.id, score, review_text))
                db_connector.connect().commit()
                flash('Рецензия успешно добавлена!', category="success")    
                return redirect(url_for('books.show_book', book_id=book_id))
        except DatabaseError as error:
            flash(f'Ошибка создания рецензии! {error}', category="danger")    
            db_connector.connect().rollback()


    return render_template("review_form.html", score_names=SCORE_NAMES)


@bp.route('/<int:book_id>', methods=["GET","POST"]) 
def show_book(book_id):
    query = "SELECT * FROM books WHERE books.id=%s"
    with db_connector.connect().cursor(named_tuple=True, buffered=True) as cursor:
        cursor.execute(query, (book_id, ))
        book = cursor.fetchone()
    book_data = form_book_data(book)
    reviews = get_reviews(book_id)
    review_ids = [review.id for review in reviews]
    print(review_ids)
    user_review = []
    print(current_user.id)
    if current_user.id in review_ids:
        user_review = get_user_review(current_user.id, book_id)
    return render_template("show_book.html", book=book_data, reviews=reviews, user_review=user_review, score_names=SCORE_NAMES)

def form_book_data(book):
    book_dict = book._asdict()
    reviews_count = get_reviews_count(book.id)
    book_dict['reviews_count'] = reviews_count
    average_score = get_average_score(book.id)
    book_dict['avg_score'] = average_score
    book_genres = get_book_genres(book.id)
    book_dict['genres'] = book_genres
    book_dict['description'] = markdown.markdown(book.description)

    return book_dict


@bp.route('/', methods=["GET","POST"]) 
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
            print(total_count)
            total_pages = math.ceil(total_count / PAGE_COUNT + 1)
            start_page = max(page_number - 3, 1)
            end_page = min(page_number + 3, total_pages)

        books_dict = []
        for book in books:
            book_dict = form_book_data(book)
            books_dict.append(book_dict)
        print(books_dict)
        return render_template("index.html", books=books_dict, start_page=start_page, end_page=end_page, page_number=page_number)
    
    except DatabaseError as error:
        print(f"Произошла ошибка при получении данных: {error}") 

def get_genres():
    genres = []
    query = ("SELECT * FROM genres")
    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        genres = cursor.fetchall()
    return genres

def get_book_genres(book_id):
    book_genres = []
    query = ("SELECT genres.* FROM genres LEFT JOIN book_genres ON genres.id=book_genres.genre_id "
             "WHERE book_genres.book_id=%s")
    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (book_id, ))
        book_genres = cursor.fetchall()
    return book_genres

@bp.route('/new',  methods=["GET", "POST"])
@login_required
def add_book():
    errors={}
    genres = get_genres()
    print(genres)
    return render_template("add_book.html", errors=errors, genres=genres)


def get_form_data(required_fields):
    book = {}
    for field in required_fields:
        book[field] = bleach.clean(request.form.get(field)) or None

    return book

def check_data(book):
    errors = {}
    for field in CHECK_BOOK_FIELDS:
        if not book.get(field):
            errors[field] = "Поле не может быть пустым"
    if 'year_pub' not in errors:
        errors['year_pub'] = check_number(book['year_pub'])
    if 'pages' not in errors:
        errors['pages'] = check_number(book['pages'])

    return errors


def check_number(number):
    try:
        number_int = int(number)
        if number_int < 0:
            return "Значение должно быть положительным числом"
        return None
    except ValueError:
        return "Значение должно быть положительным числом"

@bp.route('/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    errors = {}
    query = "SELECT * FROM books WHERE books.id=%s"
    with db_connector.connect().cursor(named_tuple=True, buffered=True) as cursor:
        cursor.execute(query, (book_id, ))
        book = cursor.fetchone()

    book_dict = book._asdict()
    book_genres = get_book_genres(book.id)
    book_dict['genres'] = book_genres
    book_dict['genres'] = [str(genre.id) for genre in book_genres]
    if request.method == 'POST':
        book_form_data = get_form_data(EDIT_BOOK_FIELDS)
        new_book_genres = [genre_id for genre_id in request.form.getlist('genres[]')]
        errors = check_data(book_form_data)
        print("new book genres", new_book_genres)

        if not new_book_genres:
            errors['genres'] = "Выберите жанры"
        if all(value is None for value in errors.values()):
            columns = ','.join([f'{key}=%({key})s' for key in book_form_data])
            book_form_data['id'] = book_id 
            print(book_form_data)
            print("columns to update", columns)

            query = (f"UPDATE books SET {columns} WHERE id=%(id)s")

            try:
                connection = db_connector.connect()
                with connection.cursor(named_tuple=True) as cursor:
                    cursor.execute(query, (book_form_data ))
                    
                    if update_genres_data(new_book_genres, book_id, connection):
                        connection.commit()
                        flash('Данные о книге успешно обновлены!', category="success")
                        return redirect(url_for("books.books"))
                    else:
                        connection.rollback()
                        flash('Ошибка обновления данных о книге!', category="danger")

            except DatabaseError as error:
                flash(f'Ошибка обновления данных! {error}', category="danger")    
                connection.rollback()            
    genres = get_genres()
    print(errors)
    print(book_dict)
    return render_template("edit_book.html", genres=genres, book=book_dict, errors=errors)
    
def update_genres_data(new_book_genres, book_id, connection):
    query_delete = ("DELETE FROM book_genres WHERE book_id=%s")
    try:
        with connection.cursor(named_tuple=True) as cursor:
            cursor.execute(query_delete, (book_id, ))
            query_genres = ("INSERT INTO book_genres (book_id, genre_id) VALUES (%s, %s)")

            for genre_id in new_book_genres:
                print(genre_id)
                try:
                    with connection.cursor(named_tuple=True) as cursor:
                        cursor.execute(query_genres, (book_id, genre_id))
                
                except DatabaseError as error:
                    flash(f'Ошибка добавления жанров! {error}', category="danger")    
                    return False
            return True

    except DatabaseError as error:
        flash(f'Ошибка обновления жанров! {error}', category="danger")    
        return False
