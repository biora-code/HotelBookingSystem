from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'MuShIPuShIMjAu890@?_!'
app.config['MYSQL_DB'] = 'WHBookingSystem'

mysql = MySQL(app)

# Set the secret key to some random bytes. Keep this really secret!
app.secret_key = 'your_secret_key'

@app.route('/')
def index():
    return 'Welcome to WH Booking System'

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        email = request.form['email']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM Users WHERE username = %s', (username,))
        account = cursor.fetchone()

        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            cursor.execute('INSERT INTO Users (username, password, email) VALUES (%s, %s, %s)', (username, password, email))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
            return redirect(url_for('login'))
    elif request.method == 'POST':
        msg = 'Please fill out the form!'
    return render_template('register.html', msg=msg)

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM Users WHERE username = %s', (username,))
        account = cursor.fetchone()

        if account and check_password_hash(account['password'], password):
            session['loggedin'] = True
            session['id'] = account['user_id']
            session['username'] = account['username']
            session['is_admin'] = account['is_admin']
            return redirect(url_for('profile'))
        else:
            return 'Incorrect username/password!'
    return render_template('login.html', msg=msg)


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/update_password', methods=['GET', 'POST'])
def update_password():
    msg = ''
    if 'loggedin' in session:
        if request.method == 'POST' and 'old_password' in request.form and 'new_password' in request.form:
            old_password = request.form['old_password']
            new_password = request.form['new_password']

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM Users WHERE user_id = %s', (session['id'],))
            account = cursor.fetchone()

            if account and check_password_hash(account['password'], old_password):
                new_password_hashed = generate_password_hash(new_password)
                cursor.execute('UPDATE Users SET password = %s WHERE user_id = %s', (new_password_hashed, session['id']))
                mysql.connection.commit()
                msg = 'Password updated successfully!'
            else:
                msg = 'Incorrect old password!'
        return render_template('update_password.html', msg=msg)
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM Users WHERE user_id = %s', (session['id'],))
        account = cursor.fetchone()
        return render_template('profile.html', account=account)
    return redirect(url_for('login'))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' not in session or not session.get('is_admin'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@admin_required
def admin_dashboard():
    return 'Welcome to the admin dashboard!'

@app.route('/hotels')
def hotels():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Hotels')
    hotels = cursor.fetchall()
    return render_template('hotels.html', hotels=hotels)

@app.route('/hotels/<int:hotel_id>')
def hotel_details(hotel_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Hotels WHERE hotel_id = %s', (hotel_id,))
    hotel = cursor.fetchone()
    cursor.execute('SELECT * FROM Rooms WHERE hotel_id = %s', (hotel_id,))
    rooms = cursor.fetchall()
    return render_template('hotel_details.html', hotel=hotel, rooms=rooms)

@app.route('/book_room/<int:hotel_id>', methods=['GET', 'POST'])
def book_room(hotel_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Hotels WHERE hotel_id = %s', (hotel_id,))
    hotel = cursor.fetchone()
    cursor.execute('SELECT * FROM Rooms WHERE hotel_id = %s', (hotel_id,))
    rooms = cursor.fetchall()

    if request.method == 'POST' and 'room' in request.form and 'check_in_date' in request.form and 'check_out_date' in request.form:
        room_id = request.form['room']
        check_in_date = request.form['check_in_date']
        check_out_date = request.form['check_out_date']

        # Calculate total price (for simplicity, using off-peak season price)
        cursor.execute('SELECT price FROM Rooms WHERE room_id = %s', (room_id,))
        room = cursor.fetchone()
        total_price = room['price']

        cursor.execute('INSERT INTO Bookings (user_id, room_id, check_in_date, check_out_date, total_price, status) VALUES (%s, %s, %s, %s, %s, %s)', 
                       (session['id'], room_id, check_in_date, check_out_date, total_price, 'booked'))
        mysql.connection.commit()
        return 'Booking successful!'
    
    return render_template('book_room.html', hotel=hotel, rooms=rooms)


if __name__ == '__main__':
    app.run(debug=True)
