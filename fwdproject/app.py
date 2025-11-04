import MySQLdb
import numpy as np
import pandas as pd
from flask import Flask, request, render_template, redirect, flash, session, url_for
import pickle
import re

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Load ML models
drug = pickle.load(open('models/drug.pkl', 'rb'))
dosage = pickle.load(open('models/dosage.pkl', 'rb'))
side = pickle.load(open('models/side.pkl', 'rb'))

# MySQL Database Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Supraja@14'
app.config['MYSQL_DB'] = 'drug'


# MySQL Configuration
mysql = MySQLdb.connect(
    host="localhost",
    user="root",
    password="Supraja@14",
    database="drug"
)
mysql.autocommit(True)

# Example condition encoding (must match what was used during training)
condition_encoding = {
    'Depression': 0,
    'Lymphocytic Colitis': 1,
    'Urinary Tract Infection': 2,
    'Weight Loss': 3,
    'Birth Control': 4,
    'Vaginal Yeast Infection': 5,
    'Narcolepsy': 6,
    'Insomnia': 7,
    'Bipolar Disorder': 8,
    'Hyperhidrosis': 9,
    'Panic Disorder': 10,
    'Rosacea': 11,
    'Bowel Preparation': 12,
    'Constipation, Drug Induced': 13,
    'Diabetes, Type 2': 14,
    'Pain': 15,
    'Alcohol Dependence': 16,
    'Emergency Contraception': 17,
    'Major Depressive Disorder': 18,
    'Anxiety': 19,
    'Acne': 20,
    'Cough and Nasal Congestion': 21,
    'Pain and Constipation, Drug Induced': 22,
    'Acne and Pain': 23,
    'Cough, Cold and Fever': 24,
    'Fever': 25,

}

# Routes

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        return render_template('dashboard.html', username=session['username'])
    return redirect(url_for('login'))


@app.route('/profile')
def profile():
    if 'loggedin' in session:
        cursor = mysql.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM people WHERE username = %s', (session['username'],))
        account = cursor.fetchone()
        return render_template('profile.html', account=account)
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully!", "info")
    return redirect(url_for('index'))


@app.route('/tracker')
def tracker():
    if 'loggedin' in session:
        return render_template('tracker.html')
    flash("Please login first to access the tracker!", "warning")
    return redirect(url_for('login'))


@app.route('/pharmacies')
def pharmacies():
    if 'loggedin' in session:
        return render_template('pharmacies.html')
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM people WHERE username = %s AND password = %s', (username, password))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['username'] = account['username']
            return redirect(url_for('dashboard'))
        flash('Incorrect username or password!', 'error')
    return render_template('login.html', msg=msg)


@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        age = request.form['age']

        reg = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%#?&])[A-Za-z\d@$!#%?&]{6,10}$"
        pattern = re.compile(reg)

        cursor = mysql.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM people WHERE username = %s', (username,))
        account = cursor.fetchone()

        if account:
            msg = 'Account already exists!'
            flash(msg, 'error')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
            flash(msg, 'error')
        elif not re.match(r'^[A-Za-z0-9]+$', username):
            msg = 'Username must contain only letters and numbers!'
            flash(msg, 'error')
        elif not pattern.match(password):
            msg = 'Password must be 6-10 chars with special chars, numbers, and uppercase!'
            flash(msg, 'error')
        else:
            try:
                cursor.execute('INSERT INTO people (username, password, email, age) VALUES (%s, %s, %s, %s)',
                               (username, password, email, age))
                mysql.commit()
                flash('You have successfully registered! Please login.', 'success')
                return redirect(url_for('login'))
            except MySQLdb.Error as e:
                print(f"MySQL Error: {e}")
            finally:
                cursor.close()
    return render_template('register.html', msg=msg)


@app.route('/prediction', methods=['GET', 'POST'])
def prediction():
    if not session.get('loggedin'):
        return render_template('prediction.html')

    if request.method == 'POST':
        try:
            bp = request.form['bloodpresssure']
            sugar = request.form['sugar']
            temp = float(request.form['Temperature'])
            age = float(request.form['age'])
            condition = request.form['Condition']

            # Convert categorical inputs
            bp_val = 0 if bp == 'Normal' else 1
            sugar_val = 0 if sugar == 'Normal' else 1
            condition_val = condition_encoding.get(condition, -1)  # Fallback -1 for unknowns

            if condition_val == -1:
                return render_template('prediction.html', prediction_text="Error: Unknown condition selected.")

            input_features = np.array([[bp_val, sugar_val, temp, age, condition_val]])

            drug_pred = drug.predict(input_features)[0]
            dosage_pred = round(dosage.predict(input_features)[0], 2)
            side_pred = side.predict(input_features)[0]

            label = f"Drug: {drug_pred}, Dosage: {dosage_pred} mg, Side-effects: {side_pred}"
            return render_template('prediction.html', prediction_text=label)
        except Exception as e:
            return render_template('prediction.html', prediction_text=f"Error: {str(e)}")

    return render_template('prediction.html')


if __name__ == "__main__":
    app.run(debug=True)
