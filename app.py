# imports
import utils

from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField
from wtforms.validators import InputRequired, Length, ValidationError, NumberRange
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeSerializer
import json
import datetime

# init
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = '3ICljySKGNH-4LYIf4eAKQ'
app.config['REMEMBER_COOKIE_DURATION'] = datetime.timedelta(days=31)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# user login init
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = "strong"

serializer = URLSafeSerializer(app.secret_key)

# Family Group Association Table
family_group = db.Table('family_group',
                        db.Column('parent_id', db.Integer, db.ForeignKey('parent.id')),
                        db.Column('child_id', db.Integer, db.ForeignKey('child.id'))
                        )


# Parent table
class Parent(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(40), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(80), nullable=True)
    wallet = db.Column(db.String(800), unique=True, nullable=False)

    children = db.relationship('Child', secondary=family_group, backref='parents')

    session_token = db.Column(db.String(100), unique=True)

    def __str__(self):
        return f"Name: {self.name} | Email: {self.email} | Token: {self.session_token}"

    def get_id(self):
        return self.session_token


# Child Table
class Child(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(40), unique=False, nullable=False)
    name = db.Column(db.String, unique=False, nullable=True)
    password = db.Column(db.String(80), nullable=False)
    wallet = db.Column(db.String, unique=True, nullable=False)

    session_token = db.Column(db.String(100), unique=True)

    def get_id(self):
        return self.session_token


# Transactions Table
class Transactions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_address = db.Column(db.String(42), nullable=False)
    to_address = db.Column(db.String(42), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Integer, nullable=False)
    token_name = db.Column(db.String(20), nullable=False, default="StakeUp")
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow(), nullable=False)


@login_manager.user_loader
def load_user(session_token):
    return Parent.query.filter_by(session_token=session_token).first() or Child.query.filter_by(
        session_token=session_token).first()


# Create Account Form
class CreateForm(FlaskForm):
    email = StringField(validators=[InputRequired(), Length(min=4, max=40)], render_kw={"placeholder": "Email"})
    password = PasswordField(validators=[InputRequired(), Length(min=6, max=20)], render_kw={"placeholder": "Password"})
    name = StringField(validators=[InputRequired(), Length(min=3, max=20)], render_kw={"placeholder": "Name"})
    private_key = PasswordField(validators=[Length(22)],
                                render_kw={"placeholder": "Wallet Private Key", 'disabled': 'true', 'hidden': 'true'})
    submit = SubmitField("Create")

    def validate_email(self, email):
        existing = Parent.query.filter_by(email=email.data).first()
        if existing:
            raise ValidationError("That email already exists. Please choose a different one.")


# Login Account Form
class LoginForm(FlaskForm):
    email = StringField(validators=[Length(min=4, max=40)], render_kw={"placeholder": "Email"})
    password = PasswordField(validators=[InputRequired(), Length(min=6, max=20)], render_kw={"placeholder": "Password"})
    name = StringField(validators=[Length(min=3)], render_kw={'placeholder': "Name", 'hidden': 'true'})
    submit = SubmitField("Login")


# Send Transaction Form
class TransferForm(FlaskForm):
    to_address = StringField(validators=[InputRequired(), Length(42)], render_kw={"placeholder": "To Address"})
    amount = IntegerField(validators=[InputRequired(), NumberRange(min=0)],
                          render_kw={"placeholder": "StakeUp Amount"})
    password = PasswordField(validators=[InputRequired(), Length(min=6, max=20)], render_kw={"placeholder": "Password"})


@app.before_request
def before_request():
    session.permanent = True
    app.permanent_session_lifetime = datetime.timedelta(minutes=20)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/wallet")
@login_required
def wallet_home():
    address = utils.get_adress_from_encrypted_wallet(current_user.wallet)
    bnb_balance = utils.get_bnb_balance(address)
    stakeup_balance = utils.get_stakeup_balance(address)
    from_txs = Transactions.query.filter_by(from_address=address).order_by(Transactions.date.desc()).limit(2).all()
    to_txs = Transactions.query.filter_by(to_address=address).order_by(Transactions.date.desc()).limit(2).all()
    return render_template('wallet.html', address=address, bnb_balance=bnb_balance, stakeup_balance=stakeup_balance,
                           from_txs=from_txs, to_txs=to_txs)


@app.route('/login', methods=['GET', "POST"])
def login():
    form = LoginForm()
    if request.method == "POST":
        user = Child.query.filter_by(name=form.name.data).first() or Parent.query.filter_by(
            email=form.email.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                session['address'] = utils.get_adress_from_encrypted_wallet(user.wallet)
                login_user(user, remember=True)

                return redirect('/wallet')
    return render_template('login_wallet.html', form=form)


@app.route('/create', methods=['GET', 'POST'])
def create():
    form = CreateForm()

    if request.method == 'POST':
        hashed = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        if form.private_key.data:
            wallet = utils.encrypt_wallet(utils.get_wallet_from_key(form.private_key.data), hashed)
        else:
            wallet = utils.create_encrypted_wallet(hashed)

        parent = Parent(email=form.email.data, password=hashed, name=form.name.data,
                        wallet=json.dumps(wallet),
                        session_token=serializer.dumps([form.email.data, hashed]))

        db.session.add(parent)
        db.session.commit()
        return redirect('/login')
    return render_template('create_wallet.html', form=form)


@app.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    logout_user()
    return redirect('/login')


@app.route('/manage-account')
@login_required
def manage():
    is_parent = isinstance(current_user, Parent)
    group = [[], []]
    if is_parent:
        group[1] = current_user.children
        if group[1]:
            group[0] = group[1][0].parents
    else:
        group[0] = current_user.parents
        if group:
            group[1] = group[0][0].children
    return render_template('manage.html', family_group=group, is_parent=is_parent)


@app.route('/manage-account/add-child', methods=['POST'])
@login_required
def add_child():
    name = request.form.get("child-name")
    password = request.form.get("child-password")

    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    wallet = utils.create_encrypted_wallet(hashed)

    child = Child(email=current_user.email, name=name, password=hashed, wallet=json.dumps(wallet),
                  session_token=serializer.dumps([password, hashed]))
    current_user.children.append(child)

    db.session.add(child)
    db.session.commit()

    return json.dumps({'status': 'OK'})


@app.route('/manage-account/add-parent', methods=['POST'])
@login_required
def parent():
    name = request.form.get("parent-name")
    email = request.form["parent-email"]
    password = request.form["parent-password"]

    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    wallet = utils.create_encrypted_wallet(hashed)

    parent = Parent(email=email, name=name, password=hashed, wallet=json.dumps(wallet),
                    session_token=serializer.dumps([email, hashed]))

    if len(current_user.children) == 0:
        return json.dumps({
            'error': True,
            'title': 'error',
            'msg': "Add a Child Before Adding a Parent"
        })

    for child in current_user.children:
        child.parents.append(parent)

    db.session.add(parent)
    db.session.commit()

    return json.dumps({'status': 'OK'})


@app.route('/transfer', methods=['GET'])
@app.route('/transfer/<token>', methods=['GET'])
@login_required
def transfer(token="STP"):
    form = TransferForm()
    group = [[], []]
    if isinstance(current_user, Parent):
        group[1] = current_user.children
        if group[1]:
            group[0] = group[1][0].parents
    else:
        group[0] = current_user.parents
        if group:
            group[1] = group[0][0].children
    return render_template('send_transaction.html', form=form, token=token, group=group)


@app.route('/transfer-post/get-address', methods=['POST'])
@login_required
def get_address():
    id = request.args.get('id')
    user = None
    if "@" in id:
        user = Parent.query.filter_by(email=id).first()
    else:
        for child in current_user.children:
            if child.name == id:
                user = child

    return json.dumps({
                'status': 'OK',
                'address': utils.get_adress_from_encrypted_wallet(user.wallet)
    })


@app.route('/transfer-post/<token>', methods=['POST'])
@login_required
def transfer_post(token="STP"):
    to_address = request.form['to_address']
    password = request.form['password']
    amount = request.form['amount']


    user = Parent.query.filter_by(email=current_user.email).first() or Child.query.filter_by(email=current_user.email)
    if bcrypt.check_password_hash(user.password, password):
        wallet = utils.decrypt_wallet(current_user.wallet, user.password)
        if token == "STP":
            transaction = utils.transfer_stakeup(wallet.address, wallet._private_key, to_address, amount)
        elif token == "BNB":
            transaction = utils.transfer_bnb(wallet.address, wallet._private_key, to_address, amount)
        else:
            return json.dumps({
                'error': True,
                'title': 'error',
                'msg': "Unrecognized Token"
            })

        if transaction == "StakeUp" or transaction == "BNB":
            tx = Transactions(from_address=session['address'], to_address=to_address, amount=amount, status=0, token_name=token)
            db.session.add(tx)
            db.session.commit()

            return json.dumps({
                'error': True,
                'title': 'error',
                'msg': "Not Enough " + transaction + " to Transact"
            })

        else:
            status = utils.get_status(transaction)
            if not status:
                status = 1
            else:
                status = 2
            tx = Transactions(from_address=session['address'], to_address=to_address, amount=amount, status=status, token_name=token)
            db.session.add(tx)
            db.session.commit()

            return json.dumps({
                'status': 'OK',
                'transaction': transaction.hex(),
                'tx_status': status
            })
    else:
        return json.dumps({
            'error': True,
            'title': 'error',
            'msg': 'Incorrect Password'
        })


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
