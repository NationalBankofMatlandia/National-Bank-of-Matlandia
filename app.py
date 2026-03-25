from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey123'
data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')
os.makedirs(data_dir, exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(data_dir, 'database.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    passport_citizenship = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    balance = db.Column(db.Float, default=0)
    loans = db.relationship('Loan', backref='user', lazy=True)

class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='Guverner').first():
        admin = User(
            username='Guverner',
            email='nationalbankofmatlandia@gmail.com',
            passport_citizenship='00000000',
            password=generate_password_hash('AlbanskaGolgota7906'),
            balance=1000000  # Initial treasury MJV
        )
        db.session.add(admin)
        db.session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        passport = request.form['passport']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash("Username already exists!", "danger")
            return redirect('/register')

        hashed = generate_password_hash(password)
        user = User(username=username, email=email, passport_citizenship=passport, password=hashed, balance=0)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect('/admin' if user.username=='Guverner' else '/dashboard')
        flash("Invalid credentials!", "danger")
        return redirect('/login')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session['username']=='Guverner':
        return redirect('/login')
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        recipient_name = request.form['recipient']
        amount = float(request.form['amount'])
        if amount > user.balance:
            flash("Insufficient balance!", "danger")
            return redirect('/transfer')
        recipient = User.query.filter_by(username=recipient_name).first()
        if not recipient:
            flash("Recipient not found!", "danger")
            return redirect('/transfer')
        user.balance -= amount
        recipient.balance += amount
        db.session.commit()
        flash(f"Transferred {amount} MJV to {recipient.username}", "success")
        return redirect('/dashboard')
    return render_template('transfer.html', user=user)

@app.route('/loan', methods=['GET', 'POST'])
def loan():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        amount = float(request.form['amount'])
        loan = Loan(amount=amount, user_id=user.id)
        user.balance += amount
        db.session.add(loan)
        db.session.commit()
        flash(f"Loan of {amount} MJV granted.", "success")
        return redirect('/dashboard')
    return render_template('loan.html', user=user)

@app.route('/repay', methods=['GET', 'POST'])
def repay():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        amount = float(request.form['amount'])
        if amount > user.balance:
            flash("Insufficient balance!", "danger")
            return redirect('/repay')
        total_loans = sum(loan.amount for loan in user.loans)
        if amount > total_loans:
            amount = total_loans
        user.balance -= amount
        for loan in user.loans:
            if amount >= loan.amount:
                amount -= loan.amount
                db.session.delete(loan)
            else:
                loan.amount -= amount
                amount = 0
        db.session.commit()
        flash("Repayment successful.", "success")
        return redirect('/dashboard')
    return render_template('repay.html', user=user)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user_id' not in session or session['username'] != 'Guverner':
        return redirect('/login')
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        if 'mint' in request.form:
            amount = float(request.form['mint_amount'])
            user.balance += amount
            db.session.commit()
            flash(f"Minted {amount} MJV.", "success")
        elif 'burn' in request.form:
            amount = float(request.form['burn_amount'])
            if amount > user.balance:
                flash("Not enough MJV to burn!", "danger")
            else:
                user.balance -= amount
                db.session.commit()
                flash(f"Burned {amount} MJV.", "success")
    all_users = User.query.filter(User.username != 'Guverner').all()
    return render_template('admin.html', user=user, all_users=all_users)

if __name__ == '__main__':
    app.run(debug=True)