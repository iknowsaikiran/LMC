from flask import Flask, render_template, request, redirect, url_for, session, flash, json, jsonify
from flask_mysqldb import MySQL
from math import radians, cos, sin, asin, sqrt
import logging
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'


# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Saty@136'
app.config['MYSQL_DB'] = 'hospital'

mysql = MySQL(app)


# Function to calculate distance between two coordinates using Haversine formula
# Function to calculate distance between two coordinates using Haversine formula
from math import radians, sin, cos, sqrt, atan2

def haversine(lat1, lon1, lat2, lon2):
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat / 2)*2 + cos(lat1) * cos(lat2) * sin(dlon / 2)*2
    
    # Clamp a between 0 and 1 to avoid math domain errors
    a = max(0, min(1, a))
    
    c = 2 * atan2(sqrt(a), sqrt(1 - a))  # Use atan2 instead of asin
    
    radius = 6371  # Radius of Earth in kilometers
    distance = radius * c
    
    return distance

@app.route('/', methods=['GET', 'POST'])
def index():
    # Check if user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    username = session['username']  # Get the username from the session
    print(f"Logged in user: {username}")  # Debugging

    if request.method == 'POST':
        # Handle POST request (when the geolocation data is sent)
        data = request.get_json()  # Parse the JSON data
        print("Received data:", data)  # Debugging to verify received data

        user_latitude = float(data.get('latitude'))
        user_longitude = float(data.get('longitude'))

        # Debugging: Print the latitude and longitude
        print(f"User Latitude: {user_latitude}, User Longitude: {user_longitude}")
        # Fetch hospital data from the database with favorite status
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT 
                h.hospital_id, 
                h.hospital_name, 
                h.timings, 
                h.years_since_established, 
                h.opcard_price, 
                h.latitude, 
                h.longitude, 
                CASE 
                    WHEN f.username IS NOT NULL THEN TRUE 
                    ELSE FALSE 
                END AS is_favorite
            FROM hospitals h
            LEFT JOIN favourites f 
            ON h.hospital_id = f.hospital_id AND f.username = %s
        """, (username,))
        hospitals = cur.fetchall()
        cur.close()

        # Compute nearby hospitals
        nearby_hospitals = []
        for hospital in hospitals:
        
            hospital_id, hospital_name, timings, years_since_established, opcard_price, lat, lon, is_favourite = hospital
            distance = haversine(user_latitude, user_longitude, lat, lon)
            if distance <= 5:  # Check if the hospital is within 5 km
                nearby_hospitals.append({
                    
                    'hospital_id': hospital_id,
                    'hospital_name': hospital_name,
                    'timings': timings,
                    'years_since_established': years_since_established,
                    'opcard_price': opcard_price,
                    'distance': round(distance, 2),
                    'is_favourite': is_favourite # Round distance to 2 decimal places
                })

        print("Nearby hospitals:", nearby_hospitals)  # Debugging

        # Return nearby hospitals as JSON response
        return jsonify(nearby_hospitals)

    # If GET request (when the page is first loaded)
    return render_template('index.html', hospitals=[])    

@app.route('/about_us')
def about_us():
    return render_template('about.html')



@app.route('/appointment', methods=['GET', 'POST'])
def appointment():
    if request.method == 'POST':
        # Get form data
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')        
        email = request.form.get('email')
        phone_number = request.form.get('number')
        gender = request.form.get('gender')
        #choose_doctor = request.form.get('choose_doctor')
        department = request.form.get('department')
        appointment_date = request.form.get('appointmentDate')
        appointment_time = request.form.get('appointmentTime')
        purpose = request.form.get('comments')
        
        # Validate form inputs
        if not first_name or not email or not phone_number:
            flash("All fields are required!")
            return redirect(url_for('appointment'))
        # Insert into database
        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO hospital_appointments 
                (first_name, last_name, email, phone_number, gender, department, appointment_date, appointment_time, purpose) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (first_name, last_name, email, phone_number, gender, department, appointment_date, appointment_time, purpose))
            mysql.connection.commit()
            flash("Appointment successfully booked!")
            cur.close()
            return redirect(url_for('appointment_success'))            
        except Exception as e:
            print(f"Error occurred: {e}")
            mysql.connection.rollback()
            flash(f"An error occurred: {e}", "error")
            return render_template('appointment.html')

    return render_template('appointment.html') 



# @app.route('/bookappointment', methods=['GET', 'POST'])
# def appointment():
#     if request.method == 'POST':
      
#         # Insert into database
#         try:
#             conn = mysql.connector.connect(**db_config)
#             cursor = conn.cursor()
#             query = """
#                 INSERT INTO hospital_appointments 
#                 (your_name, your_email, your_mobile, gender, choose_doctor, department, choose_date, choose_time, describe_your_problem) 
#                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
#             """
#             values = (your_name, your_email, your_mobile, gender, choose_doctor, department, choose_date, choose_time, describe_your_problem)
#             cursor.execute(query, values)
#             conn.commit()
#             flash("Appointment successfully booked!")
#             return redirect(url_for('appointment_success'))
#         except mysql.connector.Error as err:
#             flash(f"Database Error: {err}")
#             return render_template('error.html', message="Unable to book your appointment. Please try again later.")
#         finally:
#             if conn.is_connected():
#                 cursor.close()
#                 conn.close()

#     return render_template('appointment.html')

# @app.route('/signup', methods=['GET','POST'])
# def signup():
#     return render_template('signup.html') 


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        mail = request.form['email']
        password = request.form['password']

        # Check if username or email already exists
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM signup WHERE username = %s OR mail = %s", (username, mail))
        existing_user = cursor.fetchone()
        
        if existing_user:
            return jsonify({'success': False, 'message': 'Username or Email already exists!'})

        # Hash password and save the new user
        # hashed_password = generate_password_hash(password, method='sha256')
        cursor.execute("INSERT INTO signup (username, mail, password) VALUES (%s, %s, %s)", (username, mail, password))
        mysql.connection.commit()

        cursor.close()

        return jsonify({'success': True, 'message': 'Registration successful! Please log in.'})

    return render_template('signup.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM signup WHERE username = %s", (username,))
        user = cursor.fetchone()
        if not user or user[2] != password:  # Assuming user[2] is password
            return jsonify({'success': False, 'message': 'Invalid username or password.'})
        cursor.close()
        session['username'] = username
        print(username)
        print(f"Logged in as: {session.get('username')}")
        return redirect(url_for('index'))  # This should redirect to index
    return render_template('signup.html')




##################################################################

@app.route('/category')
def category():
    category_type = request.args.get('type')
    
    if category_type is None:
        return render_template('category.html', hospitals=[])
    
    username = session.get('username')
    
    # Fetch hospitals and check if they're favorites for the logged-in user
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT h.hospital_id, h.hospital_name, h.timings, h.years_since_established, h.opcard_price,
               CASE WHEN f.hospital_id IS NOT NULL THEN TRUE ELSE FALSE END AS is_favorite
        FROM hospitals h
        LEFT JOIN favourites f ON h.hospital_id = f.hospital_id AND f.username = %s
        WHERE h.category = %s
    """, (username, category_type))
    
    hospitals = cur.fetchall()
    cur.close()
    
    return render_template('category.html', hospitals=hospitals, category=category_type)


@app.route('/referafriend')
def referafriend():
    return render_template('referAfriend.html')

@app.route('/team')
def team():
    return render_template('team.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/logout')
def logout():
    # Remove the username from the session
    session.pop('username', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))


def toggle_favorite(hospital_id, action):
    """Helper function to add or remove a hospital from favorites."""
    username = session['username']
    try:
        cur = mysql.connection.cursor()
        if action == 'add':
            cur.execute("SELECT * FROM favourites WHERE username = %s AND hospital_id = %s", (username, hospital_id))
            existing_fav = cur.fetchone()
            if existing_fav:
                # Remove from favorites
                cur.execute("DELETE FROM favourites WHERE username = %s AND hospital_id = %s", (username, hospital_id))
                flash("Hospital removed from your favorites.", "success")
            else:
                # Add to favorites
                cur.execute("INSERT INTO favourites (username, hospital_id) VALUES (%s, %s)", (username, hospital_id))
                flash("Hospital added to your favorites!", "success")
        elif action == 'remove':
            cur.execute("DELETE FROM favourites WHERE username = %s AND hospital_id = %s", (username, hospital_id))
            flash("Hospital removed from your favorites.", "success")
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        mysql.connection.rollback()  # Rollback the transaction in case of an error
        logging.error(f"Error in toggle_favorite: {e}")
        flash(f"An error occurred: {e}", "error")


@app.route('/add_favourite', methods=['POST'])
def add_favourite():
    if 'username' not in session:
        return jsonify({'success': False}), 401  # Unauthorized access

    hospital_id = int(request.form.get('hospital_id'))  # Convert to int
    toggle_favorite(hospital_id, 'add')
    
    return jsonify({'success': True})

@app.route('/remove_favourite', methods=['POST'])
def remove_favourite():
    if 'username' not in session:
        return jsonify({'success': False}), 401  # Unauthorized access

    hospital_id = int(request.form.get('hospital_id'))  # Convert to int
    toggle_favorite(hospital_id, 'remove')
    
    return jsonify({'success': True})


@app.route('/header')
def header():
    return render_template('header.html')

@app.route('/service')
def service():
    return render_template('service.html')



@app.route('/favourite')
def favourite():
    if 'username' not in session:
        flash("Please log in to view your favorites.", "info")
        return redirect(url_for('signup'))

    username = session['username']
    try:
        cur = mysql.connection.cursor()
        # cur.execute(""" 
        #     SELECT h.hospital_id, h.hospital_name, h.timings, h.years_since_established, h.opcard_price 
        #     FROM favourites f 
        #     JOIN hospitals h ON f.hospital_id = h.hospital_id
        #     WHERE f.username = %s 
        # """, (username,))
        # favourite_hospitals = cur.fetchall()
        # Inside your /favourite route or where you're fetching hospitals for the user:
        cur.execute("""
            SELECT h.hospital_id, h.hospital_name, h.timings, h.years_since_established, h.opcard_price,
                (CASE WHEN f.username IS NOT NULL THEN TRUE ELSE FALSE END) AS is_favorite
            FROM hospitals h
            LEFT JOIN favourites f ON f.hospital_id = h.hospital_id AND f.username = %s
        """, (username,))
        favourite_hospitals = cur.fetchall()

        cur.close()
    except Exception as e:
        logging.error(f"Error fetching favorites: {e}")
        flash(f"An error occurred: {e}", "error")
        favourite_hospitals = []

    return render_template('favourite.html', hospitals=favourite_hospitals)


#####################################################################################

# Set the folder where uploaded images will be saved
UPLOAD_FOLDER = 'static/uploads/hospitals'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Define the folder to store uploaded images
UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Check if user is logged in
        if 'username' not in session:
            flash("Please log in to register a hospital.", "info")
            return redirect(url_for('login'))

        try:
            # Extract form data
            hospital_name = request.form.get('hospitalName')
            status = request.form.get('status')
            patient_count = request.form.get('patientcount')
            description = request.form.get('description')
            experience = request.form.get('experience')
            address = request.form.get('address')
            timings = request.form.get('timings')
            price = request.form.get('price')
            open_days = request.form.get('opendays')

            # Extract latitude and longitude from form
            latitude = request.form.get('latitude') or 0.0  # Default to 0.0 if not provided
            longitude = request.form.get('longitude') or 0.0

            # Extract JSON for selected categories and diseases
            selectedCategoriesJson = request.form.get('selectedCategoriesJson')
            #selectedDiseasesJson = request.form.get('selectedDiseasesJson')

            # Convert JSON strings to lists
            selectedCategories = json.loads(selectedCategoriesJson) if selectedCategoriesJson else []
            #selectedDiseases = json.loads(selectedDiseasesJson) if selectedDiseasesJson else []

            # Handle the image upload
            image_file = request.files.get('upload_hospital_image')
            if image_file and allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image_file.save(file_path)
                image_url = 'uploads/' + filename
            else:
                image_url = None

            # Insert into the register table
            cur = mysql.connection.cursor()
            sql_register = """
            INSERT INTO register (
                hospital_name, availability_status, description, 
                number_of_patients_deals_with, years_of_experience, address, 
                hospital_timing, op_price, hospital_open_days, category, image_path
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(sql_register, (hospital_name, status, description, int(patient_count), 
                                       int(experience), address, timings, price, open_days, 
                                       ', '.join(selectedCategories), image_url))
            mysql.connection.commit()

            # Insert into the hospitals table
            register_id = cur.lastrowid
            hospital_code = "HOSP" + str(register_id)
            sql_hospitals = """
            INSERT INTO hospitals (
                register_id, hospital_name, hospital_code, category,
                timings, years_since_established,
                opcard_price, latitude, longitude, contact_number,
                website, upload_hospital_image
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(sql_hospitals, (register_id, hospital_name, hospital_code, 
                                        ', '.join(selectedCategories), 
                                        str(timings), str(experience), price, 
                                        float(latitude), float(longitude), None, None, image_url))
            mysql.connection.commit()

            cur.close()

            # Success message
            flash("Hospital registered successfully!", "success")
            return redirect(url_for('index'))

        except Exception as e:
            print(f"Error occurred: {e}")
            mysql.connection.rollback()
            flash(f"An error occurred: {e}", "error")
            return render_template('register.html')

    # Render the form if the request is GET
    return render_template('register.html')




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8520, debug=True)