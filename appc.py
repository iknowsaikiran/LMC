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
app.config['MYSQL_PASSWORD'] = '12345' 
app.config['MYSQL_DB'] = 'hospital'

mysql = MySQL(app)

# Function to calculate distance between two coordinates using Haversine formula
def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat1 - lat2
    a = sin(dlat / 2) * 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) * 2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r


@app.route('/', methods=['GET', 'POST'])
def home():
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
        cur.execute("SELECT hospital_name, timings, years_since_established, opcard_price, latitude, longitude FROM hospitals")
        hospitals = cur.fetchall()
        print(hospitals)

        nearby_hospitals = []
        for hospital in hospitals:
            hospital_name, timings, years_since_established, opcard_price, lat, lon = hospital
            distance = haversine(user_latitude, user_longitude, lat, lon)
            if distance <= 5:
                nearby_hospitals.append({
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
            selectedDiseasesJson = request.form.get('selectedDiseasesJson')

            # Convert JSON strings to lists
            selectedCategories = json.loads(selectedCategoriesJson) if selectedCategoriesJson else []
            selectedDiseases = json.loads(selectedDiseasesJson) if selectedDiseasesJson else []

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
                hospital_timing, op_price, hospital_open_days, category, diseases, upload_hospital_image
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(sql_register, (hospital_name, status, description, int(patient_count), 
                                       int(experience), address, timings, price, open_days, 
                                       ', '.join(selectedCategories), ', '.join(selectedDiseases), image_url))
            mysql.connection.commit()

            # Insert into the hospitals table
            register_id = cur.lastrowid
            hospital_code = "HOSP" + str(register_id)
            sql_hospitals = """
            INSERT INTO hospitals (
                register_id, hospital_name, hospital_code, hospital_type,
                specialities, timings, years_since_established,
                opcard_price, latitude, longitude, contact_number,
                website, upload_hospital_image
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(sql_hospitals, (register_id, hospital_name, hospital_code, 
                                        ', '.join(selectedCategories), ', '.join(selectedDiseases), 
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




@app.route('/success')
def success():
    return "Hospital registered successfully!"





@app.route('/nearby_hospitals')
def get_nearby_hospitals():
    try:
        cur = mysql.connection.cursor()
        sql = "SELECT hospital_name, years_of_experience, distance, op_price, image_url FROM hospital.register WHERE distance < 5"
        cur.execute(sql)
        hospitals = cur.fetchall()
        cur.close()

        # Pass hospitals data (including image_url) to the frontend
        return jsonify([{
            "hospital_name": hospital[0],
            "years_since_established": hospital[1],
            "distance": hospital[2],
            "opcard_price": hospital[3],
            "image_url": hospital[4]  # Include image URL
        } for hospital in hospitals])
    except Exception as e:
        flash(f"Error retrieving hospitals: {e}", "error")
        return jsonify([])





@app.route('/category')
def category():
    # Get the category type from the URL parameter
    category_type = request.args.get('type')
    
    # If no category type is provided, default to an empty list
    if category_type is None:
        return render_template('category.html', hospitals=[])

    # Fetch hospitals for the selected category from the database
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT h.hospital_id, h.hospital_name, h.timings, h.years_since_established, 
               h.opcard_price, r.availability_status, r.description
        FROM hospitals AS h
        JOIN register AS r ON h.register_id = r.sno
        WHERE r.category = %s
    """, (category_type,))
    hospitals = cur.fetchall()
    cur.close()

    # If no hospitals found for the category, inform the user
    if not hospitals:
        flash("No hospitals found for this category.", "info")

    # Render the category page with the filtered hospitals
    return render_template('bookappointment.html', hospitals=hospitals, category=category_type)


@app.route('/book/<int:slno>')
def book_appointment(slno):
    # Placeholder for booking logic
    return f"Appointment booked for hospital with ID {slno}"


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
        return jsonify({'success': False, 'message': "Please log in to add favorites."})
    
    hospital_id = int(request.form.get('hospital_id'))  # Convert to int
    toggle_favorite(hospital_id, 'add')
    
    return jsonify({'success': True, 'message': "Hospital added to your favorites!"})


@app.route('/remove_favourite', methods=['POST'])
def remove_favourite():
    if 'username' not in session:
        return jsonify({'success': False, 'message': "Please log in to remove favorites."}), 401

    hospital_id = int(request.form.get('hospital_id'))  # Convert to int
    toggle_favorite(hospital_id, 'remove')
    
    return jsonify({'success': True, 'action': 'remove', 'message': "Hospital removed from your favorites."})

@app.route('/favourite')
def favourite():
    if 'username' not in session:
        flash("Please log in to view your favorites.", "info")
        return redirect(url_for('login'))

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




@app.route('/about_us')
def about_us():
    return render_template('about-us.html')

# Setup logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/bookappointment', methods=['GET', 'POST'])
def bookappointment():
    if request.method == 'POST':
        try:
            if 'firstName' in request.form:
                # New Patient Form
                first_name = request.form.get('firstName')
                last_name = request.form.get('lastName')
                phone_number = request.form.get('number')
                address = request.form.get('address')
                reason = request.form.get('reason')
                appointment_date = request.form.get('appointmentDate')

                cur = mysql.connection.cursor()
                cur.execute("SELECT * FROM newpatients WHERE phone_number = %s", (phone_number,))
                patient = cur.fetchone()

                if patient:
                    cur.close()
                    return jsonify({"error": "Patient already exists with this phone number."}), 400

                cur.execute("INSERT INTO newpatients (first_name, last_name, phone_number, address, reason, appointment_date) VALUES (%s, %s, %s, %s, %s, %s)", 
                            (first_name, last_name, phone_number, address, reason, appointment_date))
                mysql.connection.commit()
                cur.close()
                return redirect(url_for('signup'))  # Redirect to signup page
            
            elif 'opName' in request.form:
                # Existing Patient Form
                op_name = request.form.get('opName') 
                op_phone = request.form.get('opPhone')
                op_number = request.form.get('opNumber')
                appointment_date = request.form.get('appointmentDate')
                reason = request.form.get('reason')

                cur = mysql.connection.cursor()
                cur.execute("SELECT * FROM existingpatients WHERE op_number = %s AND phone_number = %s", (op_number, op_phone))
                existing_patient = cur.fetchone()
                
                if existing_patient:
                    mysql.connection.commit()
                    cur.close()
                    return redirect(url_for('login'))  # Redirect to login page
                else:
                    cur.close()
                    return jsonify({"error": "Patient does not exist with these details."}), 400

        except Exception as e:
            app.logger.error(f"Error processing request: {e}")
            return jsonify({"error": "Internal server error. Please try again later."}), 500

    return render_template('bookappointment.html')




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form data
        username = request.form['username']
        password = request.form['password']

        # Check if the user exists in the database
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM signup WHERE username = %s AND password = %s", (username, password))
        user = cur.fetchone()
        cur.close()

        if user:
            # User exists, start a session
            session['username'] = username
            return redirect(url_for('index'))  # Redirect to index.html page
        else:
            # User does not exist or password is incorrect
            flash('Incorrect username or password', 'error')
            return redirect(url_for('login'))
    
    # If the request method is GET, render the login page
    return render_template('login.html')

    
from werkzeug.security import generate_password_hash, check_password_hash

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        print("Form Data:", request.form)  # Debug print to show form data
        
        try:
            username = request.form['username']
            mail = request.form['mail']
            password = request.form['password']
        except KeyError as e:
            return f"Missing key: {e}", 400

        # Check if the username already exists
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM signup WHERE username = %s", (username,))
        user = cur.fetchone()

        if user:
            cur.close()
            flash("Username already exists! Please choose a different one.", "error")
            return redirect(url_for('signup'))

        # Directly use the password without hashing (not recommended for production)
        cur.execute("INSERT INTO signup (username, mail, password) VALUES (%s, %s, %s)", (username, mail, password))
        mysql.connection.commit()
        cur.close()

        # Show success message and redirect to the login page
        flash(f"Congratulations {username}, your account has been created!", "success")
        return redirect(url_for('login'))

    # If the request method is GET, just render the signup page
    return render_template('signup.html')


@app.route('/logout')
def logout():
    # Remove the username from the session
    session.pop('username', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

# Route to serve the call.html page

@app.route('/call')
def call():
    return render_template('call.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

# Route for search results
@app.route('/search', methods=['POST', 'GET'])
def search():
    if request.method == 'POST':
        query = request.form['query'].lower()
    else:
        query = request.args.get('query').lower()  # For GET method, as your form might use GET

    # Map search queries to specific routes
    if 'category' in query:
        return redirect(url_for('category'))
    elif 'about' in query or 'about us' in query:
        return redirect(url_for('about_us'))
    elif 'profile' in query or 'my profile' in query:
        return redirect(url_for('profile'))
    elif 'favourites' in query or 'favorites' in query:
        return redirect(url_for('favourites'))
    else:
        return "No results found."
 


@app.route('/profile')
def profile():
    # Check if the user is logged in
    if 'username' not in session:
        flash("Please log in to view your profile.", "info")
        return redirect(url_for('login'))
    
    username = session['username']
    
    # Fetch user email
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT mail FROM signup WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        
        user_email = user[0] if user else ""
    except Exception as e:
        flash(f"An error occurred: {e}", "error")
        user_email = ""
    
    # Fetch favorite hospitals
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT h.hospital_name, h.timings, h.years_since_established, h.opcard_price
            FROM favourites f
            JOIN hospitals h ON f.hospital_id = h.slno
            WHERE f.username = %s
        """, (username,))
        favourite_hospitals = cur.fetchall()
        cur.close()
    except Exception as e:
        flash(f"An error occurred: {e}", "error")
        favourite_hospitals = []

    return render_template('profile.html', user_email=user_email, hospitals=favourite_hospitals)


@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'username' not in session:
        flash("Please log in to update your profile.", "info")
        return redirect(url_for('login'))

    username = session['username']
    email = request.form.get('email')
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    try:
        cur = mysql.connection.cursor()

        # Check if the current password is correct
        cur.execute("SELECT password FROM signup WHERE username = %s", (username,))
        stored_password = cur.fetchone()

        if stored_password and stored_password[0] == current_password:
            if new_password == confirm_password:
                cur.execute("UPDATE signup SET mail = %s, password = %s WHERE username = %s", (email, new_password, username))
                mysql.connection.commit()
                flash("Profile updated successfully!", "success")
            else:
                flash("New passwords do not match.", "error")
        else:
            flash("Current password is incorrect.", "error")

        cur.close()
    except Exception as e:
        mysql.connection.rollback()
        flash(f"An error occurred: {e}", "error")

    return redirect(url_for('profile'))





# function displayHospitals(hospitals) {
#             const hospitalList = document.querySelector('.hospital-list');
#             hospitalList.innerHTML = ''; // Clear the list before adding new items

#             if (!hospitals || hospitals.length === 0) {
#                 hospitalList.innerHTML = '<p>No nearby hospitals found within 5km of your location.</p>';
#             } else {
#                 hospitals.forEach(hospital => {
#                     const hospitalItem = `
#             <div class="blog-slider">
#                 <div class="blog-slider__wrp swiper-wrapper">
#                     <div class="blog-slider__item swiper-slide d-flex">
#                         <div class="blog-slider__img col-lg-3">
#                             <img src="/static/img/apollo.jfif" alt="Hospital Image">
#                         </div>
#                         <div class="blog-slider__content col-lg-3" style="margin-left:20px">
#                             <h3 class="blog-slider__title">${hospital.hospital_name}</h3>
#                             <p class="availability-status" style="color: green;">Available Now</p>
#                             <p class="timings"><strong>Timings:</strong> ${hospital.timings}</p>
#                             <p>${hospital.years_since_established} years in healthcare</p>
#                             <p><i class="fas fa-map-marker-alt"></i> ${hospital.address}</p>
#                             <p>Op price: ₹${hospital.opcard_price}</p>
#                             <p class="current-op-count">
#                                 <strong>Current OP count:</strong> 
#                                 <span onclick="alert('Please login to see the current OP count.')">**</span>
#                             </p>
#                         </div>
#                         <div class="button-group col-lg-4 btnt">
#                             <ul class="btns d-flex" style="list-style-type:none">
#                                     <li >
#                                         <form action="/toggle_favourite" method="POST" style="display:inline;">
#                                             <input type="hidden" name="hospital_id" value="{{ hospitals[0] }}">
#                                             <button type="button" id="toggle-favorite" class="btn toggle-favourite" aria-label="{{ 'Remove from favorites' if hospitals[5] else 'Add to favorites' }}">
#                                                 <i class="fas fa-heart {{ 'active' if hospitals[5] else '' }}"></i>
#                                             </button>
#                                         </form>
#                                     </li>
#                                     <li style="padding-top:10px">
#                                         <a href="#" class="view-card" style="margin-left:10px">View</a>
#                                     </li>
#                             </ul>
#                             <div class="callbuttons col-lg-4">
#                                 <button class="btn p-2 call-btn" data-hospital-id="${hospital.hospital_id}">Call</button>
#                             <button class="btn p-2 chat-btn" data-hospital-id="${hospital.hospital_id}">Chat</button>
#                             </div>
#                             <button class="btn p-2 mt-10" data-bs-toggle="modal" data-bs-target="#appointmentModal${hospital.hospital_id}">Book Appointment</button>
#                         </div>
#                     </div>
#                 </div>
#             </div>
#             <!-- Appointment Modal -->
#             <div class="modal fade" id="appointmentModal${hospital.hospital_id}" tabindex="-1" aria-labelledby="appointmentModalLabel${hospital.hospital_id}" aria-hidden="true">
#                 <div class="modal-dialog modal-lg">
#                     <div class="modal-content">
#                         <div class="modal-header">
#                             <h5 class="modal-title" id="appointmentModalLabel${hospital.hospital_id}">Book Appointment - ${hospital.hospital_name}</h5>
#                             <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
#                         </div>
#                         <div class="modal-body">
#                             <div class="text-center">
#                                 <button class="btn btn-primary m-2 new-patient-btn" data-hospital-id="${hospital.hospital_id}" onclick="navigateToNewPage()">New Patient</button>
#                                 <button class="btn btn-primary m-2 existing-patient-btn" data-hospital-id="${hospital.hospital_id}">Already a Patient</button>
#                             </div>
#                             <form id="newPatientForm${hospital.hospital_id}" class="new-patient-form" style="display: none;" method="POST" action="/bookappointment">
#                                       <input type="hidden" name="appointmentDate" value="" id="appointmentDateHidden${hospital.hospital_id}">
#                                       <label for="firstName">First Name:</label>
#                                       <input type="text" name="firstName" placeholder="First name" class="form-control" required>
  
#                                       <label for="lastName">Last Name:</label>
#                                       <input type="text" name="lastName" placeholder="Last name" class="form-control" required>
  
#                                       <label for="number">Phone Number:</label>
#                                       <input type="text" name="number" placeholder="Phone number" class="form-control" required>
  
#                                       <label for="address">Address:</label>
#                                       <input type="text" name="address" placeholder="Your address" class="form-control" required>
  
#                                       <label for="reason">Reason for your Appointment:</label>
#                                       <input type="text" name="reason" placeholder="Reason for appointment" class="form-control" required>
  
#                                       <label for="appointmentDate">Select Date:</label>
#                                       <input type="date" name="appointmentDate" class="form-control" required>
  
#                                       <button type="submit" class="btn btn-success mt-3">Book Appointment</button>
#                                   </form>
#                                  <form id="existingPatientForm${hospital.hospital_id}" class="existing-patient-form" style="display: none;" method="POST" action="/bookappointment">
#                                       <input type="hidden" name="appointmentDate" value="" id="appointmentDateHidden${hospital.hospital_id}">
#                                       <label for="opName">Name on OP Card:</label>
#                                       <input type="text" name="opName" placeholder="Name on OP card" class="form-control" required>
  
#                                       <label for="opPhone">Phone Number on OP Card:</label>
#                                       <input type="text" name="opPhone" placeholder="Phone number on OP card" class="form-control" required>
  
#                                       <label for="opNumber">OP Number:</label>
#                                       <input type="text" name="opNumber" placeholder="OP number" class="form-control" required>
  
#                                       <button type="submit" class="btn btn-success mt-3">Book Appointment</button>
#                                   </form>
#                         </div>
#                     </div>
#                 </div>
#             </div>`;
#                     function navigateToNewPage() {
#                         window.location.href = "appointments.html"; // Redirect to the new page
#                     }

#                     hospitalList.innerHTML += hospitalItem;
#                 });

#                 // Add event listeners for Call and Chat buttons to display "coming soon" modals
#                 document.querySelectorAll('.call-btn, .chat-btn').forEach(button => {
#                     button.addEventListener('click', (e) => {
#                         e.preventDefault();
#                         alert('This feature is coming soon.');
#                     });
#                 });

#                 // Toggle between New Patient and Existing Patient forms in the modal
#                 hospitalList.addEventListener('click', function (event) {
#                     const target = event.target;
#                     const hospitalId = target.dataset.hospitalId;
#                     if (target.classList.contains('new-patient-btn')) {
#                         document.getElementById(`newPatientForm${hospitalId}`).style.display = 'block';
#                         document.getElementById(`existingPatientForm${hospitalId}`).style.display = 'none';
#                     }
#                     if (target.classList.contains('existing-patient-btn')) {
#                         document.getElementById(`newPatientForm${hospitalId}`).style.display = 'none';
#                         document.getElementById(`existingPatientForm${hospitalId}`).style.display = 'block';
#                     }
#                 });
#             }
#         }


@app.route('/appointment', methods=['GET', 'POST'])
def appointment():
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
    hospital = None
    if hospital_id:
        try:
            cur = mysql.connection.cursor()
            query = "SELECT * FROM hospitals WHERE id = %s"
            cur.execute(query, (hospital_id,))
            hospital = cur.fetchone()
            cur.close()
        except Exception as e:
            flash(f"An error occurred while fetching hospital details: {str(e)}")
    
    return render_template('appointment.html', hospital=hospital)




if __name__ == '_main_':
    app.run(host='0.0.0.0', port=8520, debug=True)