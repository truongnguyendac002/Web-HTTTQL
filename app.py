from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import pyodbc
from datetime import datetime, timedelta


app = Flask(__name__)
app.config['SECRET_KEY'] = 'key'

# app.config['MSSQL_SERVER'] = 'DESKTOP-P61169L\HIHI'
# app.config['MSSQL_DATABASE'] = 'HTTTQL'
# app.config['MSSQL_USER'] = 'sa'
# app.config['MSSQL_PASSWORD'] = 'sa'

app.config['MSSQL_SERVER'] = 'localhost'
app.config['MSSQL_DATABASE'] = 'HTTTQL'
app.config['MSSQL_USER'] = 'sa'
app.config['MSSQL_PASSWORD'] = 'nhom2'

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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT tenDienThoai, moTa, giaTien, img FROM DienThoai")
    dien_thoai_list = cursor.fetchall()
    conn.close()
    return render_template('trangchu.html',dien_thoai_list=dien_thoai_list)

@app.route("/lichlamviec", methods=['GET', 'POST'])
def lichlamviec():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        maNhanVien = request.form['maNhanVien']
        ngay = request.form['ngay']
        ca = request.form['ca']
        cursor.execute(
            "INSERT INTO LichLamViec (maNhanVien, ngay, ca) VALUES (?, ?, ?)",
            (maNhanVien, ngay, ca)
        )
        conn.commit()

    cursor.execute("SELECT maNhanVien, hoTen FROM NhanVien WHERE maChiNhanh = 'CN001'")
    employees = cursor.fetchall()

    # Get the current week's schedule
    start_of_week = datetime.now() - timedelta(days=datetime.now().weekday())
    weekly_schedule = {}
    for i in range(7):
        current_day = start_of_week + timedelta(days=i)
        formatted_date = current_day.strftime('%Y-%m-%d')
        weekly_schedule[current_day.strftime('%A')] = {'sáng': [], 'chiều': []}
        cursor.execute("SELECT nv.hoTen, llv.ca FROM LichLamViec llv JOIN NhanVien nv ON llv.maNhanVien = nv.maNhanVien WHERE llv.ngay = ?", (formatted_date,))
        shifts = cursor.fetchall()
        for shift in shifts:
            weekly_schedule[current_day.strftime('%A')][shift[1]].append(shift[0])

    conn.close()
    return render_template('QuanLy/QLLLV.html', employees=employees, weekly_schedule=weekly_schedule)

@app.route("/tkdoanhthunv")
def tkdoanhthunv():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT nv.maNhanVien, nv.hoTen, SUM(hdbh.tongTien) AS doanhThu
        FROM HoaDonBanHang hdbh
        JOIN NhanVien nv ON hdbh.maNhanVien = nv.maNhanVien
        WHERE nv.maChiNhanh = 'CN001'
        GROUP BY nv.maNhanVien, nv.hoTen
        ORDER BY doanhThu DESC
    """)
    rows = cursor.fetchall()
    
    # Loại bỏ khoảng trắng thừa trong maNhanVien
    doanhthu_data = [
        {'maNhanVien': row.maNhanVien.strip(), 'hoTen': row.hoTen.strip(), 'doanhThu': row.doanhThu}
        for row in rows
    ]
    
    conn.close()
    return render_template('QuanLy/TKDTNV.html', doanhthu_data=doanhthu_data)


@app.route("/tkdoanhthunv/<maNhanVien>")
def doanhthu_chitiet(maNhanVien):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT maHoaDon, maKhachHang, ngayThanhToan, tongTien
        FROM HoaDonBanHang
        WHERE maNhanVien = ?
        ORDER BY ngayThanhToan DESC
    """, (maNhanVien.strip(),))
    hoadon_data = cursor.fetchall()

    cursor.execute("SELECT hoTen FROM NhanVien WHERE maNhanVien = ?", (maNhanVien.strip(),))
    nhanvien = cursor.fetchone()
    
    conn.close()
    return render_template('QuanLy/ChiTietDoanhThuNV.html', hoadon_data=hoadon_data, nhanvien=nhanvien)



@app.route("/quanlyluong")
def quanlyluong():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Truy vấn để lấy danh sách nhân viên và mức lương của họ
    cursor.execute("""
        SELECT ROW_NUMBER() OVER (ORDER BY maNhanVien) AS stt, maNhanVien, hoTen, luong
        FROM NhanVien
        WHERE maChiNhanh = 'CN001'
    """)
    luong_data = cursor.fetchall()
    
    conn.close()
    return render_template('QuanLy/QLLuong.html', luong_data=luong_data)

@app.route('/delete_luong/<maNhanVien>', methods=['DELETE'])
def delete_luong(maNhanVien):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM BangLuong WHERE maNhanVien = ?", maNhanVien)
    conn.commit()
    conn.close()
    return jsonify(success=True)

@app.route('/update_luong', methods=['POST'])
def update_luong():
    data = request.get_json()
    maNhanVien = data['maNhanVien']
    hoTen = data['hoTen']
    luong = data['luong']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE NhanVien SET hoTen = ?, luong = ? WHERE maNhanVien = ?", (hoTen, luong, maNhanVien))
    conn.commit()
    conn.close()
    return jsonify(success=True)

@app.route('/delete_shift', methods=['POST'])
def delete_shift():
    data = request.get_json()
    day = data['day']
    shift = data['shift']
    employee = data['employee']
    
    # Chuyển đổi ngày từ chuỗi sang datetime.date
    day_date = datetime.strptime(day, '%Y-%m-%d').date()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM lich_lam_viec 
        WHERE maNhanVien = (
            SELECT maNhanVien FROM NhanVien WHERE hoTen = ?
        ) AND ngay = ? AND ca = ?
    """, (employee, day_date, shift))
    
    conn.commit()
    conn.close()
    
    return jsonify(success=True)


@app.route("/nvthukho")
@login_required
def nvthukho():
    return redirect(url_for('login'))

# @app.route("/")
# @login_required
# def home():
#     return f'Hello, {current_user.role}!'

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('login'))

# Trang nv ban hang

added_products = []

@app.route('/')
def index():
    return redirect(url_for('login'))



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


@app.route('/employee_management')
def employee_management():
    # Xử lý logic cho trang quản lý nhân viên ở đây
    return render_template('QuanLy/QLNhanVien.html')


# Quan ly khach hang
############################################
@app.route('/add_customer', methods=['POST'])
def add_customer():
    try:
        # Lấy dữ liệu khách hàng từ yêu cầu POST
        customer_data = request.json
        name = customer_data['name']
        address = customer_data['address']
        phone = customer_data['phone']
        
        # Tạo ID mới cho khách hàng
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(RIGHT(maKhachHang, 4)) FROM KhachHang")
        last_id = cursor.fetchone()[0]
        next_id = 1 if last_id is None else int(last_id) + 1
        new_customer_id = f'KH{next_id:04d}'
        
        # Thêm khách hàng vào cơ sở dữ liệu
        cursor.execute("INSERT INTO KhachHang (maKhachHang, hoTen, diaChi, sdt) VALUES (?, ?, ?, ?)", (new_customer_id, name, address, phone))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "Customer added successfully"}), 200

    except Exception as e:

        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/get_purchase_history', methods=['POST'])
def get_purchase_history():
    try:
        # Lấy số điện thoại của khách hàng từ yêu cầu POST
        customer_phone = request.json.get('customer_phone')

        # Tạo truy vấn SQL để lấy lịch sử mua hàng của khách hàng
        query = """
        SELECT HoaDonBanHang.maHoaDon, HoaDonBanHang.tongTien 
        FROM HoaDonBanHang 
        JOIN KhachHang ON HoaDonBanHang.maKhachHang = KhachHang.maKhachHang 
        WHERE KhachHang.sdt = ?
        """

        # Thực thi truy vấn và lấy kết quả
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, customer_phone)
        purchase_history = cursor.fetchall()

        # Chuyển kết quả sang định dạng phù hợp để trả về cho client
        formatted_purchase_history = [{'maHoaDon': row[0], 'tongTien': row[1]} for row in purchase_history]

        # Trả về lịch sử mua hàng dưới dạng JSON
        return jsonify({"success": True, "purchase_history": formatted_purchase_history}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
    
@app.route('/customer_management', methods=['GET'])
def customer_management():
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    connection = get_db_connection()
    cursor = connection.cursor()
    
    if search:
        search_query = f"""
        SELECT * FROM KhachHang
        WHERE maKhachHang LIKE ? OR hoTen LIKE ? OR sdt LIKE ?
        """
        search_param = f"%{search}%"
        cursor.execute(search_query, (search_param, search_param, search_param))
    else:
        cursor.execute("SELECT * FROM KhachHang")
    
    customers = cursor.fetchall()
    total_customers = len(customers)
    
    # Pagination logic
    start = (page - 1) * per_page
    end = start + per_page
    paginated_customers = customers[start:end]
    total_pages = (total_customers + per_page - 1) // per_page
    
    return render_template(
        'QuanLy/QLKhachHang.html',
        customers=paginated_customers,
        current_page=page,
        total_pages=total_pages,
        search=search
    )

@app.route('/update_customer', methods=['POST'])
def update_customer():
    data = request.json
    maKhachHang = data['maKhachHang']
    hoTen = data['hoTen']
    diaChi = data['diaChi']
    sdt = data['sdt']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
    UPDATE KhachHang
    SET hoTen = ?, diaChi = ?, sdt = ?
    WHERE maKhachHang = ?
    """
    cursor.execute(query, (hoTen, diaChi, sdt, maKhachHang))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/delete_customer', methods=['POST'])
def delete_customer():
    data = request.json
    maKhachHang = data['maKhachHang']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "DELETE FROM KhachHang WHERE maKhachHang = ?"
    cursor.execute(query, (maKhachHang,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})


@app.route('/finance_management')
def finance_management():
    # Xử lý logic cho trang quản lý tài chính ở đây
    return render_template('QuanLy/QLTaiChinh.html')



if __name__ == '__main__':
    app.run(debug=True)
