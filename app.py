from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Baza podataka
data_dir = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(data_dir, exist_ok=True)
db_path = os.path.join(data_dir, "database.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Valuta
CURRENCY_NAME = "Matlandian Jovla"
CURRENCY_ABBR = "MJV"

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    passport_citizenship_number = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    loan = db.Column(db.Float, default=0.0)

db.create_all()

# Create Guverner if not exists
guverner = User.query.filter_by(username="Guverner").first()
if not guverner:
    guverner = User(
        username="Guverner",
        email="guverner@matlandia.bank",
        passport_citizenship_number="ADMIN001",
        password=generate_password_hash("AlbanskaGolgota7906"),
        balance=1000000.0,
    )
    db.session.add(guverner)
    db.session.commit()

# Routes
@app.route("/")
def index():
    return render_template("index.html", currency=CURRENCY_ABBR)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form['username']
        email = request.form['email']
        passport = request.form['passport_citizenship_number']
        password = request.form['password']

        if User.query.filter((User.username==username)|(User.email==email)).first():
            return "User or Email already exists!"

        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            passport_citizenship_number=passport,
            password=hashed_password,
            balance=0.0
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect("/login")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect("/dashboard")
        return "Invalid credentials!"
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect("/login")
    user = User.query.get(session['user_id'])
    return render_template("dashboard.html", user=user, currency=CURRENCY_ABBR)

@app.route("/transfer", methods=["GET", "POST"])
def transfer():
    if 'user_id' not in session:
        return redirect("/login")
    user = User.query.get(session['user_id'])
    if request.method == "POST":
        recipient_name = request.form['recipient']
        amount = float(request.form['amount'])
        recipient = User.query.filter_by(username=recipient_name).first()
        if not recipient:
            return "Recipient not found!"
        if amount <= 0 or user.balance < amount:
            return "Insufficient funds!"
        user.balance -= amount
        recipient.balance += amount
        db.session.commit()
        return redirect("/dashboard")
    return render_template("transfer.html", user=user, currency=CURRENCY_ABBR)

@app.route("/loan", methods=["GET", "POST"])
def loan():
    if 'user_id' not in session:
        return redirect("/login")
    user = User.query.get(session['user_id'])
    if request.method == "POST":
        amount = float(request.form['amount'])
        if amount <= 0:
            return "Invalid amount!"
        user.balance += amount
        user.loan += amount
        db.session.commit()
        return redirect("/dashboard")
    return render_template("loan.html", user=user, currency=CURRENCY_ABBR)

@app.route("/repay", methods=["GET", "POST"])
def repay():
    if 'user_id' not in session:
        return redirect("/login")
    user = User.query.get(session['user_id'])
    if request.method == "POST":
        amount = float(request.form['amount'])
        if amount <= 0 or user.balance < amount:
            return "Cannot repay: insufficient funds!"
        repay_amount = min(amount, user.loan)
        user.balance -= repay_amount
        user.loan -= repay_amount
        db.session.commit()
        return redirect("/dashboard")
    return render_template("repay.html", user=user, currency=CURRENCY_ABBR)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if 'user_id' not in session:
        return redirect("/login")
    user = User.query.get(session['user_id'])
    if user.username != "Guverner":
        return "Access denied!"
    if request.method == "POST":
        action = request.form['action']
        target_username = request.form.get('target_username')
        amount = float(request.form.get('amount', 0))
        target_user = User.query.filter_by(username=target_username).first()
        if action == "add" and target_user:
            target_user.balance += amount
            db.session.commit()
        elif action == "remove" and target_user:
            if target_user.balance >= amount:
                target_user.balance -= amount
                db.session.commit()
            else:
                return "Insufficient funds!"
        elif action == "create_mjv":
            guverner.balance += amount
            db.session.commit()
        elif action == "delete_user" and target_user:
            db.session.delete(target_user)
            db.session.commit()
    users = User.query.all()
    return render_template("admin.html", users=users, user=user, currency=CURRENCY_ABBR)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)