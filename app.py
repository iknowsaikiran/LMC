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
app.config['MYSQL_PASSWORD'] = 'root123'
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

@app.route('/')
def home():    
    return render_template('index.html')


@app.route('/', methods=['GET', 'POST'])
def index():
    # Retrieve user ID from session if available (optional)
    user_id = session.get('username', None)  # Get the logged-in user's username, or None if not logged in
    print(f"Logged in user_id (from session): {user_id}")  # Debugging

    username = None
    if user_id:
        try:
            # Fetch the username from the signup table
            cur = mysql.connection.cursor()
            cur.execute("SELECT username FROM signup WHERE username = %s", (user_id,))
            result = cur.fetchone()
            cur.close()

            if result:
                username = result[0]  # Extract the username string from the result tuple
                print(f"Fetched username: {username}")  # Debugging
        except Exception as e:
            print(f"Error fetching username: {e}")

    if request.method == 'POST':
        try:
            # Handle POST request (when the geolocation data is sent)
            data = request.get_json()  # Parse the JSON data
            print("Received data:", data)  # Debugging to verify received data

            user_latitude = float(data.get('latitude'))
            user_longitude = float(data.get('longitude'))

            print(f"User Latitude: {user_latitude}, User Longitude: {user_longitude}")  # Debugging

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
                        WHEN %s IS NOT NULL AND f.username IS NOT NULL THEN TRUE 
                        ELSE FALSE 
                    END AS is_favorite
                FROM hospitals h
                LEFT JOIN favourites f 
                ON h.hospital_id = f.hospital_id AND f.username = %s
            """, (username, username))
            hospitals = cur.fetchall()
            cur.close()

            # Compute nearby hospitals
            nearby_hospitals = []
            for hospital in hospitals:
                hospital_id, hospital_name, timings, years_since_established, opcard_price, lat, lon, is_favorite = hospital
                distance = haversine(user_latitude, user_longitude, lat, lon)
                if distance <= 5:  # Check if the hospital is within 5 km
                    nearby_hospitals.append({
                        'hospital_id': hospital_id,
                        'hospital_name': hospital_name,
                        'timings': timings,
                        'years_since_established': years_since_established,
                        'opcard_price': opcard_price,
                        'distance': round(distance, 2),  # Round distance to 2 decimal places
                        'is_favorite': is_favorite
                    })

            print("Nearby hospitals:", nearby_hospitals)  # Debugging

            # Return nearby hospitals as JSON response
            return jsonify(nearby_hospitals)

        except Exception as e:
            print(f"Error processing request: {e}")
            return "Internal Server Error", 500

    # If GET request (when the page is first loaded)
    return render_template('index.html', hospitals=[])


@app.route('/about_us')
def about_us():
    return render_template('about.html')
@app.route('/hospitaldb')
def hospitaldb():
    return render_template('hospitaldb.html')





# @app.route('/appointment', methods=['GET', 'POST'])
# def appointment():
#     if request.method == 'POST':
#         # Get form data
#         first_name = request.form.get('firstName')
#         last_name = request.form.get('lastName')
#         email = request.form.get('email')
#         phone_number = request.form.get('number')
#         gender = request.form.get('gender')
#         department = request.form.get('department')
#         appointmentDate = request.form.get('appointmentDate')
#         appointmentTime = request.form.get('appointmentTime')
#         purpose = request.form.get('comments')
        
#         # Get the logged-in user's username from session
#         username = session.get('username')  
        
#         if not username:  # Check if user is logged in
#             flash("You must be logged in to make an appointment.")
#             return redirect(url_for('login'))  # Redirect to login page if not logged in

#         #Validate form inputs
#         if not first_name or not last_name or not phone_number:
#             flash("All fields are required!")
#             return redirect(url_for('appointment'))

#         #Insert into database
#         try:
#             cur = mysql.connection.cursor()
#             query = """
#                 INSERT INTO hospital_appointments 
#                 (first_name, last_name, email, phone_number, gender, department, appointment_date, appointment_time, purpose, username) 
#                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#             """
#             values = (first_name, last_name, email, phone_number, gender, department, appointmentDate, appointmentTime, purpose, username)
#             cur.execute(query, values)  # Execute the query
#             mysql.connection.commit()  # Commit the changes
#             cur.close()  # Close the cursor
#             flash("Appointment successfully booked!")
#             return redirect(url_for('appointment_success'))
#         except Exception as e:
#             flash(f"An error occurred: {str(e)}")
#             return redirect(url_for('appointment'))

#     # Handle GET request
#     return render_template('appointment.html')


@app.route('/appointment', methods=['GET', 'POST'])
def appointment():
    if 'username' not in session:
        return '''
            <script type="text/javascript">
                alert("Please log in to book appointment.");
                window.location.href = "/";  // Redirect to the desired page after alert
            </script>
        '''
    if request.method == 'POST':
        # Get form data
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        email = request.form.get('email')
        phone_number = request.form.get('number')
        gender = request.form.get('gender')
        department = request.form.get('department')
        appointment_date = request.form.get('appointmentDate')
        appointment_time = request.form.get('appointmentTime')
        purpose = request.form.get('comments')

        # Get the logged-in user's username from session
        username = session.get('username')

        if not username:  # Check if user is logged in
            flash("You must be logged in to make an appointment.")
            return redirect(url_for('login'))

        # Validate form inputs
        if not all([first_name, last_name, phone_number, department, appointment_date]):
            flash("All fields are required!")
            return redirect(request.url)

        # Insert into database
        try:
            cur = mysql.connection.cursor()
            query = """
                INSERT INTO hospital_appointments 
                (first_name, last_name, email, phone_number, gender, department, appointment_date, appointment_time, purpose, username) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (first_name, last_name, email, phone_number, gender, department, appointment_date, appointment_time, purpose, username)
            cur.execute(query, values)
            mysql.connection.commit()
            cur.close()
            flash("Appointment successfully booked!")
            return redirect(url_for('appointment_success'))
        except Exception as e:
            flash(f"An error occurred: {str(e)}")
            return redirect(request.url)

    # Handle GET request
    hospital_id = request.args.get('hospital_id', type=int)
    print("Hospital ID:", hospital_id)  # Debug statement
    print("Type of hospital_id:", type(hospital_id))  # Check type of hospital_id
    hospital = None
    if hospital_id:
        print(f"Hospital ID is valid: {hospital_id}")  # Debug statement
        try:
            cur = mysql.connection.cursor()
            query = "SELECT * FROM hospitals WHERE hospital_id = %s"
            cur.execute(query, (hospital_id,))
            hospital = cur.fetchone()
            print("Fetched hospital data:", hospital) 
            cur.close()
        except Exception as e:
            flash(f"An error occurred while fetching hospital details: {str(e)}")
    
    return render_template('appointment.html', hospital=hospital)





##########$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$4
@app.route('/category', methods=['GET', 'POST'])
def category():
    if 'username' not in session:
        return '''
            <script type="text/javascript">
                alert("Please log in to view categories.");
                window.location.href = "/";  // Redirect to the desired page after alert
            </script>
        '''

    # For GET requests, you simply retrieve the category type from the URL query parameters
    if request.method == 'GET':
        category_type = request.args.get('type')

        # Get the username from the session
        username = session.get('username')
        cur = mysql.connection.cursor()

        # Construct the query to fetch hospitals based on category
        query = """
            SELECT h.hospital_id, h.hospital_name, h.timings, h.years_since_established, 
                   h.opcard_price, h.category, h.latitude, 
                   h.longitude, 
                   CASE WHEN f.hospital_id IS NOT NULL THEN TRUE ELSE FALSE END AS is_favorite
            FROM hospitals h
            LEFT JOIN favourites f ON h.hospital_id = f.hospital_id AND f.username = %s
            WHERE 1=1
        """
        
        params = [username]
        
        if category_type:
            query += " AND h.latitude IS NOT NULL AND h.longitude IS NOT NULL"
        
        cur.execute(query, tuple(params))
        hospitals = cur.fetchall()
        cur.close()
        print(hospitals)

        # Return the category page with hospitals (without needing the location for now)
        return render_template('category.html', hospitals=hospitals, category=category_type)

    # For POST requests, process the latitude and longitude data
    if request.method == 'POST':
        data = request.get_json()
        user_latitude = float(data.get('latitude'))
        user_longitude = float(data.get('longitude'))

        print(f"User Latitude: {user_latitude}, User Longitude: {user_longitude}")  # Debugging

        # Get the username from the session
        username = session.get('username')
        cur = mysql.connection.cursor()

        # Construct the query to fetch hospitals based on category and location
        query = """
            SELECT h.hospital_id, h.hospital_name, h.timings, h.years_since_established, 
                   h.opcard_price, h.category, h.latitude, 
                   h.longitude, 
                   CASE WHEN f.hospital_id IS NOT NULL THEN TRUE ELSE FALSE END AS is_favorite
            FROM hospitals h
            LEFT JOIN favourites f ON h.hospital_id = f.hospital_id AND f.username = %s
            WHERE 1=1
        """
        
        params = [username]

        category_type = data.get('category_type')  # Get category type from POST data
        print(category_type)
        if category_type:
            
            # Split the category_type string by commas
            categories = [cat.strip() for cat in category_type.split(',')]
        
            # Add the category conditions to the query
            query += " AND ("  # Start a group for category conditions
            for idx, category in enumerate(categories):
                if idx > 0:
                    query += " OR "
                query += "h.category LIKE %s"
                params.append(f"%{category}%")  # Add wildcard for LIKE match
            query += ")"  # Close the group for category conditions
        else:            
            query += " AND h.latitude IS NOT NULL AND h.longitude IS NOT NULL"

        
        cur.execute(query, tuple(params))
        hospitals = cur.fetchall()
        cur.close()

        # Filter hospitals based on proximity (using Haversine)
        nearby_hospitals = []
        for hospital in hospitals:
            hospital_id, hospital_name, timings, years_since_established, opcard_price, category, lat, lon, is_favorite = hospital
            distance = haversine(user_latitude, user_longitude, lat, lon)
            
            if distance <= 5:
                nearby_hospitals.append({
                    'hospital_id': hospital_id,
                    'hospital_name': hospital_name,
                    'timings': timings,
                    'years_since_established': years_since_established,
                    'opcard_price': opcard_price,
                    'distance': round(distance, 2),
                    'is_favorite': is_favorite,
                    'category': category
                })
        print(nearby_hospitals)

        # Return JSON response for POST requests
        return jsonify(nearby_hospitals)

    return "Invalid request method.", 405








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
        # print(username)
        # print(f"Logged in as: {session.get('username')}")
        return redirect(url_for('index'))  # This should redirect to index
    return render_template('signup.html')


# @app.route('/signup_login', methods=['GET', 'POST'])
# def signup_login():
#     if request.method == 'POST':
#         # Check if it's a signup or login attempt by checking which form field is present
#         if 'signup' in request.form:  # This indicates the signup form was submitted
#             username = request.form['username']
#             mail = request.form['email']
#             password = request.form['password']

#             # Check if username or email already exists
#             cursor = mysql.connection.cursor()
#             cursor.execute("SELECT * FROM signup WHERE username = %s OR mail = %s", (username, mail))
#             existing_user = cursor.fetchone()

#             if existing_user:
#                 return jsonify({'success': False, 'message': 'Username or Email already exists!'})

#             # Insert the new user into the database
#             cursor.execute("INSERT INTO signup (username, mail, password) VALUES (%s, %s, %s)", (username, mail, password))
#             mysql.connection.commit()

#             cursor.close()

#             return jsonify({'success': True, 'message': 'Registration successful! Please log in.'})

#         elif 'login' in request.form:  # This indicates the login form was submitted
#             username = request.form['username']
#             password = request.form['password']

#             # Find the user by username
#             cursor = mysql.connection.cursor()
#             cursor.execute("SELECT * FROM signup WHERE username = %s", (username,))
#             user = cursor.fetchone()

#             if not user or user[2] != password:  # user[2] is assumed to be the password
#                 return jsonify({'success': False, 'message': 'Invalid username or password.'})

#             cursor.close()

#             # Store the username in session
#             session['username'] = username  # Set the session variable

#             # Debug: Print the session to verify it's set
#             print(f"Logged in as: {session.get('username')}")

#             # Redirect to the index page after successful login
#             return redirect(url_for('index'))

#     # If it's a GET request, render the signup/login page
#     return render_template('signup.html')





@app.route('/referafriend')
def referafriend():
    return render_template('referAfriend.html')

@app.route('/team')
def team():
    return render_template('team.html')
# @app.route('/logout')
# def logout():
#     # Remove the username from the session
#     session.pop('username', None)
#     flash("You have been logged out.", "info")
#     return redirect(url_for('index'))


#logout after 15 minutes
from datetime import timedelta
app.permanent_session_lifetime = timedelta(minutes=5)
@app.before_request
def make_session_permanent():
    """Make session permanent for each request"""
    session.permanent = True
@app.route('/logout')
def logout():
    # Remove the username from the session
    session.pop('username', None)
    flash("You have been logged out due to inactivity.", "info")
    return redirect(url_for('index'))
####################################


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

@app.route('/dashboard')
def dashboard():
    try:
        username = session.get('username') 
        
        cur = mysql.connection.cursor()
        # Fetch data from the hospital_appointments table based on the username
        cur.execute("""
            SELECT * FROM hospital_appointments
            WHERE username = %s
            """, (username,))

        appointments = cur.fetchall()
        
        
        # Fetch the count of favourites
        cur.execute("""
            SELECT COUNT(*) FROM favourites
            WHERE username = %s
        """, (username,))
        favourite_count = cur.fetchone()[0]  # Get the count value
        cur.close()
        print(f"appointments are {appointments}")
    except Exception as e:
        logging.error(f"Error fetching hospital appointments: {e}")
        print(f"Error fetching hospital appointments: {e}")
        flash(f"An error occurred: {e}", "error")
        print(e)
        appointments = []
        favourite_count = 0  # Default count in case of error
    
    return render_template('dashboardindex.html', appointments=appointments, username=username, count=favourite_count)
 

@app.route('/viewcard')
def viewcard():
    return render_template('viewcard.html')


@app.route('/favourite')
def favourite():
    if 'username' not in session:
        return '''
            <script type="text/javascript">
                alert("Please log in to view your favorites.");
                window.location.href = "/";  // Redirect to the desired page after alert
            </script>
        '''
        #flash("Please log in to view your favorites.", "info")
        #return redirect(url_for('signup'))

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
            SELECT h.hospital_id, h.hospital_name, h.timings, h.years_since_established, h.opcard_price
            FROM hospitals h
            JOIN favourites f ON f.hospital_id = h.hospital_id AND f.username = %s
        """, (username,))
        favourite_hospitals = cur.fetchall()
        print(favourite_hospitals)
        cur.close()
    except Exception as e:
        logging.error(f"Error fetching favorites: {e}")
        flash(f"An error occurred: {e}", "error")
        favourite_hospitals = []

    return render_template('favourites.html', hospitals=favourite_hospitals)


#####################################################################################

# Set the folder where uploaded images will be savedzzz
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
    
    
@app.route('/hospitalregister')
def hospitalregister():
    return render_template('hospital_registration.html')

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