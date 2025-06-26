from flask import Flask, send_from_directory, jsonify, request
import sqlite3
from datetime import datetime
import hashlib

app = Flask(__name__)
app.secret_key = 'limexCraft-admin-t-21.21'

        # Admin şifre hash'i (varsayılan şifre: admin123)
ADMIN_PASSWORD_HASH = hashlib.sha256('limexCraft-admin-t-21.21'.encode()).hexdigest()

def get_db_connection():
            conn = sqlite3.connect('market.db')
            conn.row_factory = sqlite3.Row
            return conn

@app.route('/')
def index():
            return send_from_directory('.', 'index.html')

@app.route('/api/stats')
def get_stats():
            conn = get_db_connection()

            # İstatistikler
            pending_count = conn.execute('SELECT COUNT(*) FROM orders WHERE status = "pending"').fetchone()[0]
            completed_count = conn.execute('SELECT COUNT(*) FROM orders WHERE status = "completed"').fetchone()[0]
            cancelled_count = conn.execute('SELECT COUNT(*) FROM orders WHERE status = "cancelled"').fetchone()[0]
            total_revenue = conn.execute('SELECT SUM(price) FROM orders WHERE status = "completed"').fetchone()[0] or 0

            conn.close()

            return jsonify({
                'pending': pending_count,
                'completed': completed_count,
                'cancelled': cancelled_count,
                'revenue': total_revenue
            })

@app.route('/api/orders')
def get_orders():
            conn = get_db_connection()
            orders = conn.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
            conn.close()

            orders_list = []
            for order in orders:
                orders_list.append({
                    'id': order['id'],
                    'code': order['order_code'],
                    'username': order['username'],
                    'product': order['product_name'],
                    'price': order['price'],
                    'status': order['status'],
                    'date': order['created_at']
                })

            return jsonify(orders_list)

@app.route('/api/approve_order/<order_code>', methods=['POST'])
def approve_order(order_code):
            conn = get_db_connection()
            
            # Siparişi bul
            order = conn.execute('SELECT * FROM orders WHERE order_code = ? AND status = "pending"', (order_code,)).fetchone()
            
            if not order:
                conn.close()
                return jsonify({'success': False, 'message': f'Bekleyen sipariş bulunamadı: {order_code}'})
            
            # Siparişi onayla
            conn.execute('UPDATE orders SET status = "completed" WHERE order_code = ?', (order_code,))
            conn.commit()
            conn.close()

            return jsonify({'success': True, 'message': f'Sipariş {order_code} başarıyla onaylandı!'})

@app.route('/api/cancel_order/<order_code>', methods=['POST'])
def cancel_order(order_code):
            conn = get_db_connection()
            
            # Siparişi bul
            order = conn.execute('SELECT * FROM orders WHERE order_code = ? AND status = "pending"', (order_code,)).fetchone()
            
            if not order:
                conn.close()
                return jsonify({'success': False, 'message': f'Bekleyen sipariş bulunamadı: {order_code}'})
            
            # Siparişi iptal et
            conn.execute('UPDATE orders SET status = "cancelled" WHERE order_code = ?', (order_code,))
            conn.commit()
            conn.close()

            return jsonify({'success': True, 'message': f'Sipariş {order_code} iptal edildi!'})

@app.route('/api/products')
def get_products():
            conn = get_db_connection()
            products = conn.execute('SELECT * FROM products ORDER BY name').fetchall()
            conn.close()

            products_list = []
            for product in products:
                products_list.append({
                    'id': product['id'],
                    'name': product['name'],
                    'price': product['price'],
                    'description': product['description']
                })

            return jsonify(products_list)

@app.route('/api/add_product', methods=['POST'])
def add_product():
            data = request.get_json()
            name = data['name']
            price = data['price']
            description = data['description']

            conn = get_db_connection()
            conn.execute('INSERT INTO products (name, price, description) VALUES (?, ?, ?)', 
                        (name, price, description))
            conn.commit()
            conn.close()

            return jsonify({'success': True, 'message': f'Ürün "{name}" başarıyla eklendi!'})

@app.route('/api/delete_product/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
            conn = get_db_connection()
            conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
            conn.commit()
            conn.close()

            return jsonify({'success': True, 'message': 'Ürün başarıyla silindi!'})

if __name__ == '__main__':
            app.run(debug=True, host='0.0.0.0', port=8080)