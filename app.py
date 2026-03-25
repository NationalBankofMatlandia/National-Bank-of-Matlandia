import os
from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "BarjakMatlandije"

# SQLite path za Render
data_dir = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(data_dir, exist_ok=True)
db_path = os.path.join(data_dir, "database.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    passport_citizenship_number = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    is_admin = db.Column(db.Boolean, default=False)

class BankTreasury(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total_mjv = db.Column(db.Float, default=1000000)

with app.app_context():
    db.create_all()
    # Admin account (Guverner)
    admin = User.query.filter_by(username="Governor").first()
    if not admin:
        db.session.add(User(
            username="Governor",
            email="nationalbankofmatlandia@gmail.com",
            passport_citizenship_number="ADMIN",
            password=generate_password_hash("AlbanskaGolgota7906"),
            balance=0,
            is_admin=True
        ))
    if not BankTreasury.query.first():
        db.session.add(BankTreasury(total_mjv=1000000))
    db.session.commit()

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        username = request.form['username']
        email = request.form['email']
        passport = request.form['passport']
        password = request.form['password']

        if User.query.filter((User.username==username)|(User.email==email)|(User.passport_citizenship_number==passport)).first():
            return "User already exists!"

        hashed = generate_password_hash(password)
        new_user = User(username=username,email=email,passport_citizenship_number=passport,password=hashed,balance=0)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password,password):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            return redirect('/dashboard')
        return "Invalid credentials!"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/transfer', methods=['GET','POST'])
def transfer():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    if request.method=='POST':
        recipient_name = request.form['recipient']
        amount = float(request.form['amount'])
        recipient = User.query.filter_by(username=recipient_name).first()
        if not recipient:
            return "Recipient not found"
        if user.balance < amount:
            return "Insufficient funds"
        user.balance -= amount
        recipient.balance += amount
        db.session.commit()
        return "Transfer successful!"
    return render_template('transfer.html')

@app.route('/admin', methods=['GET','POST'])
def admin():
    if 'user_id' not in session:
        return redirect('/login')
    if not session.get('is_admin', False):
        return "Access denied!"
    treasury = BankTreasury.query.first()
    users = User.query.filter(User.is_admin==False).all()
    if request.method=='POST':
        action = request.form['action']
        amount = float(request.form.get('amount',0))
        if action=='mint':
            treasury.total_mjv += amount
            db.session.commit()
        elif action=='delete_user':
            uid = int(request.form.get('user_id'))
            user_to_delete = User.query.get(uid)
            db.session.delete(user_to_delete)
            db.session.commit()
    return render_template('admin.html', treasury=treasury, users=users)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)), debug=True)