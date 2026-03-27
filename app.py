from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "BarjakMatlandije"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Hardkodovan admin
ADMIN_USERNAME = "Guverner"
ADMIN_PASSWORD = "AlbanskaGolgota7906"

# Kurs MJV
MJV_TO_RSD = 10
MJV_TO_EUR = 0.0095
MJV_TO_USD = 0.01

# Baza
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    passport_number = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    balance = db.Column(db.Float, default=0)
    debt = db.Column(db.Float, default=0)

class BankTreasury(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total_mjv = db.Column(db.Float, default=1000000)  # početni MJV u trezoru

db.create_all()
if not BankTreasury.query.first():
    db.session.add(BankTreasury(total_mjv=1000000))
    db.session.commit()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        passport_number = request.form['passport_number']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("User already exists!", "error")
            return redirect('/register')
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email,
                        passport_number=passport_number, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("Account created! You can now log in.", "success")
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect('/admin')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect('/dashboard')
        flash("Invalid credentials", "error")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    treasury = BankTreasury.query.first()
    return render_template('dashboard.html', user=user, treasury=treasury,
                           mjv_to_rsd=MJV_TO_RSD, mjv_to_eur=MJV_TO_EUR, mjv_to_usd=MJV_TO_USD)

@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        recipient_username = request.form['recipient']
        amount = float(request.form['amount'])
        recipient = User.query.filter_by(username=recipient_username).first()
        if not recipient:
            flash("Recipient does not exist.", "error")
            return redirect('/transfer')
        if user.balance < amount:
            flash("Insufficient balance.", "error")
            return redirect('/transfer')
        user.balance -= amount
        recipient.balance += amount
        db.session.commit()
        flash("Transfer successful!", "success")
        return redirect('/dashboard')
    return render_template('transfer.html', user=user)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin' not in session:
        return redirect('/login')
    treasury = BankTreasury.query.first()
    users = User.query.all()
    if request.method == 'POST':
        action = request.form['action']
        target_username = request.form.get('target_user')
        amount = float(request.form.get('amount', 0))
        target_user = User.query.filter_by(username=target_username).first() if target_username else None
        if action == "add_mjv":
            treasury.total_mjv += amount
            db.session.commit()
            flash(f"Added {amount} MJV to treasury.", "success")
        elif action == "send_mjv" and target_user:
            if treasury.total_mjv >= amount:
                treasury.total_mjv -= amount
                target_user.balance += amount
                db.session.commit()
                flash(f"Sent {amount} MJV to {target_user.username}.", "success")
            else:
                flash("Not enough MJV in treasury.", "error")
        elif action == "delete_user" and target_user:
            if target_user.debt == 0:
                treasury.total_mjv += target_user.balance
                db.session.delete(target_user)
                db.session.commit()
                flash(f"Deleted user {target_user.username}.", "success")
            else:
                flash("Cannot delete user with debt.", "error")
    return render_template('admin.html', treasury=treasury, users=users)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
