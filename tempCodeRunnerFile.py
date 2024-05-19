from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import pyodbc

app = Flask(__name__)
app.config['SECRET_KEY'] = 'key'
app.config['MSSQL_SERVER'] = 'DESKTOP-P61169L\HIHI'
app.config['MSSQL_DATABASE'] = 'HTTTQL'
app.config['MSSQL_USER'] = 'sa'
app.config['MSSQL_PASSWORD'] = 'sa'

# Setup MSSQL connection
def get_db_connection():
    conn = pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={app.config['MSSQL_SERVER']};"
        f"DATABASE={app.config['MSSQL_DATABASE']};"
        f"UID={app.config['MSSQL_USER']};"
        f"PWD={app.config['MSSQL_PASSWORD']}"
    )
    return conn

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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, phone, role FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
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
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, phone, role FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            user_obj = User(user[0], user[1], user[2], user[3])
            login_user(user_obj)
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

# Trang nv ban hang


added_products = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_product', methods=['POST'])
def add_product():
    product_code = request.json.get('product_code')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT maDienThoai, tenDienThoai, giaTien FROM DienThoai WHERE maDienThoai = ?", (product_code,))
    product = cursor.fetchone()
    conn.close()

    if product:
        product_info = {"maDienThoai": product[0], "tenDienThoai": product[1], "giaTien": product[2]}
        added_products.append(product_info)
        return jsonify({"success": True, "product": product_info}), 200
    else:
        return jsonify({"success": False, "message": "Product not found"}), 404


from uuid import uuid4

@app.route('/process_payment', methods=['POST'])
def process_payment():
    customer_phone = request.json.get('customer_phone')  # Sử dụng 'customer_phone' thay vì 'customer_code'

    if added_products:
        total_amount = sum(product['giaTien'] for product in added_products)
        
        # Tìm id của khách hàng dựa trên số điện thoại
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT maKhachHang FROM KhachHang WHERE sdt = ?", (customer_phone,))
        customer_id = cursor.fetchone()
        
        if customer_id:
            customer_id = customer_id[0]  # Lấy id của khách hàng

            # Tạo mã hóa đơn theo định dạng HDB000001
            cursor.execute("SELECT MAX(RIGHT(maHoaDon, 6)) FROM HoaDonBanHang")
            max_id = cursor.fetchone()[0]
            next_id = 1 if max_id is None else int(max_id) + 1
            maHoaDon = f'HDB{next_id:06d}'  # Format mã hóa đơn

            # Lưu hóa đơn bán hàng vào cơ sở dữ liệu
            cursor.execute("INSERT INTO HoaDonBanHang (maHoaDon, maKhachHang, maNhanVien, ngayThanhToan, tongTien) VALUES (?, ?, ?, GETDATE(), ?)", (maHoaDon, customer_id, current_user.id, total_amount))
            conn.commit()
            conn.close()

            return jsonify({"success": True, "total_amount": total_amount}), 200
        else:
            conn.close()
            return jsonify({"success": False, "message": "Customer not found"}), 404
    else:
        return jsonify({"success": False, "message": "No products to process"}), 400



if __name__ == '__main__':
    app.run(debug=True)
