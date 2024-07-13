from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
from functools import wraps
from reportlab.pdfgen import canvas
from io import BytesIO
from flask import send_file
from datetime import datetime, timedelta
from decimal import Decimal
from flask_login import login_required
import bcrypt

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
    city = request.args.get('city', '')
    hotel_name = request.args.get('hotel_name', '')
    min_price = request.args.get('min_price', type=int)
    max_price = request.args.get('max_price', type=int)
    # Handle invalid price range
    if min_price is not None and max_price is not None and max_price < min_price:
        flash('Max price cannot be lower than min price', 'error')
        return redirect(url_for('hotels'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Determine the current month
    current_month = datetime.now().month
    query = "SELECT hotel_id, name, city, CASE WHEN %s THEN peak_price ELSE off_peak_price END AS price FROM hotels WHERE 1=1"
    # Determine if it's peak season
    is_peak = current_month in [1, 5, 6, 7, 8, 12]
    # Add conditions based on search criteria
    params = [is_peak]
    if city:
        query += " AND city LIKE %s"
        params.append("%" + city + "%")
    
    if hotel_name:
        query += " AND name LIKE %s"
        params.append("%" + hotel_name + "%")
    
    if min_price is not None:
        query += " AND price >= %s"
        params.append(min_price)
    
    if max_price is not None:
        query += " AND price <= %s"
        params.append(max_price)
    
    cursor.execute(query, tuple(params))
    hotels = cursor.fetchall()
    return render_template('home.html', hotels=hotels)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM Users WHERE username = %s', (username,))
        account = cursor.fetchone()

        if account:
            flash(f'Account already exists!') 
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash(f'Invalid email address!')
        elif not re.match(r'[A-Za-z0-9]+', username):
            flash(f'Username must contain only characters and numbers!')
        elif not username or not password or not email:
            flash(f'Please fill out the form!')
        else:
            cursor.execute('INSERT INTO Users (username, password, email) VALUES (%s, %s, %s)', (username, hashed_password, email))
            mysql.connection.commit()
            flash(f'You have successfully registered!')
            return redirect(url_for('hotels'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'loggedin' in session:
        return redirect(url_for('hotels'))
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM Users WHERE username = %s', (username,))
        account = cursor.fetchone()
        if account:
            # Extract the hashed password from the database
            hashed_password_db = account['password'].encode('utf-8')
            # Check if the hashed passwords match
            if bcrypt.checkpw(password.encode('utf-8'), hashed_password_db): #
                # Passwords match
                session['loggedin'] = True
                session['user_id'] = account['user_id']
                session['username'] = account['username']
                session['is_admin'] = account['is_admin']
                return redirect(url_for('hotels'))
            else:
                # Passwords do not match
                flash(f'Incorrect username/password!') 
                print("Incorrect username or pass")

        else:
            return 'User not found!'
    return render_template('login.html')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/update_password', methods=['GET', 'POST'])
@login_required
def update_password():
    if 'loggedin' in session:
        if request.method == 'POST' and 'old_password' in request.form and 'new_password' in request.form:
            old_password = request.form['old_password']
            new_password = request.form['new_password']
            
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM Users WHERE user_id = %s', (session['user_id'],))
            account = cursor.fetchone()
            
            if account and bcrypt.checkpw(old_password.encode('utf-8'), account['password'].encode('utf-8')):
                new_password_hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                cursor.execute('UPDATE Users SET password = %s WHERE user_id = %s', (new_password_hashed.decode('utf-8'), session['user_id']))
                mysql.connection.commit()
                return redirect(url_for('hotels')) 
            
            else:
                flash('Incorrect old password', 'error')
        
        return render_template('update_password.html')
    
    return redirect(url_for('login'))


@app.route('/profile')
def profile():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM Users WHERE user_id = %s', (session['user_id'],))
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

@app.route('/hotels')
def hotels():
    city = request.args.get('city', '')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if city:
        query = 'SELECT hotel_id, name, city FROM Hotels WHERE city LIKE %s'
        cursor.execute(query, ('%' + city + '%',))
    else:
        query = 'SELECT hotel_id, name, city FROM Hotels'
        cursor.execute(query)

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


def calculate_price(room_id, check_in_date, check_out_date, num_guests):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT room_type, max_guests, hotel_id FROM Rooms WHERE room_id = %s', (room_id,))
    room = cursor.fetchone()
    hotel_id_for_selected_room = room['hotel_id']
    room_type = room['room_type']
    max_guests = room['max_guests']
    # Fetch hotel details including peak and off-peak prices
    cursor.execute('SELECT * FROM Hotels WHERE hotel_id = %s', (hotel_id_for_selected_room,))
    hotel = cursor.fetchone()
    current_month = datetime.now().month
    if current_month in [1, 5, 6, 7, 8, 12]:
        price = hotel['peak_price']
    else:
        price = hotel['off_peak_price']

    # Calculate the number of days of stay
    days_of_stay = (check_out_date - check_in_date).days
    # Ensure price is a float
    price = float(price) 
    # Calculate the total price
    total_price = price * days_of_stay

    if room_type == 'Standard':
        total_price += price * num_guests
    elif room_type == 'Standard' and num_guests > 1:
        return 'A standard room cannot have more than 1 guest'
    elif room_type == 'Double' and num_guests == 1:
        total_price += 0.20 * price * num_guests * days_of_stay
    elif room_type == 'Double' and num_guests == 2:
        total_price += 0.3 * price * num_guests * days_of_stay
    elif room_type == 'Double' and num_guests > 2:
        return 'A Double room cannot have more than 2 guests'
    elif room_type == 'Family' and 4 >= num_guests > 1:
        total_price += 0.05 * price * num_guests * days_of_stay
    elif room_type == 'Family' and  num_guests > 4:
        return 'A Family Room cannot have more than 4 guests'
    elif room_type == 'Executive':
        total_price += 5 * price * num_guests * days_of_stay
    else:
        return 'Please review the Room Type'

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

def calculate_price_in_currency(discounted_price, currency):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM conversion_rates WHERE currency = %s', (currency,))
    conversion_rates = cursor.fetchone()
    currency_rate = conversion_rates['rate']

    return float(discounted_price) * float(currency_rate)


@app.route('/book_room/<int:hotel_id>', methods=['GET', 'POST'])
@login_required
def book_room(hotel_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Hotels WHERE hotel_id = %s', (hotel_id,))
    hotel = cursor.fetchone()
    cursor.execute('SELECT * FROM Rooms WHERE hotel_id = %s', (hotel_id,))
    rooms = cursor.fetchall()

    if request.method == 'POST' and 'room' in request.form and 'check_in_date' in request.form and 'check_out_date' in request.form and 'num_guests' in request.form:
        user_id = session.get('user_id')
        if not user_id:
            return 'User ID not found in session. Please log in again.'
        
        room_id = request.form['room']
        check_in_date = datetime.strptime(request.form['check_in_date'], '%Y-%m-%d').date()
        check_out_date = datetime.strptime(request.form['check_out_date'], '%Y-%m-%d').date()
        num_guests = int(request.form['num_guests'])
        currency = request.form['currency']
        cursor.execute('SELECT max_guests, status FROM Rooms WHERE room_id = %s', (room_id,))
        room = cursor.fetchone()
        max_guests = room['max_guests']
        room_status = room ['status']
        current_date = datetime.now().date()
        max_booking_date = current_date + timedelta(days=4 * 30)  # Four months in advance

        # Check if check-in or check-out date is earlier than today
        if check_in_date < current_date or check_out_date < current_date:
            flash('Check-in and Check-out dates cannot be earlier than today.')
            return redirect(url_for('book_room', hotel_id=hotel_id))
    
        # Check if check-out date is earlier than check-in date
        if check_out_date <= check_in_date:
            flash('Check-out date cannot be earlier than check-in date.')
            return redirect(url_for('book_room', hotel_id=hotel_id))
        
        if check_in_date > max_booking_date or check_out_date > max_booking_date:
            flash('You cannot book more than 4 months in advance.')
            return redirect(url_for('book_room', hotel_id=hotel_id))
        
        # Check if the booking duration exceeds 20 days
        stay_duration = (check_out_date - check_in_date).days
        if stay_duration > 20:
            flash('Maximum stay duration is 20 days. Please make separate bookings for a longer stay.')
            return redirect(url_for('book_room', hotel_id=hotel_id))

        if num_guests > max_guests:
            flash(f'The selected room can only accommodate up to {max_guests} guests.')
            return redirect(url_for('book_room', hotel_id=hotel_id))
        
        if room_status == 'maintenance':
            flash(f'The selected room is unavailable due to maintenance at the moment. Please pick another room.')
            return redirect(url_for('book_room', hotel_id = hotel_id))

        # Check for overlapping bookings
        cursor.execute('SELECT * FROM Bookings WHERE room_id = %s AND status = %s AND ((check_in_date <= %s AND check_out_date >= %s) OR (check_in_date <= %s AND check_out_date >= %s) OR (check_in_date >= %s AND check_out_date <= %s))', 
            (room_id, 'booked', check_in_date, check_in_date, check_out_date, check_out_date, check_in_date, check_out_date))
        overlapping_bookings = cursor.fetchall()

        if overlapping_bookings:
            available_dates = []
            for booking in overlapping_bookings:
                if booking['user_id'] != user_id:
                    if booking['check_in_date'] > check_out_date or booking['check_out_date'] < check_in_date:
                        continue
                    if check_in_date < booking['check_in_date']:
                        available_dates.append((check_in_date, booking['check_in_date'] - timedelta(days=1)))
                    if check_out_date > booking['check_out_date']:
                        available_dates.append((booking['check_out_date'] + timedelta(days=1), check_out_date))

            if not available_dates:
                flash('This room is already booked by another user during your selected dates.')
                return redirect(url_for('book_room', hotel_id=hotel_id))

            flash('This room is partially available. Available dates: {}'.format(', '.join(f"{start} to {end}" for start, end in available_dates)))
            return redirect(url_for('book_room', hotel_id=hotel_id))

        # Calculate total price (for simplicity, using off-peak season price)
        total_price = calculate_price(room_id, check_in_date, check_out_date, num_guests)
        final_price = calculate_price_in_currency(total_price, currency)

        # Fetch user details
        cursor.execute('SELECT username, email FROM Users WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()
        cursor.execute(
            'INSERT INTO Bookings (user_id, room_id, check_in_date, check_out_date, total_price, currency) VALUES (%s, %s, %s, %s, %s, %s)', 
            (user_id, room_id, check_in_date, check_out_date, final_price, currency)
        )
        cursor.execute(
            'UPDATE Rooms SET status = %s WHERE room_id = %s', 
            ('booked', room_id)
        )
        mysql.connection.commit()

        cursor.execute('SELECT booking_date, booking_id FROM Bookings WHERE user_id = %s AND check_in_date = %s AND check_out_date = %s', (user_id,check_in_date, check_out_date))
        booking_info = cursor.fetchone()
        booking_date = booking_info['booking_date']
        booking_id = booking_info['booking_id']


        # Generate PDF receipt
        buffer = BytesIO()
        p = canvas.Canvas(buffer)
        width, height = p._pagesize
        center_x = width / 2

        p.drawString(center_x - 55, height - 270, f"Booking ID: {booking_id}")
        p.drawString(center_x - 55, height - 290, f"User ID: {user_id}")
        p.drawString(center_x - 55, height - 310, f"Username: {user['username']}")
        p.drawString(center_x - 55, height - 330, f"Email: {user['email']}")
        p.drawString(center_x - 55, height - 350, f"Room ID: {room_id}")
        p.drawString(center_x - 55, height - 370, f"Booking Date: {booking_date}")
        p.drawString(center_x - 55, height - 390, f"Check-in Date: {check_in_date}")
        p.drawString(center_x - 55, height - 410, f"Check-out Date: {check_out_date}")
        p.drawString(center_x - 55, height - 430, f"Total Price: {final_price} {currency}")
        p.drawString(center_x - 55, height - 450, f"Status: booked")
        p.showPage()
        p.save()

        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f'receipt_{booking_id}_{user["username"]}.pdf', mimetype='application/pdf')
    
    return render_template('book_room.html', hotel=hotel, rooms=rooms)



@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # Fetch the booking details
        cursor.execute('SELECT room_id, booking_date, total_price, currency FROM Bookings WHERE booking_id = %s AND user_id = %s', (booking_id, session['user_id']))
        booking = cursor.fetchone()
        if not booking:
            flash('Booking not found or you do not have permission to cancel this booking.')
            return redirect(url_for('my_bookings'))  # Redirect to the page showing user's bookings

        room_id = booking['room_id']
        booking_date = booking['booking_date'].date()
        booking_price = booking['total_price']
        currency = booking['currency']
        # Calculate the number of days between today and the booking date
        today = datetime.today().date()
        days_until_booking = (booking_date - today).days
        # Determine cancellation charges
        if days_until_booking > 60:
            cancellation_charge = Decimal(0)
        elif 30 < days_until_booking <= 60:
            cancellation_charge = Decimal(0.4) * booking_price
        elif 10 < days_until_booking <= 30:
            cancellation_charge = Decimal(0.8) * booking_price
        else:
            cancellation_charge = Decimal(1.0) * booking_price

        # Update the booking status to 'cancelled' and set the cancellation charge
        cursor.execute('UPDATE Bookings SET status = %s, cancellation_charge = %s WHERE booking_id = %s', ('cancelled', cancellation_charge, booking_id))
        
        # Check if the status update was successful
        if cursor.rowcount == 0:
            raise Exception("Failed to update booking status")
        
        # Update the room status to 'available'
        cursor.execute('UPDATE Rooms SET status = %s WHERE room_id = %s', ('available', room_id))
        mysql.connection.commit()
        flash(f'Booking cancelled successfully. Cancellation charge: {currency} {cancellation_charge:.2f}')
    
        return redirect(url_for('my_bookings'))

    
@app.route('/my_bookings')
@login_required
def my_bookings():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Bookings WHERE user_id = %s', (session['user_id'],))
    bookings = cursor.fetchall()
    return render_template('my_bookings.html', bookings=bookings)


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

    cursor.execute('SELECT * FROM Rooms')
    rooms = cursor.fetchall()
    
    cursor.execute('SELECT * FROM conversion_rates')
    conversion_rates = cursor.fetchall()

    return render_template('admin_dashboard.html', hotels=hotels, bookings=bookings, users=users, rooms = rooms, conversion_rates = conversion_rates)

@app.route('/add_hotel', methods=['GET', 'POST'])
@admin_required
def add_hotel():
    if request.method == 'POST':
            name = request.form.get('name')
            city = request.form.get('city')
            capacity = request.form.get('capacity')
            peak_season_price = request.form.get('peak_price')
            off_peak_season_price = request.form.get('off_peak_price')
            
            # Ensure no field is None
            if None in [name, city, capacity, peak_season_price, off_peak_season_price]:
                print("One or more form fields are missing.")
                return render_template('add_hotel.html', error="Please fill out all fields")
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('INSERT INTO Hotels (name, city, capacity, peak_price, off_peak_price) VALUES (%s, %s, %s, %s, %s)', 
                           (name, city, capacity, peak_season_price, off_peak_season_price))
            mysql.connection.commit()
            return redirect(url_for('admin_dashboard'))
    
    return render_template('add_hotel.html')

@app.route('/delete_hotel/<int:hotel_id>')
@admin_required
def delete_hotel(hotel_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DELETE FROM hotels WHERE hotel_id = %s", (hotel_id,))
    mysql.connection.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_booking/<int:booking_id>')
@admin_required
def delete_boooking(booking_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DELETE FROM Bookings WHERE booking_id = %s", (booking_id,))
    mysql.connection.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_room/<int:room_id>')
@admin_required
def delete_room(room_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DELETE FROM rooms WHERE room_id = %s", (room_id,))
    mysql.connection.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/modify_hotel/<int:hotel_id>', methods=['GET', 'POST'])
@admin_required
def modify_hotel(hotel_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM hotels WHERE hotel_id = %s", (hotel_id,))
    mysql.connection.commit()
    hotels = cursor.fetchall()
    if request.method == 'GET':
        for hotel in hotels:
            if hotel['hotel_id'] == hotel_id:
                return render_template('modify_hotel.html', hotel=hotel)
        return 'Hotel not found', 404
    elif request.method == 'POST':
        for hotel in hotels:
                name = request.form['name']
                city = request.form['city']
                capacity = int(request.form['capacity'])
                off_peak_price = float(request.form['off_peak_price'])
                peak_price = float(request.form['peak_price'])
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute("UPDATE hotels SET name = %s, city= %s, capacity= %s, off_peak_price = %s, peak_price=%s  WHERE hotel_id = %s", (name, city , capacity, off_peak_price, peak_price, hotel_id,))
                mysql.connection.commit()
                return redirect(url_for('admin_dashboard'))
        return 'Hotel not found', 404

@app.route('/delete_user/<int:user_id>')
@admin_required
def delete_user(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    mysql.connection.commit()
    return redirect(url_for('admin_dashboard'))


@app.route('/add_room', methods=['GET', 'POST'])
@admin_required
def add_room():
    if request.method == 'POST' and 'hotel_id' in request.form:
        hotel_id = request.form['hotel_id']
        features = request.form['features']
        status = request.form['status']
        room_type = request.form['room_type']
        max_guests = request.form['max_guests']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # Get the hotel's capacity
        cursor.execute('SELECT capacity FROM Hotels WHERE hotel_id = %s', (hotel_id,))
        hotel = cursor.fetchone()
        hotel_capacity = hotel['capacity']
        # Calculate the maximum allowed rooms of each type
        max_standard_rooms = int(hotel_capacity * 0.30)
        max_double_rooms = int(hotel_capacity * 0.40)
        max_family_rooms = int(hotel_capacity * 0.20)
        max_executive_suites = int(hotel_capacity * 0.10)
        # Query the current distribution of room types in the hotel
        cursor.execute('SELECT room_type, COUNT(*) as count FROM Rooms WHERE hotel_id = %s GROUP BY room_type', (hotel_id,))
        current_rooms = cursor.fetchall()
        room_counts = { 'Standard': 0, 'Double': 0, 'Family': 0, 'Executive': 0 }
        for room in current_rooms:
            room_counts[room['room_type']] = room['count']
        # Check constraints
        if room_type == 'Standard' and room_counts['Standard'] >= max_standard_rooms:
            flash('Cannot add more Standard rooms. Limit reached.')
            return redirect(url_for('add_room'))
        elif room_type == 'Double' and room_counts['Double'] >= max_double_rooms:
            flash('Cannot add more Double rooms. Limit reached.')
            return redirect(url_for('add_room'))
        elif room_type == 'Family' and room_counts['Family'] >= max_family_rooms:
            flash('Cannot add more Family rooms. Limit reached.')
            return redirect(url_for('add_room'))
        elif room_type == 'Executive' and room_counts['Executive'] >= max_executive_suites:
            flash('Cannot add more Executive suites. Limit reached.')
            return redirect(url_for('add_room'))

        cursor.execute('INSERT INTO Rooms (hotel_id, status, features, room_type, max_guests) VALUES (%s, %s, %s, %s, %s)', 
                       (hotel_id, status, features, room_type, max_guests))
        mysql.connection.commit()
        return redirect(url_for('admin_dashboard'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Hotels')
    hotels = cursor.fetchall()
    
    return render_template('add_room.html', hotels=hotels)

@app.route('/change_room_status/<int:room_id>', methods=['GET', 'POST'])
@admin_required
def change_room_status(room_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM rooms WHERE room_id = %s", (room_id,))
    mysql.connection.commit()
    rooms = cursor.fetchall()
    if request.method == 'GET':
        for room in rooms:
            if room['room_id'] == room_id:
                return render_template('change_room_status.html', room=room)
        return 'Room not found', 404
    elif request.method == 'POST':
        for room in rooms:
                status = request.form['status']
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute("UPDATE rooms SET status = %s  WHERE room_id = %s", (status, room_id,))
                cursor.execute("UPDATE bookings SET status = %s  WHERE room_id = %s", (status, room_id,))
                mysql.connection.commit()
                return redirect(url_for('admin_dashboard'))
        return 'Room not found', 404
    
@app.route('/change_conversion_rate/<string:currency>', methods=['GET', 'POST'])
@admin_required
def change_conversion_rate(currency):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM conversion_rates WHERE currency = %s", (currency,))
    conversion_rate = cursor.fetchone()
    if conversion_rate is None:
        return 'Currency not found', 404
    
    if request.method == 'GET':
        return render_template('change_conversion_rate.html', conversion_rate=conversion_rate)
    
    elif request.method == 'POST':
        rate = request.form['rate']
        cursor.execute("UPDATE conversion_rates SET rate = %s WHERE currency = %s", (rate, currency,))
        mysql.connection.commit()
        return redirect(url_for('admin_dashboard'))


@app.route('/modify_users', methods=['GET', 'POST'])
@admin_required
def modify_users():
    if 'username' not in session or not session.get('is_admin'):
        flash('You must be logged in as an admin to access this page.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = request.form['user_id']
        new_password = request.form['new_password']

        if user_id and new_password:
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("UPDATE users SET password = %s WHERE user_id = %s", (hashed_password, user_id))
            mysql.connection.commit()
            cursor.close()
            return redirect(url_for('admin_dashboard'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT user_id, username, email FROM users")
    users = cursor.fetchall()
    cursor.close()

    return render_template('modify_users.html', users=users)

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
