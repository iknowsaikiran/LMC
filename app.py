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
app.config['MYSQL_PASSWORD'] = 'Saty@136'
app.config['MYSQL_DB'] = 'hospital'

mysql = MySQL(app)






if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8520, debug=True)