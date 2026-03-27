from flask import Flask, render_template, request, redirect, session 
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "BarjakMatlandije"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    passport_citizenship = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    debt = db.Column(db.Float, default=0.0)

class Bank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    treasury = db.Column(db.Float, default=1000000.0)  # initial MJV

# --- INITIALIZE DB ---
with app.app_context():
    db.create_all()
    if not Bank.query.first():
        bank = Bank()
        db.session.add(bank)
        db.session.commit()

# --- ROUTES ---
@app.route('/')
def index():
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        passport_citizenship = request.form['passport_citizenship']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            return "User already exists!"
        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            passport_citizenship=passport_citizenship,
            password=hashed_password,
            balance=0.0
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # --- ADMIN LOGIN ---
        if username == "Guverner" and password == "AlbanskaGolgota7906":
            session['user'] = "Guverner"
            return redirect('/admin')

        # --- REGULAR USER LOGIN ---
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user'] = username
            return redirect('/dashboard')
        else:
            return "Invalid credentials!"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session or session['user'] == "Guverner":
        return redirect('/login')
    user = User.query.filter_by(username=session['user']).first()
    bank = Bank.query.first()
    mjv_to_rsd = 10
    mjv_to_eur = 0.0095
    mjv_to_usd = 0.0098
    return render_template('dashboard.html', user=user, bank=bank,
                           mjv_to_rsd=mjv_to_rsd, mjv_to_eur=mjv_to_eur, mjv_to_usd=mjv_to_usd)

@app.route('/loan', methods=['GET', 'POST'])
def loan():
    if 'user' not in session or session['user'] == "Guverner":
        return redirect('/login')
    user = User.query.filter_by(username=session['user']).first()
    if request.method == 'POST':
        amount = float(request.form['amount'])
        user.balance += amount
        user.debt += amount * 1.05  # 5% interest
        db.session.commit()
        return redirect('/dashboard')
    return render_template('loan.html', user=user)

@app.route('/repay', methods=['GET', 'POST'])
def repay():
    if 'user' not in session or session['user'] == "Guverner":
        return redirect('/login')
    user = User.query.filter_by(username=session['user']).first()
    if request.method == 'POST':
        amount = float(request.form['amount'])
        if amount > user.balance:
            return "Not enough balance to repay!"
        if amount > user.debt:
            amount = user.debt
        user.balance -= amount
        user.debt -= amount
        db.session.commit()
        return redirect('/dashboard')
    return render_template('repay.html', user=user)

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user' not in session or session['user'] == "Guverner":
        return redirect('/login')
    user = User.query.filter_by(username=session['user']).first()
    bank = Bank.query.first()
    if user.debt > 0:
        return "Cannot delete account with debt!"
    bank.treasury += user.balance
    db.session.delete(user)
    db.session.commit()
    session.pop('user', None)
    return redirect('/register')

@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if 'user' not in session or session['user'] == "Guverner":
        return redirect('/login')
    sender = User.query.filter_by(username=session['user']).first()
    if request.method == 'POST':
        recipient_name = request.form['recipient']
        amount = float(request.form['amount'])
        recipient = User.query.filter_by(username=recipient_name).first()
        if not recipient:
            return "Recipient not found!"
        if amount > sender.balance:
            return "Insufficient balance!"
        sender.balance -= amount
        recipient.balance += amount
        db.session.commit()
        return redirect('/dashboard')
    return render_template('transfer.html', user=sender)

# --- ADMIN / GUVERNER ---
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user' not in session or session['user'] != "Guverner":
        return redirect('/login')
    bank = Bank.query.first()
    users = User.query.all()
    if request.method == 'POST':
        if 'create_mjv' in request.form:
            bank.treasury += float(request.form['amount'])
        elif 'delete_user' in request.form:
            user_id = int(request.form['user_id'])
            u = User.query.get(user_id)
            if u.debt == 0:
                bank.treasury += u.balance
                db.session.delete(u)
        elif 'transfer_from_admin' in request.form:
            recipient_name = request.form['recipient']
            amount = float(request.form['amount'])
            recipient = User.query.filter_by(username=recipient_name).first()
            if recipient and amount <= bank.treasury:
                bank.treasury -= amount
                recipient.balance += amount
        db.session.commit()
        return redirect('/admin')
    return render_template('admin.html', bank=bank, users=users)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
