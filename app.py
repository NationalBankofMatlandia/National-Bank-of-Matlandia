from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'BarjakMatlandije')

DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    DATABASE_URL = "sqlite:///database.db"

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

### MODELS ###
class Bank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    treasury = db.Column(db.Float, default=1000000.0)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    passport = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    balance = db.Column(db.Float, default=0)
    debt = db.Column(db.Float, default=0)

### INIT DB ###
with app.app_context():
    db.create_all()
    if not Bank.query.first():
        db.session.add(Bank())
        db.session.commit()

### ROUTES ###
@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    elif 'admin' in session:
        return redirect(url_for('admin'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        passport = request.form['passport']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            return "Username already exists!"
        user = User(
            username=username,
            email=email,
            passport=passport,
            password=generate_password_hash(password),
            balance=50
        )
        bank = Bank.query.first()
        bank.treasury -= 50
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Admin login
        if username == "Guverner" and password == "AlbanskaGolgota7906":
            session['admin'] = True
            return redirect(url_for('admin'))

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user'] = username
            return redirect(url_for('dashboard'))
        return "Invalid login"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session['user']).first()
    bank = Bank.query.first()
    return render_template('dashboard.html', user=user, bank=bank,
                           mjv_to_rsd=10, mjv_to_eur=0.0095, mjv_to_usd=0.0098)

# Loan, Repay, Transfer
@app.route('/loan', methods=['POST'])
def loan():
    user = User.query.filter_by(username=session['user']).first()
    amount = float(request.form['amount'])
    user.balance += amount
    user.debt += amount
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/repay', methods=['POST'])
def repay():
    user = User.query.filter_by(username=session['user']).first()
    amount = float(request.form['amount'])
    if amount > user.balance:
        return "Insufficient balance!"
    if amount > user.debt:
        amount = user.debt
    user.balance -= amount
    user.debt -= amount
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/transfer', methods=['POST'])
def transfer():
    sender = User.query.filter_by(username=session['user']).first()
    recipient = User.query.filter_by(username=request.form['recipient']).first()
    amount = float(request.form['amount'])
    if not recipient:
        return "Recipient not found!"
    if sender.balance < amount:
        return "Insufficient balance!"
    sender.balance -= amount
    recipient.balance += amount
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete_account', methods=['POST'])
def delete_account():
    user = User.query.filter_by(username=session['user']).first()
    if user.debt > 0:
        return "Repay all debts before deleting!"
    if request.form.get('confirm') != 'yes':
        return "You must confirm deletion!"
    bank = Bank.query.first()
    bank.treasury += user.balance
    db.session.delete(user)
    db.session.commit()
    session.clear()
    return redirect(url_for('register'))

# Admin Panel
@app.route('/admin')
def admin():
    if 'admin' not in session:
        return redirect(url_for('login'))
    bank = Bank.query.first()
    users = User.query.all()
    return render_template('admin.html', users=users, bank=bank)

@app.route('/admin/add_mjv', methods=['POST'])
def add_mjv():
    bank = Bank.query.first()
    amount = float(request.form['amount'])
    bank.treasury += amount
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/remove_mjv', methods=['POST'])
def remove_mjv():
    bank = Bank.query.first()
    amount = float(request.form['amount'])
    if amount <= bank.treasury:
        bank.treasury -= amount
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/transfer_to_user', methods=['POST'])
def admin_transfer():
    bank = Bank.query.first()
    recipient = User.query.filter_by(username=request.form['recipient']).first()
    amount = float(request.form['amount'])
    if recipient and amount <= bank.treasury:
        recipient.balance += amount
        bank.treasury -= amount
        db.session.commit()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
