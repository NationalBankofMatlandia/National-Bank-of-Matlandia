from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'BarjakMatlandije')

# SQLite persistent database (Render free plan)
DB_PATH = os.environ.get("DB_PATH", "database.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

### MODELS ###
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    passport = db.Column(db.String(120), nullable=False)
    balance = db.Column(db.Float, default=50)
    debt = db.Column(db.Float, default=0)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(80))
    receiver = db.Column(db.String(80))
    amount = db.Column(db.Float)

class Bank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    treasury = db.Column(db.Float, default=1000000.0)  # initial MJV

with app.app_context():
    db.create_all()
    if not Bank.query.first():
        bank = Bank()
        db.session.add(bank)
        db.session.commit()

### ROUTES ###
@app.route('/')
def home():
    return render_template("index.html")

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        data = request.form
        if User.query.filter_by(username=data['username']).first():
            return "Username already exists"
        user = User(
            username=data['username'],
            email=data['email'],
            password=generate_password_hash(data['password']),
            passport=data['passport']
        )
        db.session.add(user)
        db.session.commit()
        return redirect('/login')
    return render_template("register.html")

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        data = request.form
        user = User.query.filter_by(username=data['username']).first()

        # Admin login
        if data['username'] == "Guverner" and data['password'] == "AlbanskaGolgota7906":
            session['admin'] = True
            return redirect('/admin')

        if user and check_password_hash(user.password, data['password']):
            session['user'] = user.username
            return redirect('/dashboard')
        return "Invalid login"
    return render_template("login.html")

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
    mjv_to_rsd = 10
    mjv_to_eur = 0.0095
    mjv_to_usd = 0.0098
    return render_template("dashboard.html", user=user, bank=bank,
                           mjv_to_rsd=mjv_to_rsd, mjv_to_eur=mjv_to_eur, mjv_to_usd=mjv_to_usd)

@app.route('/transfer', methods=['GET','POST'])
def transfer():
    if 'user' not in session:
        return redirect('/')
    sender = User.query.filter_by(username=session['user']).first()
    if request.method == 'POST':
        recipient = User.query.filter_by(username=request.form['to']).first()
        amount = float(request.form['amount'])
        if not recipient:
            return "Receiver does not exist"
        if sender.balance < amount:
            return "Insufficient balance"
        sender.balance -= amount
        recipient.balance += amount
        db.session.add(Transaction(sender=sender.username, receiver=recipient.username, amount=amount))
        db.session.commit()
        return redirect('/dashboard')
    return render_template("transfer.html", user=sender)

@app.route('/loan', methods=['GET','POST'])
def loan():
    if 'user' not in session:
        return redirect('/')
    user = User.query.filter_by(username=session['user']).first()
    if request.method == 'POST':
        amount = float(request.form['amount'])
        user.balance += amount
        user.debt += amount
        db.session.commit()
        return redirect('/dashboard')
    return render_template("loan.html", user=user)

@app.route('/repay', methods=['GET','POST'])
def repay():
    if 'user' not in session:
        return redirect('/')
    user = User.query.filter_by(username=session['user']).first()
    if request.method == 'POST':
        amount = float(request.form['amount'])
        if user.balance < amount:
            return "Insufficient balance"
        if amount > user.debt:
            amount = user.debt
        user.balance -= amount
        user.debt -= amount
        db.session.commit()
        return redirect('/dashboard')
    return render_template("repay.html", user=user)

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user' not in session:
        return redirect('/')
    user = User.query.filter_by(username=session['user']).first()
    bank = Bank.query.first()
    if user.debt > 0:
        return "Cannot delete account with debt"
    bank.treasury += user.balance
    db.session.delete(user)
    db.session.commit()
    session.clear()
    return redirect('/')

### ADMIN PANEL ###
@app.route('/admin')
def admin():
    if 'admin' not in session:
        return redirect('/')
    bank = Bank.query.first()
    users = User.query.all()
    return render_template("admin.html", users=users, bank=bank)

@app.route('/admin/add_money', methods=['POST'])
def add_money():
    if 'admin' not in session:
        return redirect('/')
    user = User.query.filter_by(username=request.form['user']).first()
    amount = float(request.form['amount'])
    user.balance += amount
    db.session.commit()
    return redirect('/admin')

@app.route('/admin/remove_money', methods=['POST'])
def remove_money():
    if 'admin' not in session:
        return redirect('/')
    user = User.query.filter_by(username=request.form['user']).first()
    amount = float(request.form['amount'])
    if user.balance >= amount:
        user.balance -= amount
        db.session.commit()
    return redirect('/admin')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))