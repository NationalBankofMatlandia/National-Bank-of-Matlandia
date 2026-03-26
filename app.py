from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'BarjakMatlandije'

# DATABASE (RENDER POSTGRES)
db_url = os.environ.get("DATABASE_URL")

if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# MODELS
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120))
    passport = db.Column(db.String(50))
    password = db.Column(db.String(200))
    balance = db.Column(db.Float, default=0)

class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# INIT
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="Guverner").first():
        admin = User(
            username="Guverner",
            email="nationalbankofmatlandia@gmail.com",
            passport="ADMIN",
            password=generate_password_hash("AlbanskaGolgota7906"),
            balance=1000000
        )
        db.session.add(admin)
        db.session.commit()

# HOME
@app.route('/')
def index():
    return render_template('index.html')

# REGISTER
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        user = User(
            username=request.form['username'],
            email=request.form['email'],
            passport=request.form['passport'],
            password=generate_password_hash(request.form['password']),
            balance=0
        )
        db.session.add(user)
        db.session.commit()
        return redirect('/login')
    return render_template('register.html')

# LOGIN
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect('/admin' if user.username=="Guverner" else '/dashboard')
        flash("Wrong login")
    return render_template('login.html')

# DASHBOARD
@app.route('/dashboard')
def dashboard():
    user = User.query.get(session['user_id'])
    loans = Loan.query.filter_by(user_id=user.id).all()
    total_loans = sum(l.amount for l in loans)
    return render_template('dashboard.html', user=user, loans=total_loans)

# TRANSFER
@app.route('/transfer', methods=['GET','POST'])
def transfer():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        recipient = User.query.filter_by(username=request.form['recipient']).first()
        amount = float(request.form['amount'])

        if amount > user.balance:
            flash("No money")
        elif not recipient:
            flash("User not found")
        else:
            user.balance -= amount
            recipient.balance += amount
            db.session.commit()
            flash("Sent")

    return render_template('transfer.html')

# LOAN
@app.route('/loan', methods=['GET','POST'])
def loan():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        amount = float(request.form['amount'])
        loan = Loan(amount=amount, user_id=user.id)
        user.balance += amount
        db.session.add(loan)
        db.session.commit()
    return render_template('loan.html')

# REPAY
@app.route('/repay', methods=['GET','POST'])
def repay():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        amount = float(request.form['amount'])
        loans = Loan.query.filter_by(user_id=user.id).all()

        if amount > user.balance:
            flash("Not enough money")
        else:
            user.balance -= amount
            for l in loans:
                if amount >= l.amount:
                    amount -= l.amount
                    db.session.delete(l)
                else:
                    l.amount -= amount
                    break
            db.session.commit()

    return render_template('repay.html')

# DELETE ACCOUNT
@app.route('/delete_account', methods=['POST'])
def delete_account():
    user = User.query.get(session['user_id'])
    loans = Loan.query.filter_by(user_id=user.id).all()

    if sum(l.amount for l in loans) > 0:
        flash("Pay debts first")
        return redirect('/dashboard')

    treasury = User.query.filter_by(username="Guverner").first()
    treasury.balance += user.balance

    db.session.delete(user)
    db.session.commit()

    session.clear()
    return redirect('/')

# ADMIN
@app.route('/admin', methods=['GET','POST'])
def admin():
    if session.get('username') != "Guverner":
        return redirect('/login')

    user = User.query.get(session['user_id'])
    users = User.query.filter(User.username!="Guverner").all()

    if request.method == 'POST':

        # SEND MONEY
        if 'send' in request.form:
            recipient = User.query.filter_by(username=request.form['recipient']).first()
            amount = float(request.form['amount'])

            if recipient and amount <= user.balance:
                user.balance -= amount
                recipient.balance += amount
                db.session.commit()

        # MINT
        if 'mint' in request.form:
            user.balance += float(request.form['mint'])

        # BURN
        if 'burn' in request.form:
            amount = float(request.form['burn'])
            if amount <= user.balance:
                user.balance -= amount

        db.session.commit()

    return render_template('admin.html', user=user, users=users)

if __name__ == "__main__":
    app.run()