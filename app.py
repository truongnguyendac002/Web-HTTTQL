from flask import Flask, render_template, redirect, url_for, request, flash
from flask_mysqldb import MySQL
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'key'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Truongkute'
app.config['MYSQL_DB'] = 'flask_app'

mysql = MySQL(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, phone, role):
        self.id = id
        self.username = username
        self.phone = phone
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, username, phone, role FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    if user:
        return User(id=user[0], username=user[1], phone=user[2], role=user[3])
    return None

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, username, phone, role FROM users WHERE username = %s AND password = %s", (username, password))
        user = cur.fetchone()
        if user:
            user_obj = User(user[0], user[1], user[2], user[3])
            login_user(user_obj)
            print(user_obj.role)
            if user_obj.role == 'banhang':
                return redirect(url_for('nvbanhang'))
            elif user_obj.role == 'quanly':
                return redirect(url_for('quanly'))
            elif user_obj.role == 'thukho':
                return redirect(url_for('nvthukho'))
            
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', form=form)

@app.route("/nvbanhang")
@login_required
def nvbanhang():
    return render_template('nvbanhang.html')

@app.route("/quanly")
@login_required
def quanly():
    return render_template('quanly.html')

@app.route("/nvthukho")
@login_required
def nvthukho():
    return render_template('nvthukho.html')

@app.route("/")
@login_required
def home():
    return f'Hello, {current_user.role}!'

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
