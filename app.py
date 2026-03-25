from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = "matlandia_secret"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, "database.db")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= MODELS =================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    email = db.Column(db.String(100))
    passport = db.Column(db.String(100))
    balance = db.Column(db.Integer, default=0)
    loan = db.Column(db.Integer, default=0)

class Bank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    treasury = db.Column(db.Integer, default=1000000)

# ================= INIT =================

with app.app_context():
    db.create_all()
    if not Bank.query.first():
        db.session.add(Bank(treasury=1000000))
        db.session.commit()

# ================= ADMIN =================

ADMIN_USERNAME = "Guverner"
ADMIN_PASSWORD = "AlbanskaGolgota7906"

# ================= ROUTES =================

@app.route("/")
def home():
    return render_template("index.html")

# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = User(
            username=request.form["username"],
            password=request.form["password"],
            email=request.form["email"],
            passport=request.form["passport"]
        )
        db.session.add(user)
        db.session.commit()
        return redirect("/login")

    return render_template("register.html")

# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")

        user = User.query.filter_by(username=u, password=p).first()
        if user:
            session["user"] = user.id
            return redirect("/dashboard")

    return render_template("login.html")

# DASHBOARD
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    user = User.query.get(session["user"])
    return render_template("dashboard.html", user=user)

# TRANSFER
@app.route("/transfer", methods=["POST"])
def transfer():
    sender = User.query.get(session["user"])
    receiver = User.query.filter_by(username=request.form["to"]).first()
    amount = int(request.form["amount"])

    if not receiver:
        return "User not found"

    if sender.balance < amount:
        return "Insufficient funds"

    sender.balance -= amount
    receiver.balance += amount

    db.session.commit()
    return redirect("/dashboard")

# LOAN
@app.route("/loan", methods=["POST"])
def loan():
    user = User.query.get(session["user"])
    amount = int(request.form["amount"])

    interest = int(amount * 0.1)

    user.balance += amount
    user.loan += amount + interest

    db.session.commit()
    return redirect("/dashboard")

# REPAY
@app.route("/repay", methods=["POST"])
def repay():
    user = User.query.get(session["user"])
    amount = int(request.form["amount"])

    if user.balance < amount:
        return "Not enough money"

    user.balance -= amount
    user.loan -= amount

    if user.loan < 0:
        user.loan = 0

    db.session.commit()
    return redirect("/dashboard")

# ================= ADMIN =================

@app.route("/admin")
def admin():
    if "admin" not in session:
        return "Access denied"

    users = User.query.all()
    bank = Bank.query.first()

    return render_template("admin.html", users=users, bank=bank)

# SEND MONEY
@app.route("/admin/send", methods=["POST"])
def admin_send():
    if "admin" not in session:
        return "Access denied"

    user = User.query.filter_by(username=request.form["user"]).first()
    amount = int(request.form["amount"])

    if user:
        user.balance += amount
        db.session.commit()

    return redirect("/admin")

# MINT
@app.route("/admin/mint", methods=["POST"])
def mint():
    bank = Bank.query.first()
    bank.treasury += int(request.form["amount"])
    db.session.commit()
    return redirect("/admin")

# BURN
@app.route("/admin/burn", methods=["POST"])
def burn():
    bank = Bank.query.first()
    amount = int(request.form["amount"])

    if bank.treasury >= amount:
        bank.treasury -= amount
        db.session.commit()

    return redirect("/admin")

# ================= RUN =================

if __name__ == "__main__":
    app.run(debug=True)
