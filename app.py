from flask import Flask, render_template, request, redirect, url_for, session, flash, json, jsonify
from flask_mysqldb import MySQL
from math import radians, cos, sin, asin, sqrt
from flask_mysqldb import MySQL
import logging
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'


# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'varma'
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

@app.route('/', methods=['GET','POST'])
def index():
    if request.method == 'POST':
        # Handle POST request (when the geolocation data is sent)
        data = request.get_json()
        print("Received data:", data)  # Add this line to verify if the data is being received
        user_latitude = float(data.get('latitude'))
        user_longitude = float(data.get('longitude'))

        # Debugging: print the received values
        print(f"Received Latitude: {user_latitude}")
        print(f"Received Longitude: {user_longitude}")

        cur = mysql.connection.cursor()
        cur.execute("SELECT hospital_id,hospital_name, timings, years_since_established, opcard_price, latitude, longitude FROM hospitals")
        hospitals = cur.fetchall()
        print(hospitals)

        nearby_hospitals = []
        for hospital in hospitals:
            hospital_id,hospital_name, timings, years_since_established, opcard_price, lat, lon = hospital
            distance = haversine(user_latitude, user_longitude, lat, lon)
            if distance <= 5:
                nearby_hospitals.append({
                    'hospital_id': hospital_id,
                    'hospital_name': hospital_name,
                    'timings': timings,
                    'years_since_established': years_since_established,
                    'opcard_price': opcard_price,
                    'distance': round(distance, 2)
                })

        print("Nearby hospitals:", nearby_hospitals)

        return jsonify(nearby_hospitals)  # Return hospitals as JSON to the frontend    
    
    # If GET request (when the page is first loaded)
    return render_template('index.html', hospitals=[])
    # try:
    #     # Connect to the database
    #     cur = mysql.connection.cursor()

    #     # Fetch data from the 'hospitals' table
    #     query = """
    #         SELECT * FROM hospitals
    #     """
    #     cur.execute(query)
    #     hospitals = cur.fetchall()

    #     # Close the database connection
    #     cur.close()

    #     # Render the index.html template with the fetched hospital data
    #     return render_template('index.html', hospitals=hospitals)

    # except Exception as e:
    #     print(f"An error occurred: {e}")
    #     return "An error occurred while fetching hospital data. {e}"

@app.route('/about_us')
def about_us():
    return render_template('about.html')

@app.route('/appointment')
def appointment():
    return render_template('appointment.html') 



@app.route('/referafriend')
def referafriend():
    return render_template('referAfriend.html')

@app.route('/team')
def team():
    return render_template('team.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')


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



@app.route('/favourite')
def favourite():
    if 'username' not in session:
        flash("Please log in to view your favorites.", "info")
        return redirect(url_for('signuplogin'))

    username = session['username']
    try:
        cur = mysql.connection.cursor()
        cur.execute(""" 
            SELECT h.hospital_id, h.hospital_name, h.timings, h.years_since_established, h.opcard_price 
            FROM favourites f 
            JOIN hospitals h ON f.hospital_id = h.hospital_id
            WHERE f.username = %s 
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