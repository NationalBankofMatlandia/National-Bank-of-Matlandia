import os
from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'BarjakMatlandije')

database_url = os.environ.get('DATABASE_URL')
if not database_url:
    raise ValueError("DATABASE_URL environment variable not set!")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    passport_citizenship = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    debt = db.Column(db.Float, default=0.0)

class Bank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    treasury = db.Column(db.Float, default=1000000.0)  # Initial MJV in bank

with app.app_context():
    db.create_all()
    if not Bank.query.first():
        bank = Bank()
        db.session.add(bank)
        db.session.commit()

# --- ROUTES ---
@app.route('/')
def home():
    return redirect('/login')

# REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    bank = Bank.query.first()
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        passport_citizenship = request.form['passport_citizenship']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            return "User already exists!"

        if bank.treasury < 50:
            return "Bank treasury does not have enough MJV to allocate."

        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            passport_citizenship=passport_citizenship,
            password=hashed_password,
            balance=50  # Initial MJV
        )
        bank.treasury -= 50  # Deduct from bank treasury
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')
    return render_template('register.html')

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Admin login
        if username == "Guverner" and password == "AlbanskaGolgota7906":
            session['admin'] = True
            return redirect('/admin')

        # User login
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user'] = username
            return redirect('/dashboard')

        return "Invalid login"
    return render_template('login.html')

# LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# DASHBOARD
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    user = User.query.filter_by(username=session['user']).first()
    bank = Bank.query.first()
    # MJV exchange rates
    mjv_to_rsd = 10
    mjv_to_eur = 0.0095
    mjv_to_usd = 0.0098
    return render_template('dashboard.html', user=user, bank=bank,
                           mjv_to_rsd=mjv_to_rsd, mjv_to_eur=mjv_to_eur, mjv_to_usd=mjv_to_usd)

# LOAN
@app.route('/loan', methods=['POST'])
def loan():
    if 'user' not in session:
        return redirect('/login')
    user = User.query.filter_by(username=session['user']).first()
    amount = float(request.form['amount'])
    user.balance += amount
    user.debt += amount
    db.session.commit()
    return redirect('/dashboard')

# REPAY
@app.route('/repay', methods=['POST'])
def repay():
    if 'user' not in session:
        return redirect('/login')
    user = User.query.filter_by(username=session['user']).first()
    amount = float(request.form['amount'])
    if amount > user.balance:
        return "Insufficient balance!"
    if amount > user.debt:
        amount = user.debt
    user.balance -= amount
    user.debt -= amount
    db.session.commit()
    return redirect('/dashboard')

# TRANSFER
@app.route('/transfer', methods=['POST'])
def transfer():
    if 'user' not in session:
        return redirect('/login')
    sender = User.query.filter_by(username=session['user']).first()
    recipient_name = request.form['recipient']
    amount = float(request.form['amount'])
    recipient = User.query.filter_by(username=recipient_name).first()
    if not recipient:
        return "Recipient not found!"
    if sender.balance < amount:
        return "Insufficient balance!"
    sender.balance -= amount
    recipient.balance += amount
    db.session.commit()
    return redirect('/dashboard')

# DELETE ACCOUNT
@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user' not in session:
        return redirect('/login')
    user = User.query.filter_by(username=session['user']).first()
    bank = Bank.query.first()
    confirmation = request.form.get('confirm_delete', 'no')
    if user.debt > 0:
        return "Cannot delete account with debt!"
    if confirmation != 'yes':
        return "You must confirm deletion!"
    bank.treasury += user.balance
    db.session.delete(user)
    db.session.commit()
    session.pop('user', None)
    return redirect('/register')

# --- ADMIN PANEL ---
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin' not in session:
        return redirect('/login')
    bank = Bank.query.first()
    users = User.query.all()
    if request.method == 'POST':
        # Add MJV to bank treasury
        if 'add_mjv' in request.form:
            amount = float(request.form['amount'])
            bank.treasury += amount
        # Remove MJV from bank treasury
        elif 'remove_mjv' in request.form:
            amount = float(request.form['amount'])
            if bank.treasury >= amount:
                bank.treasury -= amount
        # Transfer MJV from bank to user
        elif 'transfer_mjv' in request.form:
            recipient_name = request.form['recipient']
            amount = float(request.form['amount'])
            recipient = User.query.filter_by(username=recipient_name).first()
            if recipient and bank.treasury >= amount:
                bank.treasury -= amount
                recipient.balance += amount
        db.session.commit()
        return redirect('/admin')
    return render_template('admin.html', bank=bank, users=users)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
