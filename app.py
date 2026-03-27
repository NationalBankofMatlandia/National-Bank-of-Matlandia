# Matlandia Digital Currency (MJV) - Backend (Render Ready)

from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'BarjakMatlandije')

# Database (persistent on Render)
DB_PATH = os.environ.get("DB_PATH", "/data/database.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    passport = db.Column(db.String(120), nullable=False)
    balance = db.Column(db.Float, default=0)
    debt = db.Column(db.Float, default=0)

class Bank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    treasury = db.Column(db.Float, default=1000000.0)  # initial MJV

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(80))
    receiver = db.Column(db.String(80))
    amount = db.Column(db.Float)

with app.app_context():
    db.create_all()
    if not Bank.query.first():
        bank = Bank()
        db.session.add(bank)
        db.session.commit()

# --- ROUTES ---
@app.route('/')
def home():
    return render_template("index.html")

@app.route('/register', methods=['POST'])
def register():
    data = request.form
    if User.query.filter_by(username=data['username']).first():
        return "Username already exists"

    bank = Bank.query.first()
    initial_mjv = 50
    if bank.treasury < initial_mjv:
        return "Not enough MJV in bank treasury to create new account"

    user = User(
        username=data['username'],
        email=data['email'],
        password=generate_password_hash(data['password']),
        passport=data['passport'],
        balance=initial_mjv
    )
    bank.treasury -= initial_mjv  # Oduzimamo iz trezora banke
    db.session.add(user)
    db.session.commit()
    return redirect('/')

@app.route('/login', methods=['POST'])
def login():
    data = request.form
    user = User.query.filter_by(username=data['username']).first()

    if user and check_password_hash(user.password, data['password']):
        session['user'] = user.username
        return redirect('/dashboard')

    if data['username'] == "Guverner" and data['password'] == "AlbanskaGolgota7906":
        session['admin'] = True
        return redirect('/admin')

    return "Invalid login"

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    user = User.query.filter_by(username=session['user']).first()
    bank = Bank.query.first()
    # Kurs MJV
    mjv_to_rsd = 10
    mjv_to_eur = 0.0095
    mjv_to_usd = 0.0098
    return render_template("dashboard.html", user=user, bank=bank,
                           mjv_to_rsd=mjv_to_rsd, mjv_to_eur=mjv_to_eur, mjv_to_usd=mjv_to_usd)

@app.route('/transfer', methods=['POST'])
def transfer():
    sender = User.query.filter_by(username=session['user']).first()
    receiver = User.query.filter_by(username=request.form['to']).first()
    amount = float(request.form['amount'])

    if not receiver:
        return "Receiver does not exist"
    if sender.balance < amount:
        return "Insufficient funds"

    sender.balance -= amount
    receiver.balance += amount
    db.session.add(Transaction(sender=sender.username, receiver=receiver.username, amount=amount))
    db.session.commit()
    return redirect('/dashboard')

@app.route('/loan', methods=['POST'])
def loan():
    user = User.query.filter_by(username=session['user']).first()
    amount = float(request.form['amount'])
    user.balance += amount
    user.debt += amount * 1.05  # 5% interest
    db.session.commit()
    return redirect('/dashboard')

@app.route('/repay', methods=['POST'])
def repay():
    user = User.query.filter_by(username=session['user']).first()
    amount = float(request.form['amount'])
    if user.balance < amount:
        return "Insufficient balance"
    if amount > user.debt:
        amount = user.debt
    user.balance -= amount
    user.debt -= amount
    db.session.commit()
    return redirect('/dashboard')

@app.route('/delete_account', methods=['POST'])
def delete_account():
    user = User.query.filter_by(username=session['user']).first()
    bank = Bank.query.first()
    confirm = request.form.get('confirm', 'no')
    if user.debt > 0:
        return "You must repay all debts before deleting your account"
    if confirm != 'yes':
        return "You must confirm deletion by checking the disclaimer"
    bank.treasury += user.balance
    db.session.delete(user)
    db.session.commit()
    session.clear()
    return redirect('/')

# --- ADMIN PANEL ---
@app.route('/admin')
def admin():
    if 'admin' not in session:
        return redirect('/')
    bank = Bank.query.first()
    users = User.query.all()
    return render_template("admin.html", bank=bank, users=users)

@app.route('/admin/create_mjv', methods=['POST'])
def admin_create_mjv():
    if 'admin' not in session:
        return redirect('/')
    bank = Bank.query.first()
    amount = float(request.form['amount'])
    bank.treasury += amount
    db.session.commit()
    return redirect('/admin')

@app.route('/admin/remove_mjv', methods=['POST'])
def admin_remove_mjv():
    if 'admin' not in session:
        return redirect('/')
    bank = Bank.query.first()
    amount = float(request.form['amount'])
    if bank.treasury >= amount:
        bank.treasury -= amount
        db.session.commit()
    return redirect('/admin')

@app.route('/admin/transfer', methods=['POST'])
def admin_transfer():
    if 'admin' not in session:
        return redirect('/')
    bank = Bank.query.first()
    recipient = User.query.filter_by(username=request.form['to']).first()
    amount = float(request.form['amount'])
    if recipient and bank.treasury >= amount:
        bank.treasury -= amount
        recipient.balance += amount
        db.session.commit()
    return redirect('/admin')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)