from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from reportlab.pdfgen import canvas
from io import BytesIO
from flask import send_file
from datetime import datetime
from decimal import Decimal

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
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM Users WHERE username = %s', (username,))
        account = cursor.fetchone()

        if account:
            return 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            return 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            return 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            return 'Please fill out the form!'
        else:
            cursor.execute('INSERT INTO Users (username, password, email) VALUES (%s, %s, %s)', (username, password, email))
            mysql.connection.commit()
            return 'You have successfully registered!'

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Check if the user is already logged in
    if 'loggedin' in session:
        return redirect(url_for('hotels'))

    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM Users WHERE username = %s AND password = %s', (username, password))
        account = cursor.fetchone()
        print(f"Account: {account}")

        if account:
            # Create session data
            session['loggedin'] = True
            session['user_id'] = account['user_id']
            session['username'] = account['username']
            session['is_admin'] = account['is_admin'] 

            return redirect(url_for('hotels'))
        else:
            return 'Incorrect username/password!'
    return render_template('login.html')



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
def admin_dashboard_welcome():
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


def calculate_price(room_id, check_in_date, check_out_date):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT price FROM Rooms WHERE room_id = %s', (room_id,))
    room = cursor.fetchone()
    base_price = room['price']

    # Calculate the number of days of stay
    days_of_stay = (check_out_date - check_in_date).days

    # Calculate the total price
    total_price = base_price * days_of_stay

    # Apply any discounts if applicable
    total_price = apply_advanced_booking_discount(check_in_date, total_price)
    return total_price

def apply_advanced_booking_discount(check_in_date, total_price):
    days_in_advance = (check_in_date - datetime.now().date()).days
    if  80 >= days_in_advance >= 90:
        discount = 0.25  # 25% discount
    elif 60 >= days_in_advance >= 79:
        discount = 0.20  # 20% discount
    elif 45 >= days_in_advance >= 59:
        discount = 0.15  # 15% discount
    elif 31 >= days_in_advance >= 44:
        discount = 0.10 # 10% discount
    else:
        discount = 0.0  # No discount
    # Convert total_price to float, apply discount, then convert back to Decimal
    total_price_float = float(total_price)
    discounted_price_float = total_price_float * (1 - discount)
    discounted_price = Decimal(discounted_price_float)

    return discounted_price

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
        user_id = session.get('user_id')
        if not user_id:
            return 'User ID not found in session. Please log in again.'
            return redirect(url_for('login'))

        room_id = request.form['room']
        check_in_date = datetime.strptime(request.form['check_in_date'], '%Y-%m-%d').date()
        check_out_date = datetime.strptime(request.form['check_out_date'], '%Y-%m-%d').date()

        # Calculate total price (for simplicity, using off-peak season price)
        total_price = calculate_price(room_id, check_in_date, check_out_date)

        cursor.execute(
            'INSERT INTO Bookings (user_id, room_id, check_in_date, check_out_date, total_price) VALUES (%s, %s, %s, %s, %s)', 
            (user_id, room_id, check_in_date, check_out_date, total_price)
        )
        mysql.connection.commit()

        booking_id = cursor.lastrowid

        # Generate PDF receipt
        buffer = BytesIO()
        p = canvas.Canvas(buffer)
        p.drawString(100, 750, f"Booking ID: {booking_id}")
        p.drawString(100, 735, f"User ID: {user_id}")
        p.drawString(100, 720, f"Room ID: {room_id}")
        p.drawString(100, 705, f"Check-in Date: {check_in_date}")
        p.drawString(100, 690, f"Check-out Date: {check_out_date}")
        p.drawString(100, 675, f"Total Price: {total_price}")
        p.drawString(100, 660, f"Status: booked")
        p.showPage()
        p.save()

        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name='receipt.pdf', mimetype='application/pdf')
    
    return render_template('book_room.html', hotel=hotel, rooms=rooms)

@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Hotels')
    hotels = cursor.fetchall()
    
    cursor.execute('SELECT * FROM Bookings')
    bookings = cursor.fetchall()
    
    cursor.execute('SELECT * FROM Users')
    users = cursor.fetchall()
    
    return render_template('admin_dashboard.html', hotels=hotels, bookings=bookings, users=users)


@app.route('/add_hotel', methods=['GET', 'POST'])
@admin_required
def add_hotel():
    if request.method == 'POST' and 'name' in request.form and 'city' in request.form and 'capacity' in request.form and 'peak_price' in request.form and 'off_peak_price' in request.form:
        name = request.form['name']
        city = request.form['city']
        capacity = request.form['capacity']
        peak_season_price = request.form['peak_price']
        off_peak_season_price = request.form['off_peak_price']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO Hotels (name, city, capacity, peak_price, off_peak_price) VALUES (%s, %s, %s, %s, %s)', 
                       (name, city, capacity, peak_season_price, off_peak_season_price))
        mysql.connection.commit()
        return redirect(url_for('admin_dashboard'))
    
    return render_template('add_hotel.html')

@app.route('/add_room', methods=['GET', 'POST'])
@admin_required
def add_room():
    if request.method == 'POST' and 'hotel_id' in request.form and 'price' in request.form and 'features' in request.form:
        hotel_id = request.form['hotel_id']
        price = request.form['price']
        features = request.form['features']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO Rooms (hotel_id, price, features) VALUES (%s, %s, %s)', 
                       (hotel_id, price, features))
        mysql.connection.commit()
        return redirect(url_for('admin_dashboard'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Hotels')
    hotels = cursor.fetchall()
    
    return render_template('add_room.html', hotels=hotels)

@app.route('/generate_reports')
@admin_required
def generate_reports():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Monthly Sales
    cursor.execute('SELECT DATE_FORMAT(booking_date, "%Y-%m") AS month, SUM(total_price) AS sales FROM Bookings GROUP BY month')
    monthly_sales = cursor.fetchall()
    
    # Sales for Each Hotel
    cursor.execute('''
        SELECT Rooms.hotel_id, SUM(Bookings.total_price) AS sales
        FROM Bookings
        JOIN Rooms ON Bookings.room_id = Rooms.room_id
        GROUP BY Rooms.hotel_id
    ''')
    hotel_sales = cursor.fetchall()
    
    # Top Customers
    cursor.execute('SELECT user_id, SUM(total_price) AS total_spent FROM Bookings GROUP BY user_id ORDER BY total_spent DESC LIMIT 5')
    top_customers = cursor.fetchall()
    
    return render_template('reports.html', monthly_sales=monthly_sales, hotel_sales=hotel_sales, top_customers=top_customers)



if __name__ == '__main__':
    app.run(debug=True)
