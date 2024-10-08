import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash,make_response
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash,check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # 画像保存先フォルダ
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 最大アップロードサイズ: 16MB
app.secret_key = 'your_secret_key'  # フラッシュメッセージのためのシークレットキー

# SQLiteデータベースへの接続
def get_db_connection():
    conn = sqlite3.connect('cafe_manegement.db')
    conn.row_factory = sqlite3.Row
    return conn

# 初回起動時にテーブルを作成する関数
def init_db():
    conn = get_db_connection()
    try:
        conn.execute(''' CREATE TABLE IF NOT EXISTS StockLog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            quantity INTEGER,
            operation_type TEXT,
            datetime TEXT,
            responsible_person TEXT,
            FOREIGN KEY (product_id) REFERENCES Product(id)
        ) ''')
        conn.execute(''' CREATE TABLE IF NOT EXISTS Product (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL,
            category TEXT,
            image_url TEXT,
            description TEXT
        ) ''')
        conn.execute(''' CREATE TABLE IF NOT EXISTS MANAGERS (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            password TEXT,
            role TEXT
        ) ''')
        conn.commit()
    except Exception as e:
        print(f"Database initialization error: {e}")
    finally:
        conn.close()

# アプリケーションが起動する際にテーブルを初期化
init_db()

# 画像の許可拡張子
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ログインページ
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']

        conn = get_db_connection()
        staff = conn.execute('SELECT * FROM MANAGERS WHERE name = ?', (name,)).fetchone()
        conn.close()

        if staff and check_password_hash(staff['password'], password):  # パスワードをチェック
            resp = make_response(redirect(url_for('stock_operation')))
            resp.set_cookie('responsible_person', name)  # クッキーに担当者を保存
            return resp
        else:
            flash('ログイン情報が正しくありません。')

    return render_template('login.html')

# 在庫の入出庫処理ページ
@app.route('/stock_operation', methods=['GET', 'POST'])
def stock_operation():
    conn = get_db_connection()
    if request.method == 'POST':
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])
        operation_type = request.form['operation_type']
        
        responsible_person = request.cookies.get('responsible_person', '')  # クッキーから担当者を取得
        datetime_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # StockLogテーブルに記録
        conn.execute('INSERT INTO StockLog (product_id, quantity, operation_type, datetime, responsible_person) VALUES (?, ?, ?, ?, ?)',
                     (product_id, quantity, operation_type, datetime_now, responsible_person))
        
        conn.commit()
        conn.close()
        return redirect(url_for('stock_operation'))

    # 商品一覧を取得して表示
    products = conn.execute('SELECT * FROM Product').fetchall()
    conn.close()
    return render_template('stock_operation.html', products=products)

# ログアウト機能
@app.route('/logout')
def logout():
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('responsible_person', '', expires=0)  # クッキーを削除
    return resp

# 商品入力ページの表示と処理
@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        category = request.form['category']
        description = request.form['description']
        
        # 画像アップロード処理
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            image_url = filepath  # 保存先パスをデータベースに保存
        else:
            image_url = ''  # 画像がない場合は空欄にする

        conn = get_db_connection()
        conn.execute('INSERT INTO Product (name, price, category, image_url, description) VALUES (?, ?, ?, ?, ?)',
                     (name, price, category, image_url, description))
        conn.commit()
        conn.close()
        return redirect(url_for('add_product'))  # 入力後も同じページを表示

    return render_template('add_product.html')

# 商品編集ページの表示と処理
@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM Product WHERE id = ?', (product_id,)).fetchone()

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        category = request.form['category']
        description = request.form['description']
        
        conn.execute('UPDATE Product SET name = ?, price = ?, category = ?, description = ? WHERE id = ?',
                     (name, price, category, description, product_id))
        conn.commit()
        conn.close()
        return redirect(url_for('product_list'))

    conn.close()
    return render_template('edit_product.html', product=product)

# 商品削除機能
@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM Product WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('product_list'))

# 商品一覧ページ
@app.route('/product_list')
def product_list():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM Product').fetchall()  # Productテーブルの全データを取得
    conn.close()
    return render_template('product_list.html', products=products)

# 在庫の入出庫処理ページ


# 在庫履歴の編集ページ
@app.route('/edit_stock/<int:log_id>', methods=['GET', 'POST'])
def edit_stock(log_id):
    conn = get_db_connection()
    stock_log = conn.execute('SELECT * FROM StockLog WHERE id = ?', (log_id,)).fetchone()

    if request.method == 'POST':
        quantity = int(request.form['quantity'])
        operation_type = request.form['operation_type']
        responsible_person = request.form['responsible_person']

        conn.execute('UPDATE StockLog SET quantity = ?, operation_type = ?, responsible_person = ? WHERE id = ?',
                     (quantity, operation_type, responsible_person, log_id))
        conn.commit()
        conn.close()
        return redirect(url_for('stock_history'))

    conn.close()
    return render_template('edit_stock.html', stock_log=stock_log)

# 在庫履歴の削除機能
@app.route('/delete_stock/<int:log_id>', methods=['POST'])
def delete_stock(log_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM StockLog WHERE id = ?', (log_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('stock_history'))

# 在庫履歴一覧を表示
@app.route('/stock_history')
def stock_history():
    conn = get_db_connection()
    stock_logs = conn.execute(''' 
        SELECT StockLog.*, Product.name AS product_name 
        FROM StockLog 
        JOIN Product ON StockLog.product_id = Product.id
        ORDER BY StockLog.datetime DESC 
    ''').fetchall()
    conn.close()
    return render_template('stock_history.html', stock_logs=stock_logs)

# スタッフ登録ページ
@app.route('/register_staff', methods=['GET', 'POST'])
def register_staff():
    if request.method == 'POST':
        name = request.form['name']
        password = generate_password_hash(request.form['password'])  # パスワードをハッシュ化
        role = request.form['role']

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO MANAGERS (name, password, role) VALUES (?, ?, ?)',
                         (name, password, role))
            conn.commit()
            # フラッシュメッセージの設定
            flash('スタッフが登録されました。')
        except Exception as e:
            print(f"Error registering staff: {e}")
        finally:
            conn.close()

        return redirect(url_for('register_staff'))

    return render_template('register_staff.html')

if __name__ == '__main__':
    app.run(debug=False)
