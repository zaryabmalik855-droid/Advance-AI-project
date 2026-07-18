#!/usr/bin/env python
"""
Complete Trusted Home Platform - Simple HTTP Server (No Framework Dependencies)
Working alternative without FastAPI/Django compatibility issues
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import sqlite3
import hashlib
import hmac
from datetime import datetime, timedelta
import uuid
from typing import Dict, Any
import socket

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.db_file = "trusted_home.db"
        self.init_db()
    
    def connect(self):
        return sqlite3.connect(self.db_file)
    
    def init_db(self):
        conn = self.connect()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT,
                phone TEXT,
                password_hash TEXT,
                city TEXT,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Workers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workers (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                experience_years INTEGER DEFAULT 0,
                rating REAL DEFAULT 0.0,
                specialties TEXT,
                description TEXT,
                verified BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # Services table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY,
                name TEXT,
                category TEXT,
                description TEXT,
                price REAL,
                duration INTEGER,
                worker_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(worker_id) REFERENCES workers(id)
            )
        ''')
        
        # Bookings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                service_id INTEGER,
                status TEXT DEFAULT 'pending',
                booking_date TIMESTAMP,
                location TEXT DEFAULT '',
                house_number TEXT DEFAULT '',
                full_name TEXT DEFAULT '',
                phone_number TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(service_id) REFERENCES services(id)
            )
        ''')
        
        # Add missing columns to existing bookings table if they don't exist
        try:
            cursor.execute('ALTER TABLE bookings ADD COLUMN location TEXT DEFAULT ""')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE bookings ADD COLUMN house_number TEXT DEFAULT ""')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE bookings ADD COLUMN full_name TEXT DEFAULT ""')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE bookings ADD COLUMN phone_number TEXT DEFAULT ""')
        except:
            pass
        
        # Create test data
        cursor.execute('SELECT COUNT(*) FROM users')
        if cursor.fetchone()[0] == 0:
            # Create test users
            password_hash = hashlib.sha256(b'User@12345').hexdigest()
            cursor.execute(
                'INSERT INTO users (email, full_name, phone, password_hash, city, role) VALUES (?, ?, ?, ?, ?, ?)',
                ('user@example.com', 'Test User', '+923001234567', password_hash, 'Karachi', 'user')
            )
            user_id = cursor.lastrowid
            
            admin_hash = hashlib.sha256(b'Admin@12345').hexdigest()
            cursor.execute(
                'INSERT INTO users (email, full_name, phone, password_hash, city, role) VALUES (?, ?, ?, ?, ?, ?)',
                ('admin@example.com', 'Admin User', '+923001234568', admin_hash, 'Karachi', 'admin')
            )
            
            # Create test workers
            worker_users = [
                ('ahmed@example.com', 'Ahmed Khan', '+923001234569', 'Karachi', 5, 4.8, 'Plumbing,Electrical', 'Certified plumber with 5 years experience'),
                ('sara@example.com', 'Sara Ahmed', '+923001234570', 'Lahore', 3, 4.9, 'AC Repair,Cleaning', 'AC specialist with expertise in all brands'),
                ('bilal@example.com', 'Bilal Hussain', '+923001234571', 'Islamabad', 7, 4.7, 'Electrical,Plumbing', 'Master electrician and plumbing expert')
            ]
            
            for email, name, phone, city, exp, rating, specs, desc in worker_users:
                worker_hash = hashlib.sha256(b'Worker@12345').hexdigest()
                cursor.execute(
                    'INSERT INTO users (email, full_name, phone, password_hash, city, role) VALUES (?, ?, ?, ?, ?, ?)',
                    (email, name, phone, worker_hash, city, 'worker')
                )
                worker_user_id = cursor.lastrowid
                
                cursor.execute(
                    'INSERT INTO workers (user_id, experience_years, rating, specialties, description, verified) VALUES (?, ?, ?, ?, ?, ?)',
                    (worker_user_id, exp, rating, specs, desc, 1)
                )
                worker_id = cursor.lastrowid
                
                # Create services for this worker
                if 'Plumbing' in specs:
                    cursor.execute(
                        'INSERT INTO services (name, category, description, price, duration, worker_id) VALUES (?, ?, ?, ?, ?, ?)',
                        ('Plumbing Service', 'plumber', 'Professional plumbing services including repairs and installations', 1500, 60, worker_id)
                    )
                if 'Electrical' in specs:
                    cursor.execute(
                        'INSERT INTO services (name, category, description, price, duration, worker_id) VALUES (?, ?, ?, ?, ?, ?)',
                        ('Electrical Service', 'electrician', 'Certified electrical services for homes and offices', 1200, 45, worker_id)
                    )
                if 'AC Repair' in specs:
                    cursor.execute(
                        'INSERT INTO services (name, category, description, price, duration, worker_id) VALUES (?, ?, ?, ?, ?, ?)',
                        ('AC Repair Service', 'ac_repair', 'Complete air conditioning repair and maintenance', 2000, 90, worker_id)
                    )
            
            conn.commit()
            print("✓ Database initialized with test data")
        
        conn.close()

# ==================== AUTHENTICATION ====================
class Auth:
    SECRET = "trusted-home-secret-key-2024"
    
    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(password, hash_val):
        return Auth.hash_password(password) == hash_val
    
    @staticmethod
    def create_token(email, user_id):
        payload = f"{email}:{user_id}:{datetime.now().timestamp()}"
        return hmac.new(Auth.SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest() + f":{user_id}"
    
    @staticmethod
    def verify_token(token):
        try:
            if ':' not in token:
                return None
            token_hash, user_id = token.rsplit(':', 1)
            # For simplicity, we'll just return the user_id from the token
            # In production, you'd verify the hash properly
            return int(user_id)
        except:
            return None

# ==================== REQUEST HANDLER ====================
class TrustedHomeHandler(BaseHTTPRequestHandler):
    db = Database()
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        # API routes
        if path.startswith('/api/'):
            self.handle_api_get(path, query)
            return
        
        # Web interface routes
        if path == '/' or path == '/web':
            self.serve_html_page('dashboard')
        elif path == '/web/login':
            self.serve_html_page('login')
        elif path == '/web/register':
            self.serve_html_page('register')
        elif path == '/web/services':
            self.serve_html_page('services')
        elif path == '/web/bookings':
            self.serve_html_page('bookings')
        elif path == '/web/profile':
            self.serve_html_page('profile')
        elif path == '/web/dashboard':
            self.serve_html_page('dashboard')
        else:
            self.send_html(404, "<h1>404 - Page Not Found</h1>")
    
    def handle_api_get(self, path, query):
        if path == '/api/services':
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.id, s.name, s.category, s.description, s.price, s.duration,
                       w.experience_years, w.rating, w.specialties, w.description as worker_desc,
                       u.full_name, u.phone, u.city
                FROM services s
                JOIN workers w ON s.worker_id = w.id
                JOIN users u ON w.user_id = u.id
                WHERE w.verified = 1
            ''')
            services = []
            for row in cursor.fetchall():
                services.append({
                    'id': row[0],
                    'name': row[1],
                    'category': row[2],
                    'description': row[3],
                    'price': row[4],
                    'duration': row[5],
                    'worker': {
                        'name': row[10],
                        'experience_years': row[6],
                        'rating': row[7],
                        'specialties': row[8],
                        'description': row[9],
                        'phone': row[11],
                        'city': row[12]
                    }
                })
            conn.close()
            self.send_json(200, {"services": services})
        
        elif path.startswith('/api/bookings'):
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            user_id = Auth.verify_token(token)
            if not user_id:
                self.send_json(401, {"error": "Invalid or missing token"})
                return
            
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT b.id, b.user_id, b.service_id, b.status, b.booking_date, b.created_at,
                       s.name as service_name, s.price,
                       u.full_name as worker_name, b.location, b.house_number, b.full_name as customer_full_name, b.phone_number
                FROM bookings b
                JOIN services s ON b.service_id = s.id
                JOIN workers w ON s.worker_id = w.id
                JOIN users u ON w.user_id = u.id
                WHERE b.user_id = ?
                ORDER BY b.created_at DESC
            ''', (user_id,))
            bookings = []
            for row in cursor.fetchall():
                bookings.append({
                    'id': row[0],
                    'user_id': row[1],
                    'service_id': row[2],
                    'status': row[3],
                    'booking_date': row[4],
                    'created_at': row[5],
                    'service_name': row[6],
                    'price': row[7],
                    'worker_name': row[8],
                    'location': row[9],
                    'house_number': row[10],
                    'customer_full_name': row[11],
                    'phone_number': row[12]
                })
            conn.close()
            self.send_json(200, {"bookings": bookings})
        
        elif path == '/api/user/me':
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            user_id = Auth.verify_token(token)
            if not user_id:
                self.send_json(401, {"error": "Invalid or missing token"})
                return
            
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT id, email, full_name, phone, city, role FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                self.send_json(200, {
                    "id": user[0],
                    "email": user[1],
                    "full_name": user[2],
                    "phone": user[3],
                    "city": user[4],
                    "role": user[5]
                })
            else:
                self.send_json(404, {"error": "User not found"})
        
        else:
            self.send_json(404, {"error": "Not found"})
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        path = self.path
        
        if path == '/api/auth/register':
            email =data.get('email')
            password = data.get('password')
            full_name = data.get('full_name')
            
            if not email or not password:
                self.send_json(400, {"error": "Email and password required"})
                return
            
            conn = self.db.connect()
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            if cursor.fetchone():
                conn.close()
                self.send_json(400, {"error": "Email already exists"})
                return
            
            password_hash = Auth.hash_password(password)
            cursor.execute(
                'INSERT INTO users (email, full_name, password_hash, city) VALUES (?, ?, ?, ?)',
                (email, full_name or email, password_hash, 'Unknown')
            )
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            
            self.send_json(201, {
                "message": "User registered successfully",
                "user": {"id": user_id, "email": email}
            })
        
        elif path == '/api/auth/login':
            email = data.get('email')
            password = data.get('password')
            
            if not email or not password:
                self.send_json(400, {"error": "Email and password required"})
                return
            
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT id, password_hash FROM users WHERE email = ?', (email,))
            result = cursor.fetchone()
            conn.close()
            
            if not result or not Auth.verify_password(password, result[1]):
                self.send_json(401, {"error": "Invalid credentials"})
                return
            
            token = Auth.create_token(email, result[0])
            self.send_json(200, {
                "access_token": token,
                "token_type": "bearer",
                "user_id": result[0]
            })
        
        elif path == '/api/bookings' or path == '/api/bookings/':
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            user_id = Auth.verify_token(token)
            if not user_id:
                self.send_json(401, {"error": "Invalid or missing token"})
                return
            
            # UNIQUE_MARKER_12345 - This line should execute
            service_id = data.get('service_id')
            booking_date = data.get('booking_date')
            location = data.get('location', '')
            house_number = data.get('house_number', '')
            full_name = data.get('full_name', '')
            phone_number = data.get('phone_number', '')
            
            if not service_id:
                self.send_json(400, {"error": "service_id required"})
                return
            
            if not location:
                self.send_json(400, {"error": "location is required"})
                return
            
            conn = self.db.connect()
            cursor = conn.cursor()
            
            try:
                # Verify service exists and get price
                cursor.execute('SELECT price FROM services WHERE id = ?', (service_id,))
                result = cursor.fetchone()
                if not result:
                    conn.close()
                    self.send_json(404, {"error": "Service not found"})
                    return
                
                price = result[0]
                
                # Create booking with authenticated user
                cursor.execute(
                    'INSERT INTO bookings (user_id, service_id, booking_date, status, location, house_number, full_name, phone_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (user_id, service_id, booking_date or datetime.now().isoformat(), 'pending', location, house_number, full_name, phone_number)
                )
                conn.commit()
                booking_id = cursor.lastrowid
                conn.close()
                
                self.send_json(201, {
                    "success": True,
                    "message": "Booking created successfully",
                    "booking": {"id": booking_id, "service_id": service_id, "user_id": user_id, "price": price, "status": "pending"}
                })
            except Exception as e:
                conn.close()
                self.send_json(500, {"error": f"Database error: {str(e)}"})
            
        
        elif path.startswith('/api/bookings/') and '/cancel' in path:
            # Cancel booking
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            user_id = Auth.verify_token(token)
            if not user_id:
                self.send_json(401, {"error": "Invalid or missing token"})
                return
            
            try:
                # Extract booking ID from path like /api/bookings/123/cancel
                path_parts = path.split('/')
                booking_id = int(path_parts[3])
            except (ValueError, IndexError):
                self.send_json(400, {"error": "Invalid booking ID"})
                return
            
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # Check if booking belongs to user
            cursor.execute('SELECT user_id, status FROM bookings WHERE id = ?', (booking_id,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                self.send_json(404, {"error": "Booking not found"})
                return
            
            if result[0] != user_id:
                conn.close()
                self.send_json(403, {"error": "Unauthorized"})
                return
            
            if result[1] == 'completed':
                conn.close()
                self.send_json(400, {"error": "Cannot cancel completed booking"})
                return
            
            # Update booking status
            cursor.execute('UPDATE bookings SET status = ? WHERE id = ?', ('cancelled', booking_id))
            conn.commit()
            conn.close()
            
            self.send_json(200, {"message": "Booking cancelled successfully", "booking_id": booking_id})
        
        elif path.startswith('/api/bookings/') and '/complete' in path:
            # Complete booking
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            user_id = Auth.verify_token(token)
            if not user_id:
                self.send_json(401, {"error": "Invalid or missing token"})
                return
            
            try:
                # Extract booking ID from path like /api/bookings/123/complete
                path_parts = path.split('/')
                booking_id = int(path_parts[3])
            except (ValueError, IndexError):
                self.send_json(400, {"error": "Invalid booking ID"})
                return
            
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # Check if booking belongs to user
            cursor.execute('SELECT user_id, status FROM bookings WHERE id = ?', (booking_id,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                self.send_json(404, {"error": "Booking not found"})
                return
            
            if result[0] != user_id:
                conn.close()
                self.send_json(403, {"error": "Unauthorized"})
                return
            
            if result[1] == 'cancelled':
                conn.close()
                self.send_json(400, {"error": "Cannot complete cancelled booking"})
                return
            
            # Update booking status
            cursor.execute('UPDATE bookings SET status = ? WHERE id = ?', ('completed', booking_id))
            conn.commit()
            conn.close()
            
            self.send_json(200, {"message": "Booking completed successfully", "booking_id": booking_id})
        
        elif path == '/api/change-password':
            # Change password endpoint
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            user_id = Auth.verify_token(token)
            if not user_id:
                self.send_json(401, {"error": "Invalid or missing token"})
                return
            
            current_password = data.get('current_password')
            new_password = data.get('new_password')
            
            if not current_password or not new_password:
                self.send_json(400, {"error": "current_password and new_password are required"})
                return
            
            if len(new_password) < 6:
                self.send_json(400, {"error": "New password must be at least 6 characters"})
                return
            
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # Get user's current password hash
            cursor.execute('SELECT password_hash FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                self.send_json(404, {"error": "User not found"})
                return
            
            password_hash = result[0]
            
            # Verify current password
            if not Auth.verify_password(current_password, password_hash):
                conn.close()
                self.send_json(401, {"error": "Current password is incorrect"})
                return
            
            # Hash new password
            new_password_hash = Auth.hash_password(new_password)
            
            # Update password
            cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_password_hash, user_id))
            conn.commit()
            conn.close()
            
            self.send_json(200, {"message": "Password changed successfully"})
        
        else:
            self.send_json(404, {"error": "Not found"})
    
    def do_DELETE(self):
        path = self.path
        
        if path.startswith('/api/bookings/') and path.endswith(('delete', 'delete/')):
            # Old format - not used
            self.send_json(400, {"error": "Invalid request"})
            return
        
        elif path.startswith('/api/bookings/'):
            # DELETE /api/bookings/{id}
            try:
                booking_id = int(path.split('/')[3])
            except (ValueError, IndexError):
                self.send_json(400, {"error": "Invalid booking ID"})
                return
            
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            user_id = Auth.verify_token(token)
            if not user_id:
                self.send_json(401, {"error": "Invalid or missing token"})
                return
            
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # Check if booking belongs to user
            cursor.execute('SELECT user_id, status FROM bookings WHERE id = ?', (booking_id,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                self.send_json(404, {"error": "Booking not found"})
                return
            
            if result[0] != user_id:
                conn.close()
                self.send_json(403, {"error": "Unauthorized"})
                return
            
            # Only allow deletion of completed or cancelled bookings
            if result[1] not in ['completed', 'cancelled']:
                conn.close()
                self.send_json(400, {"error": "Can only delete completed or cancelled bookings"})
                return
            
            # Delete booking
            cursor.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
            conn.commit()
            conn.close()
            
            self.send_json(200, {"message": "Booking deleted successfully"})
        
        else:
            self.send_json(404, {"error": "Not found"})
    
    def send_json(self, status, data):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def send_html(self, status, html_content):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def serve_html_page(self, page_name):
        html_templates = {
            'dashboard': self.get_dashboard_html(),
            'login': self.get_login_html(),
            'register': self.get_register_html(),
            'services': self.get_services_html(),
            'bookings': self.get_bookings_html(),
            'profile': self.get_profile_html()
        }
        
        if page_name in html_templates:
            self.send_html(200, html_templates[page_name])
        else:
            self.send_html(404, "<h1>404 - Page Not Found</h1>")
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    # ==================== HTML TEMPLATES ====================
    
    def get_dashboard_html(self):
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trusted Home Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem 1rem; text-align: center; }
        .header h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
        .header p { font-size: 1.1rem; opacity: 0.9; }
        
        .nav { background: #34495e; padding: 0.75rem; display: flex; flex-wrap: wrap; gap: 0.5rem; }
        .nav a { color: white; text-decoration: none; padding: 0.5rem 1rem; border-radius: 4px; transition: all 0.3s; }
        .nav a:hover { background: #2980b9; }
        .nav span { color: white; margin-left: auto; padding: 0.5rem; }
        
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .card { background: white; border-radius: 12px; padding: 2rem; margin: 1.5rem 0; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        
        /* Hero Section */
        .hero { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 12px; padding: 3rem 2rem; text-align: center; margin-bottom: 2rem; }
        .hero h2 { font-size: 2rem; margin-bottom: 1rem; }
        .hero p { font-size: 1.1rem; margin-bottom: 2rem; opacity: 0.95; }
        .hero-btns { display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; }
        
        .btn { background: #3498db; color: white; padding: 0.75rem 1.5rem; border: none; border-radius: 6px; cursor: pointer; font-size: 1rem; transition: all 0.3s; }
        .btn:hover { background: #2980b9; transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
        .btn-primary { background: #27ae60; }
        .btn-primary:hover { background: #229954; }
        
        /* Stats Section */
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
        .stat-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; border-radius: 12px; text-align: center; }
        .stat-number { font-size: 2.5rem; font-weight: bold; }
        .stat-label { font-size: 1rem; opacity: 0.9; margin-top: 0.5rem; }
        
        /* Features Section */
        .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 2rem; margin: 3rem 0; }
        .feature-card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; transition: transform 0.3s; }
        .feature-card:hover { transform: translateY(-8px); box-shadow: 0 8px 16px rgba(0,0,0,0.15); }
        .feature-icon { font-size: 3rem; margin-bottom: 1rem; }
        .feature-card h3 { color: #2c3e50; margin-bottom: 1rem; font-size: 1.3rem; }
        .feature-card p { color: #555; line-height: 1.6; }
        
        /* Service Category Cards */
        .service-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin-top: 2rem; }
        .service-box { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 2rem; border-radius: 12px; text-align: center; border: 2px solid transparent; transition: all 0.3s; }
        .service-box:hover { border-color: #667eea; transform: translateY(-5px); }
        .service-icon { font-size: 3.5rem; margin-bottom: 1rem; }
        .service-box h3 { color: #2c3e50; margin-bottom: 0.5rem; }
        .service-box p { color: #555; font-size: 0.95rem; margin-bottom: 1rem; }
        .service-price { font-weight: bold; color: #27ae60; font-size: 1.2rem; }
        
        /* Testimonials */
        .testimonials { background: white; border-radius: 12px; padding: 2rem; margin-top: 3rem; }
        .testimonials h2 { color: #2c3e50; margin-bottom: 2rem; text-align: center; }
        .testimonial-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; }
        .testimonial-card { background: #f8f9fa; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #667eea; }
        .testimonial-text { color: #555; margin-bottom: 1rem; font-style: italic; }
        .testimonial-author { font-weight: bold; color: #2c3e50; }
        .stars { color: #f39c12; }
        
        /* Why Choose Us */
        .why-choose { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin: 2rem 0; }
        .why-item { padding: 1.5rem; background: #f0f4f8; border-radius: 8px; text-align: center; }
        .why-item .icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
        .why-item h4 { color: #2c3e50; margin: 0.5rem 0; }
        .why-item p { color: #666; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏠 Trusted Home Platform</h1>
        <p>Your trusted partner for professional home services</p>
    </div>
    
    <div class="nav">
        <a href="/web/dashboard">Dashboard</a>
        <a href="/web/services">Services</a>
        <a href="/web/bookings">My Bookings</a>
        <a href="/web/profile">Profile</a>
        <span id="user-info">Not logged in</span>
        <a href="#" id="logout-link" style="display:none;" onclick="logout(); return false;">Logout</a>
        <a href="/web/login" id="login-link">Login</a>
    </div>
    
    <div class="container">
        <!-- Hero Section -->
        <div class="hero">
            <h2 id="hero-title">Welcome to Trusted Home!</h2>
            <p id="hero-subtitle">Get professional home services from verified workers in your area</p>
            <div class="hero-btns">
                <a href="/web/services" class="btn btn-primary" style="text-decoration: none;">🔍 Browse Services</a>
                <a href="/web/register" class="btn" style="text-decoration: none;">📝 Register Now</a>
            </div>
        </div>
        
        <!-- Stats Section -->
        <div class="stats" id="stats-container">
            <div class="stat-card">
                <div class="stat-number">2500+</div>
                <div class="stat-label">Happy Customers</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">500+</div>
                <div class="stat-label">Verified Workers</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">15000+</div>
                <div class="stat-label">Services Completed</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">4.8★</div>
                <div class="stat-label">Customer Rating</div>
            </div>
        </div>
        
        <!-- Why Choose Us -->
        <div class="card">
            <h2 style="color: #2c3e50; margin-bottom: 2rem; text-align: center;">Why Choose Trusted Home?</h2>
            <div class="why-choose">
                <div class="why-item">
                    <div class="icon">✅</div>
                    <h4>Verified Workers</h4>
                    <p>All our workers are verified and certified professionals</p>
                </div>
                <div class="why-item">
                    <div class="icon">💰</div>
                    <h4>Transparent Pricing</h4>
                    <p>No hidden charges, upfront and clear pricing</p>
                </div>
                <div class="why-item">
                    <div class="icon">🔒</div>
                    <h4>Safe & Secure</h4>
                    <p>Your safety and security is our top priority</p>
                </div>
                <div class="why-item">
                    <div class="icon">⏰</div>
                    <h4>On-Time Service</h4>
                    <p>Professional and punctual service delivery</p>
                </div>
                <div class="why-item">
                    <div class="icon">📞</div>
                    <h4>24/7 Support</h4>
                    <p>Round-the-clock customer support available</p>
                </div>
                <div class="why-item">
                    <div class="icon">⭐</div>
                    <h4>Quality Guarantee</h4>
                    <p>100% satisfaction guarantee on all services</p>
                </div>
            </div>
        </div>
        
        <!-- Featured Services -->
        <div class="card">
            <h2 style="text-align: center; color: #2c3e50; margin-bottom: 2rem;">Our Popular Services</h2>
            <div class="service-grid">
                <div class="service-box">
                    <div class="service-icon">🔧</div>
                    <h3>Plumbing</h3>
                    <p>Professional plumbing repairs, installations, and maintenance</p>
                    <p class="service-price">From Rs. 1,500</p>
                    <button class="btn" onclick="window.location.href='/web/services'" style="width: 100%; margin-top: 1rem;">Book Now</button>
                </div>
                <div class="service-box">
                    <div class="service-icon">⚡</div>
                    <h3>Electrical</h3>
                    <p>Certified electrical services for homes and offices</p>
                    <p class="service-price">From Rs. 1,200</p>
                    <button class="btn" onclick="window.location.href='/web/services'" style="width: 100%; margin-top: 1rem;">Book Now</button>
                </div>
                <div class="service-box">
                    <div class="service-icon">❄️</div>
                    <h3>AC Repair</h3>
                    <p>Complete air conditioning repair and maintenance services</p>
                    <p class="service-price">From Rs. 2,000</p>
                    <button class="btn" onclick="window.location.href='/web/services'" style="width: 100%; margin-top: 1rem;">Book Now</button>
                </div>
            </div>
        </div>
        
        <!-- Features -->
        <div style="margin: 3rem 0;">
            <h2 style="text-align: center; color: #2c3e50; margin-bottom: 2rem;">How It Works</h2>
            <div class="features">
                <div class="feature-card">
                    <div class="feature-icon">📝</div>
                    <h3>1. Register</h3>
                    <p>Create your account in just a few minutes and set up your profile</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🔍</div>
                    <h3>2. Browse</h3>
                    <p>Explore services, compare prices, and read worker reviews</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">📅</div>
                    <h3>3. Book</h3>
                    <p>Select your preferred date and time for the service</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">✅</div>
                    <h3>4. Enjoy</h3>
                    <p>Professional service delivery and complete satisfaction</p>
                </div>
            </div>
        </div>
        
        <!-- Testimonials -->
        <div class="testimonials">
            <h2>What Our Customers Say 💬</h2>
            <div class="testimonial-grid">
                <div class="testimonial-card">
                    <div class="stars">⭐⭐⭐⭐⭐</div>
                    <p class="testimonial-text">"Excellent plumbing service! The worker was professional and completed the job on time. Highly recommended!"</p>
                    <p class="testimonial-author">- Fatima Khan, Karachi</p>
                </div>
                <div class="testimonial-card">
                    <div class="stars">⭐⭐⭐⭐⭐</div>
                    <p class="testimonial-text">"Best electrical services I've had. Fair pricing and very quick response time. Will definitely book again."</p>
                    <p class="testimonial-author">- Ahmed Ali, Lahore</p>
                </div>
                <div class="testimonial-card">
                    <div class="stars">⭐⭐⭐⭐⭐</div>
                    <p class="testimonial-text">"My AC unit is working perfectly now! The technician was knowledgeable and friendly. Thanks Trusted Home!"</p>
                    <p class="testimonial-author">- Saira Hassan, Islamabad</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Check authentication status
        async function checkAuth() {
            const token = localStorage.getItem('token');
            if (token) {
                try {
                    const response = await fetch('/api/user/me', {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    
                    if (response.ok) {
                        const user = await response.json();
                        document.getElementById('user-info').textContent = `Hello, ${user.full_name || user.email}`;
                        document.getElementById('login-link').style.display = 'none';
                        document.getElementById('logout-link').style.display = 'inline';
                        document.getElementById('hero-title').textContent = `Welcome back, ${user.full_name || user.email}!`;
                        document.getElementById('hero-subtitle').textContent = 'Ready to book a service? Browse our verified professionals now!';
                    } else {
                        logout();
                    }
                } catch (error) {
                    logout();
                }
            }
        }
        
        function logout() {
            localStorage.removeItem('token');
            localStorage.removeItem('userId');
            document.getElementById('user-info').textContent = 'Not logged in';
            document.getElementById('login-link').style.display = 'inline';
            document.getElementById('logout-link').style.display = 'none';
        }
        
        checkAuth();
    </script>
</body>
</html>"""
    
    def get_login_html(self):
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Trusted Home</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .login-form { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
        .form-group { margin-bottom: 1rem; }
        label { display: block; margin-bottom: 0.5rem; font-weight: bold; }
        input { width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 4px; }
        .btn { background: #3498db; color: white; padding: 0.75rem; border: none; border-radius: 4px; cursor: pointer; width: 100%; font-size: 1rem; }
        .btn:hover { background: #2980b9; }
        .link { text-align: center; margin-top: 1rem; }
        .link a { color: #3498db; text-decoration: none; }
        .alert { padding: 0.75rem; border-radius: 4px; margin-bottom: 1rem; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    </style>
</head>
<body>
    <div class="login-form">
        <h2>Login to Your Account</h2>
        <div id="message"></div>
        <form id="loginForm">
            <div class="form-group">
                <label for="email">Email</label>
                <input type="email" id="email" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" required>
            </div>
            <button type="submit" class="btn">Login</button>
        </form>
        <div class="link">
            <a href="/web/register">Don't have an account? Register</a>
        </div>
    </div>
    
    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const message = document.getElementById('message');
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    localStorage.setItem('token', data.access_token);
                    localStorage.setItem('userId', data.user_id);
                    message.innerHTML = '<div class="alert alert-success">Login successful! Redirecting...</div>';
                    setTimeout(() => window.location.href = '/web/dashboard', 1000);
                } else {
                    message.innerHTML = '<div class="alert alert-error">' + data.error + '</div>';
                }
            } catch (error) {
                message.innerHTML = '<div class="alert alert-error">Network error</div>';
            }
        });
    </script>
</body>
</html>"""
    
    def get_register_html(self):
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Register - Trusted Home</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .register-form { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
        .form-group { margin-bottom: 1rem; }
        label { display: block; margin-bottom: 0.5rem; font-weight: bold; }
        input { width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 4px; }
        .btn { background: #27ae60; color: white; padding: 0.75rem; border: none; border-radius: 4px; cursor: pointer; width: 100%; font-size: 1rem; }
        .btn:hover { background: #229954; }
        .link { text-align: center; margin-top: 1rem; }
        .link a { color: #27ae60; text-decoration: none; }
        .alert { padding: 0.75rem; border-radius: 4px; margin-bottom: 1rem; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    </style>
</head>
<body>
    <div class="register-form">
        <h2>Create Your Account</h2>
        <div id="message"></div>
        <form id="registerForm">
            <div class="form-group">
                <label for="fullName">Full Name</label>
                <input type="text" id="fullName" required>
            </div>
            <div class="form-group">
                <label for="email">Email</label>
                <input type="email" id="email" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" required minlength="6">
            </div>
            <button type="submit" class="btn">Register</button>
        </form>
        <div class="link">
            <a href="/web/register">Already have an account? Login</a>
        </div>
    </div>
    
    <script>
        document.getElementById('registerForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const message = document.getElementById('message');
            
            const full_name = document.getElementById('fullName').value;
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            try {
                const response = await fetch('/api/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password, full_name })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    message.innerHTML = '<div class="alert alert-success">Registration successful! Please login.</div>';
                    setTimeout(() => window.location.href = '/web/login', 2000);
                } else {
                    message.innerHTML = '<div class="alert alert-error">' + data.error + '</div>';
                }
            } catch (error) {
                message.innerHTML = '<div class="alert alert-error">Network error</div>';
            }
        });
    </script>
</body>
</html>"""
    
    def get_services_html(self):
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Services - Trusted Home</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 1rem; text-align: center; }
        .nav { background: #34495e; padding: 0.5rem; }
        .nav a { color: white; text-decoration: none; margin: 0 1rem; padding: 0.5rem; border-radius: 4px; }
        .nav a:hover { background: #2980b9; }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .card { background: white; border-radius: 8px; padding: 1.5rem; margin: 1rem 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        
        /* Tab Styling */
        .tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; border-bottom: 2px solid #ddd; flex-wrap: wrap; }
        .tab-btn { background: #ecf0f1; color: #2c3e50; padding: 0.75rem 1.5rem; border: none; border-radius: 4px 4px 0 0; cursor: pointer; font-weight: bold; transition: all 0.3s; }
        .tab-btn:hover { background: #bdc3c7; }
        .tab-btn.active { background: #3498db; color: white; }
        
        .btn { background: #3498db; color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; }
        .btn:hover { background: #2980b9; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 1.5rem; }
        .service-card { border: 1px solid #ddd; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: transform 0.3s; }
        .service-card:hover { transform: translateY(-5px); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
        .service-card h3 { color: #2c3e50; margin-bottom: 0.5rem; }
        .service-card .price { font-weight: bold; color: #27ae60; font-size: 1.3rem; margin: 0.5rem 0; }
        .booking-form { margin-top: 1rem; }
        input[type="datetime-local"] { width: 100%; padding: 0.5rem; margin: 0.5rem 0; border: 1px solid #ddd; border-radius: 4px; }
        
        .worker-info { background: #f8f9fa; padding: 1rem; border-radius: 4px; margin: 1rem 0; border-left: 4px solid #3498db; }
        .worker-info p { margin: 0.3rem 0; font-size: 0.95rem; }
        .rating { color: #f39c12; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏠 Trusted Home Services</h1>
    </div>
    
    <div class="nav">
        <a href="/web/dashboard">Dashboard</a>
        <a href="/web/services">Services</a>
        <a href="/web/bookings">My Bookings</a>
        <a href="/web/profile">Profile</a>
        <span id="user-info" style="color: white; margin-left: auto;">Not logged in</span>
        <a href="#" id="logout-link" style="display:none; color: white;" onclick="logout(); return false;">Logout</a>
        <a href="/web/login" id="login-link">Login</a>
    </div>
    
    <div class="container">
        <div class="card">
            <h2>Browse Services by Category</h2>
            <div class="tabs" id="category-tabs"></div>
            <div class="grid" id="services-list">
                <p>Loading services...</p>
            </div>
        </div>
    </div>
    
    <script>
        let services = [];
        let currentCategory = 'All';
        
        async function checkAuth() {
            const token = localStorage.getItem('token');
            if (token) {
                try {
                    const response = await fetch('/api/user/me', {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    
                    if (response.ok) {
                        const user = await response.json();
                        document.getElementById('user-info').textContent = `Hello, ${user.full_name || user.email}`;
                        document.getElementById('login-link').style.display = 'none';
                        document.getElementById('logout-link').style.display = 'inline';
                    } else {
                        logout();
                    }
                } catch (error) {
                    logout();
                }
            }
        }
        
        function logout() {
            localStorage.removeItem('token');
            localStorage.removeItem('userId');
            document.getElementById('user-info').textContent = 'Not logged in';
            document.getElementById('login-link').style.display = 'inline';
            document.getElementById('logout-link').style.display = 'none';
        }
        
        async function loadServices() {
            try {
                const response = await fetch('/api/services');
                const data = await response.json();
                services = data.services;
                createCategoryTabs();
                displayServices('All');
                checkAuth();
            } catch (error) {
                document.getElementById('services-list').innerHTML = '<p>Error loading services</p>';
            }
        }
        
        function createCategoryTabs() {
            const categories = ['All', ...new Set(services.map(s => s.category))];
            const tabsContainer = document.getElementById('category-tabs');
            
            tabsContainer.innerHTML = categories.map(cat => `
                <button class="tab-btn ${cat === 'All' ? 'active' : ''}" onclick="switchCategory('${cat}')">
                    ${getCategoryName(cat)}
                </button>
            `).join('');
        }
        
        function getCategoryName(category) {
            const names = {
                'All': '📋 All Services',
                'plumber': '🔧 Plumbing',
                'electrician': '⚡ Electrical',
                'ac_repair': '❄️ AC Repair',
                'cleaning': '🧹 Cleaning'
            };
            return names[category] || category;
        }
        
        function switchCategory(category) {
            currentCategory = category;
            
            // Update active tab
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.remove('active');
                if (btn.textContent.includes(getCategoryName(category).split(' ').pop())) {
                    btn.classList.add('active');
                }
            });
            
            displayServices(category);
        }
        
        function displayServices(category) {
            const filtered = category === 'All' 
                ? services 
                : services.filter(s => s.category === category);
            
            if (filtered.length === 0) {
                document.getElementById('services-list').innerHTML = '<p>No services available in this category.</p>';
                return;
            }
            
            const list = document.getElementById('services-list');
            list.innerHTML = filtered.map(s => `
                <div class="service-card">
                    <h3>${s.name}</h3>
                    
                    <div class="worker-info">
                        <p><strong>👨‍🔧 Worker:</strong> ${s.worker.name}</p>
                        <p><strong>📅 Experience:</strong> ${s.worker.experience_years} years</p>
                        <p class="rating"><strong>⭐ Rating:</strong> ${s.worker.rating}/5.0</p>
                        <p><strong>🎯 Specialties:</strong> ${s.worker.specialties}</p>
                        <p><strong>📍 Location:</strong> ${s.worker.city}</p>
                        <p><strong>📞 Phone:</strong> ${s.worker.phone}</p>
                    </div>
                    
                    <p style="font-style: italic; color: #555;">${s.description}</p>
                    <div class="price">💰 Rs. ${s.price}</div>
                    
                    <button class="btn" onclick="openBookingModal(${s.id}, '${s.name}', ${s.price})" style="width: 100%; margin-top: 1rem;">📅 Book Now</button>
                </div>
            `).join('');
        }
        
        async function bookService(serviceId) {
            const token = localStorage.getItem('token');
            if (!token) {
                alert('Please login to book services');
                window.location.href = '/web/login';
                return;
            }
            
            const locationInput = document.getElementById(`location-${serviceId}`);
            const dateInput = document.getElementById(`date-${serviceId}`);
            const location = locationInput.value.trim();
            const bookingDate = dateInput.value;
            
            // Validation
            if (!location) {
                alert('Please enter the service location');
                locationInput.focus();
                return;
            }
            
            if (!bookingDate) {
                alert('Please select a date and time');
                dateInput.focus();
                return;
            }
            
            try {
                // Show loading state
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = '⏳ Booking...';
                btn.disabled = true;
                
                const response = await fetch('/api/bookings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        service_id: serviceId,
                        booking_date: bookingDate,
                        location: location
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    // Show success message with modal
                    showBookingSuccess(data.booking);
                    // Reset form
                    locationInput.value = '';
                    dateInput.value = '';
                } else {
                    alert('Error: ' + (data.error || 'Unable to book service'));
                }
                
                // Restore button
                btn.textContent = originalText;
                btn.disabled = false;
                
            } catch (error) {
                console.error('Booking error:', error);
                alert('Network error while booking service');
                event.target.textContent = 'Book Now';
                event.target.disabled = false;
            }
        }
        
        function showBookingSuccess(booking) {
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
            `;
            
            const content = document.createElement('div');
            content.style.cssText = `
                background: white;
                padding: 2rem;
                border-radius: 8px;
                max-width: 500px;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            `;
            
            content.innerHTML = `
                <div style="font-size: 3rem; margin-bottom: 1rem;">✅</div>
                <h2 style="color: #27ae60; margin-bottom: 1rem;">Booking Confirmed!</h2>
                <p style="color: #555; margin-bottom: 1.5rem;">
                    Your booking has been successfully created and saved to your account.
                </p>
                <div style="background: #f9f9f9; padding: 1rem; border-radius: 4px; margin-bottom: 1.5rem; text-align: left;">
                    <p><strong>Booking ID:</strong> #${booking.id}</p>
                    <p><strong>Status:</strong> <span style="color: #f39c12; font-weight: bold;">Pending</span></p>
                    <p><strong>Price:</strong> Rs. ${booking.price}</p>
                </div>
                <p style="color: #666; font-size: 0.9rem; margin-bottom: 1.5rem;">
                    You can view and manage your booking in the "My Bookings" section.
                </p>
                <button onclick="window.location.href='/web/bookings'" style="
                    background: #27ae60;
                    color: white;
                    border: none;
                    padding: 0.75rem 2rem;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 1rem;
                    margin-right: 0.5rem;
                ">View My Bookings</button>
                <button onclick="this.parentElement.parentElement.remove()" style="
                    background: #ecf0f1;
                    color: #2c3e50;
                    border: none;
                    padding: 0.75rem 2rem;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 1rem;
                ">Continue Browsing</button>
            `;
            
            modal.appendChild(content);
            document.body.appendChild(modal);
            
            // Close on background click
            modal.addEventListener('click', (e) => {
                if (e.target === modal) modal.remove();
            });
        }
        
        // Booking Modal Functions
        function openBookingModal(serviceId, serviceName, price) {
            const modal = document.getElementById('booking-modal');
            const form = document.getElementById('booking-form');
            
            // Store service info in form
            form.dataset.serviceId = serviceId;
            form.dataset.serviceName = serviceName;
            form.dataset.price = price;
            
            // Update modal title
            document.getElementById('modal-service-name').textContent = serviceName;
            
            // Reset form
            form.reset();
            
            // Show modal
            modal.style.display = 'flex';
        }
        
        function closeBookingModal() {
            document.getElementById('booking-modal').style.display = 'none';
        }
        
        function submitBookingForm() {
            const form = document.getElementById('booking-form');
            const fullName = document.getElementById('full-name').value.trim();
            const phone = document.getElementById('phone').value.trim();
            const address = document.getElementById('address').value.trim();
            const houseNumber = document.getElementById('house-number').value.trim();
            const date = document.getElementById('booking-date').value;
            const time = document.getElementById('booking-time').value;
            
            // Validation
            if (!fullName) { alert('Please enter your full name'); return; }
            if (!phone || phone.length < 10) { alert('Please enter a valid phone number (at least 10 digits)'); return; }
            if (!address) { alert('Please enter your address'); return; }
            if (!houseNumber) { alert('Please enter your house number'); return; }
            if (!date) { alert('Please select a date'); return; }
            if (!time) { alert('Please select a time'); return; }
            
            const serviceId = form.dataset.serviceId;
            const bookingDateTime = date + 'T' + time;
            
            const token = localStorage.getItem('token');
            
            fetch('/api/bookings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + token
                },
                body: JSON.stringify({
                    service_id: parseInt(serviceId),
                    booking_date: bookingDateTime,
                    location: address,
                    house_number: houseNumber,
                    full_name: fullName,
                    phone_number: phone
                })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    closeBookingModal();
                    showBookingSuccess(data.booking);
                } else {
                    alert('Error: ' + data.message);
                }
            })
            .catch(err => alert('Booking failed: ' + err));
        }
        
        // Modal HTML
        const bookingModalHTML = `
            <div id="booking-modal" style="
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 1001;
                justify-content: center;
                align-items: center;
            ">
                <div style="
                    background: white;
                    padding: 2rem;
                    border-radius: 8px;
                    max-width: 500px;
                    width: 90%;
                    max-height: 90vh;
                    overflow-y: auto;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.2);
                ">
                    <h2 style="margin-bottom: 0.5rem; color: #2c3e50;">Book Service</h2>
                    <p style="color: #7f8c8d; margin-bottom: 1.5rem;" id="modal-service-name"></p>
                    
                    <form id="booking-form" style="display: grid; gap: 1rem;">
                        <div>
                            <label style="display: block; font-weight: bold; margin-bottom: 0.4rem;">Full Name *</label>
                            <input type="text" id="full-name" placeholder="Enter your full name" required style="width: 100%; padding: 0.5rem; border: 1px solid #bdc3c7; border-radius: 4px;">
                        </div>
                        
                        <div>
                            <label style="display: block; font-weight: bold; margin-bottom: 0.4rem;">Phone Number *</label>
                            <input type="tel" id="phone" placeholder="Enter your phone number" required style="width: 100%; padding: 0.5rem; border: 1px solid #bdc3c7; border-radius: 4px;">
                        </div>
                        
                        <div>
                            <label style="display: block; font-weight: bold; margin-bottom: 0.4rem;">Address *</label>
                            <input type="text" id="address" placeholder="Enter your address" required style="width: 100%; padding: 0.5rem; border: 1px solid #bdc3c7; border-radius: 4px;">
                        </div>
                        
                        <div>
                            <label style="display: block; font-weight: bold; margin-bottom: 0.4rem;">House Number *</label>
                            <input type="text" id="house-number" placeholder="Enter your house number" required style="width: 100%; padding: 0.5rem; border: 1px solid #bdc3c7; border-radius: 4px;">
                        </div>
                        
                        <div>
                            <label style="display: block; font-weight: bold; margin-bottom: 0.4rem;">Date *</label>
                            <input type="date" id="booking-date" required style="width: 100%; padding: 0.5rem; border: 1px solid #bdc3c7; border-radius: 4px;">
                        </div>
                        
                        <div>
                            <label style="display: block; font-weight: bold; margin-bottom: 0.4rem;">Time *</label>
                            <input type="time" id="booking-time" required style="width: 100%; padding: 0.5rem; border: 1px solid #bdc3c7; border-radius: 4px;">
                        </div>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem;">
                            <button type="button" onclick="submitBookingForm()" style="
                                background: #27ae60;
                                color: white;
                                border: none;
                                padding: 0.75rem;
                                border-radius: 4px;
                                cursor: pointer;
                                font-weight: bold;
                                font-size: 1rem;
                            ">✓ Confirm Booking</button>
                            <button type="button" onclick="closeBookingModal()" style="
                                background: #ecf0f1;
                                color: #2c3e50;
                                border: none;
                                padding: 0.75rem;
                                border-radius: 4px;
                                cursor: pointer;
                                font-weight: bold;
                                font-size: 1rem;
                            ">Cancel</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        // Append modal to page
        document.body.insertAdjacentHTML('beforeend', bookingModalHTML);
        
        // Close modal when clicking outside
        document.getElementById('booking-modal').addEventListener('click', (e) => {
            if (e.target.id === 'booking-modal') closeBookingModal();
        });
        
        loadServices();
    </script>
</body>
</html>"""
    
    def get_bookings_html(self):
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Bookings - Trusted Home</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 1rem; text-align: center; }
        .nav { background: #34495e; padding: 0.5rem; }
        .nav a { color: white; text-decoration: none; margin: 0 1rem; padding: 0.5rem; border-radius: 4px; }
        .nav a:hover { background: #2980b9; }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .card { background: white; border-radius: 8px; padding: 1.5rem; margin: 1rem 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        
        /* Status Filter Tabs */
        .filter-tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
        .filter-btn { background: #ecf0f1; color: #2c3e50; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; transition: all 0.3s; }
        .filter-btn:hover { background: #bdc3c7; }
        .filter-btn.active { background: #3498db; color: white; }
        
        .booking-item { 
            border: 2px solid #ddd; 
            padding: 1.5rem; 
            margin: 1rem 0; 
            border-radius: 8px; 
            transition: all 0.3s;
            background: #f9f9f9;
        }
        .booking-item:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .booking-item.status-completed { border-left: 4px solid #27ae60; background: #d4edda; }
        .booking-item.status-pending { border-left: 4px solid #f39c12; background: #fff3cd; }
        .booking-item.status-cancelled { border-left: 4px solid #e74c3c; background: #f8d7da; }
        
        .booking-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
        .status-cancelled { background: #e74c3c; color: white; }

        .booking-header h3 { color: #2c3e50; margin: 0; }
        
        .status { padding: 0.4rem 0.8rem; border-radius: 20px; font-size: 0.85rem; font-weight: bold; display: inline-block; }
        .status-pending { background: #f39c12; color: white; }
        .status-completed { background: #27ae60; color: white; }
        
        .booking-details { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1rem 0; }
        .detail-item { background: white; padding: 0.75rem; border-radius: 4px; }
        .detail-item strong { color: #2c3e50; }
        
        .btn { background: #3498db; color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; margin: 0.25rem; }
        .btn:hover { background: #2980b9; }
        .btn-complete { background: #27ae60; }
        .btn-complete:hover { background: #229954; }
        .btn-cancel { background: #e74c3c; }
        .btn-cancel:hover { background: #c0392b; }
        .btn-delete { background: #95a5a6; }
        .btn-delete:hover { background: #7f8c8d; }
        
        .progress-bar { width: 100%; height: 8px; background: #ecf0f1; border-radius: 4px; margin: 1rem 0; overflow: hidden; }
        .progress-fill { height: 100%; background: #3498db; transition: width 0.3s; }
        .progress-fill.completed { background: #27ae60; width: 100%; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📅 My Bookings</h1>
    </div>
    
    <div class="nav">
        <a href="/web/dashboard">Dashboard</a>
        <a href="/web/services">Services</a>
        <a href="/web/bookings">My Bookings</a>
        <a href="/web/profile">Profile</a>
        <span id="user-info" style="color: white; margin-left: auto;">Not logged in</span>
        <a href="#" id="logout-link" style="display:none; color: white;" onclick="logout(); return false;">Logout</a>
        <a href="/web/login" id="login-link">Login</a>
    </div>
    
    <div class="container">
        <div class="card">
            <h2>Your Bookings</h2>
            
            <div class="filter-tabs">
                <button class="filter-btn active" onclick="filterBookings('Active', event)">📋 Active Bookings</button>
                <button class="filter-btn" onclick="filterBookings('completed', event)">🎉 Completed</button>
                <button class="filter-btn" onclick="filterBookings('cancelled', event)">❌ Cancelled</button>
            </div>
            
            <div id="bookings-list">
                <p>Loading bookings...</p>
            </div>
        </div>
    </div>
    
    <script>
        let allBookings = [];
        let currentFilter = 'Active';
        
        async function checkAuth() {
            const token = localStorage.getItem('token');
            if (token) {
                try {
                    const response = await fetch('/api/user/me', {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    
                    if (response.ok) {
                        const user = await response.json();
                        document.getElementById('user-info').textContent = `Hello, ${user.full_name || user.email}`;
                        document.getElementById('login-link').style.display = 'none';
                        document.getElementById('logout-link').style.display = 'inline';
                    } else {
                        logout();
                    }
                } catch (error) {
                    logout();
                }
            }
        }
        
        function logout() {
            localStorage.removeItem('token');
            localStorage.removeItem('userId');
            document.getElementById('user-info').textContent = 'Not logged in';
            document.getElementById('login-link').style.display = 'inline';
            document.getElementById('logout-link').style.display = 'none';
        }
        
        async function loadBookings() {
            const token = localStorage.getItem('token');
            if (!token) {
                document.getElementById('bookings-list').innerHTML = '<p>Please <a href="/web/login">login</a> to view your bookings</p>';
                return;
            }
            
            try {
                const response = await fetch('/api/bookings', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const data = await response.json();
                
                if (response.ok) {
                    allBookings = data.bookings;
                    displayBookings(currentFilter || 'Active');
                    checkAuth();
                } else {
                    document.getElementById('bookings-list').innerHTML = '<p>Error loading bookings</p>';
                }
            } catch (error) {
                document.getElementById('bookings-list').innerHTML = '<p>Network error</p>';
            }
        }
        
        function filterBookings(status, evt) {
            currentFilter = status;
            
            // Update active button
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            const target = (evt && evt.target) || window.event && window.event.target;
            if (target) {
                target.classList.add('active');
            }
            
            displayBookings(status);
        }
        
        function displayBookings(filter) {
            let filtered;
            
            if (filter === 'Active') {
                // Show only pending bookings (not completed or cancelled)
                filtered = allBookings.filter(b => b.status === 'pending');
            } else if (filter === 'completed') {
                // Show only completed bookings
                filtered = allBookings.filter(b => b.status === 'completed');
            } else if (filter === 'cancelled') {
                // Show only cancelled bookings
                filtered = allBookings.filter(b => b.status === 'cancelled');
            } else {
                // Default to active
                filtered = allBookings.filter(b => b.status === 'pending');
            }
            
            const list = document.getElementById('bookings-list');
            
            if (filtered.length === 0) {
                const emptyMessages = {
                    'Active': 'No active bookings. <a href="/web/services">Book a service</a>',
                    'completed': 'No completed bookings yet.',
                    'cancelled': 'No cancelled bookings.'
                };
                list.innerHTML = '<p>' + (emptyMessages[filter] || 'No bookings found') + '</p>';
                return;
            }
            
            list.innerHTML = filtered.map(b => {
                const bookingDate = new Date(b.booking_date);
                const createdDate = new Date(b.created_at);
                const statusClass = b.status || 'pending';
                
                // Determine which buttons to show
                let actionButtons = '';
                if (b.status === 'pending') {
                    // Only show buttons for active (pending) bookings
                    actionButtons = `
                        <button class="btn btn-complete" onclick="markComplete(${b.id})">✅ Mark as Completed</button>
                        <button class="btn btn-cancel" onclick="cancelBooking(${b.id})">❌ Cancel Booking</button>
                    `;
                } else if (b.status === 'completed') {
                    actionButtons = `
                        <p style="color: #27ae60; font-weight: bold;">✅ Service Completed!</p>
                        <button class="btn btn-delete" onclick="deleteBooking(${b.id})">🗑️ Delete</button>
                    `;
                } else if (b.status === 'cancelled') {
                    actionButtons = `
                        <p style="color: #e74c3c; font-weight: bold;">❌ Booking Cancelled</p>
                        <button class="btn btn-delete" onclick="deleteBooking(${b.id})">🗑️ Delete</button>
                    `;
                }
                
                return `
                    <div class="booking-item status-${statusClass}">
                        <div class="booking-header">
                            <div>
                                <h3>🔧 ${b.service_name}</h3>
                                <p style="margin: 0.3rem 0; color: #666;">Booking #${b.id}</p>
                            </div>
                            <span class="status status-${statusClass}">${(b.status || 'pending').toUpperCase()}</span>
                        </div>
                        
                        <div class="progress-bar">
                            <div class="progress-fill ${b.status === 'completed' ? 'completed' : ''}" 
                                 style="width: ${b.status === 'pending' ? '50%' : '100%'};"></div>
                        </div>
                        
                        <div class="booking-details">
                            <div class="detail-item">
                                <strong>👨‍🔧 Worker</strong>
                                <p>${b.worker_name || 'Not assigned yet'}</p>
                            </div>
                            <div class="detail-item">
                                <strong>💰 Price</strong>
                                <p>Rs. ${b.price}</p>
                            </div>
                            <div class="detail-item">
                                <strong>📅 Booking Date</strong>
                                <p>${bookingDate.toLocaleString()}</p>
                            </div>
                            <div class="detail-item">
                                <strong>🕐 Created</strong>
                                <p>${createdDate.toLocaleString()}</p>
                            </div>
                        </div>
                        
                        <div style="margin-top: 1rem; display: flex; gap: 1rem; flex-wrap: wrap;">
                            ${actionButtons}
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        async function markComplete(bookingId) {
            if (!confirm('Are you sure you want to mark this booking as completed?')) {
                return;
            }
            
            const token = localStorage.getItem('token');
            if (!token) {
                alert('Please login to complete bookings.');
                window.location.href = '/web/login';
                return;
            }
            
            console.log('Completing booking', bookingId);
            
            try {
                const response = await fetch(`/api/bookings/${bookingId}/complete`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                
                const data = await response.json();
                console.log('Complete response', data);
                
                if (response.ok) {
                    // Reload bookings from server to ensure UI is in sync
                    await loadBookings();
                    alert('Booking marked as completed! 🎉');
                } else {
                    alert('Error: ' + (data.error || 'Unable to complete booking'));
                }
            } catch (error) {
                console.error('Complete error', error);
                alert('Network error while completing booking');
            }
        }
        
        async function cancelBooking(bookingId) {
            if (!confirm('Are you sure you want to cancel this booking?')) {
                return;
            }
            
            const token = localStorage.getItem('token');
            if (!token) {
                alert('Please login to cancel bookings.');
                window.location.href = '/web/login';
                return;
            }
            
            console.log('Cancelling booking', bookingId);
            
            try {
                const response = await fetch(`/api/bookings/${bookingId}/cancel`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                
                const data = await response.json();
                console.log('Cancel response', data);
                
                if (response.ok) {
                    // Reload bookings from server to ensure UI is in sync
                    await loadBookings();
                    alert('Booking cancelled successfully! The booking has been removed from your active bookings list. ❌');
                } else {
                    alert('Error: ' + (data.error || 'Unable to cancel booking'));
                }
            } catch (error) {
                console.error('Cancel error', error);
                alert('Network error while cancelling booking');
            }
        }
        
        async function deleteBooking(bookingId) {
            if (!confirm('Are you sure you want to permanently delete this booking? This action cannot be undone.')) {
                return;
            }
            
            const token = localStorage.getItem('token');
            if (!token) {
                alert('Please login to delete bookings.');
                window.location.href = '/web/login';
                return;
            }
            
            console.log('Deleting booking', bookingId);
            
            try {
                const response = await fetch(`/api/bookings/${bookingId}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                
                const data = await response.json();
                console.log('Delete response', data);
                
                if (response.ok) {
                    // Reload bookings from server
                    await loadBookings();
                    alert('Booking deleted successfully! ✅');
                } else {
                    alert('Error: ' + (data.error || 'Unable to delete booking'));
                }
            } catch (error) {
                console.error('Delete error', error);
                alert('Network error while deleting booking');
            }
        }
        
        loadBookings();
    </script>
</body>
</html>"""

    def get_profile_html(self):
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Profile - Trusted Home</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 1rem; text-align: center; }
        .nav { background: #34495e; padding: 0.5rem; display: flex; flex-wrap: wrap; }
        .nav a { color: white; text-decoration: none; margin: 0 1rem; padding: 0.5rem; border-radius: 4px; }
        .nav a:hover { background: #2980b9; }
        .container { max-width: 900px; margin: 2rem auto; padding: 0 1rem; }
        .card { background: white; border-radius: 8px; padding: 2rem; margin: 1rem 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        
        .profile-header { display: flex; align-items: center; gap: 2rem; margin-bottom: 2rem; padding-bottom: 2rem; border-bottom: 2px solid #ecf0f1; }
        .avatar { width: 120px; height: 120px; border-radius: 50%; background: #3498db; color: white; display: flex; align-items: center; justify-content: center; font-size: 48px; }
        .user-basic h1 { color: #2c3e50; margin-bottom: 0.5rem; }
        .user-basic p { color: #7f8c8d; margin: 0.3rem 0; }
        
        .profile-section { margin: 2rem 0; }
        .profile-section h2 { color: #2c3e50; margin-bottom: 1rem; border-bottom: 2px solid #3498db; padding-bottom: 0.5rem; }
        
        .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; }
        .info-item { background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #3498db; }
        .info-item label { font-weight: bold; color: #2c3e50; display: block; margin-bottom: 0.5rem; }
        .info-item p { color: #555; }
        
        .btn { background: #3498db; color: white; padding: 0.75rem 1.5rem; border: none; border-radius: 4px; cursor: pointer; font-size: 1rem; }
        .btn:hover { background: #2980b9; }
        .btn-logout { background: #e74c3c; }
        .btn-logout:hover { background: #c0392b; }
        .btn-group { display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 2rem; }
        
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1rem 0; }
        .stat-card { background: linear-gradient(135deg, #3498db, #2980b9); color: white; padding: 1.5rem; border-radius: 8px; text-align: center; }
        .stat-number { font-size: 2rem; font-weight: bold; }
        .stat-label { opacity: 0.9; margin-top: 0.5rem; }
        
        .status { display: inline-block; padding: 0.4rem 0.8rem; border-radius: 20px; font-size: 0.85rem; font-weight: bold; }
        .status-active { background: #27ae60; color: white; }
        
        /* Modal Styles */
        .modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
        .modal-content { background: white; padding: 2rem; border-radius: 8px; max-width: 400px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .modal-header { font-size: 1.5rem; color: #2c3e50; margin-bottom: 1.5rem; border-bottom: 2px solid #ecf0f1; padding-bottom: 1rem; }
        .form-group { margin-bottom: 1.5rem; }
        .form-group label { display: block; color: #2c3e50; font-weight: bold; margin-bottom: 0.5rem; }
        .form-group input { width: 100%; padding: 0.75rem; border: 1px solid #bdc3c7; border-radius: 4px; font-size: 1rem; box-sizing: border-box; }
        .form-group input:focus { outline: none; border-color: #3498db; box-shadow: 0 0 5px rgba(52, 152, 219, 0.3); }
        .form-buttons { display: flex; gap: 1rem; justify-content: flex-end; }
        .btn-submit { background: #27ae60; color: white; padding: 0.75rem 1.5rem; border: none; border-radius: 4px; cursor: pointer; font-size: 1rem; }
        .btn-submit:hover { background: #229954; }
        .btn-cancel { background: #ecf0f1; color: #2c3e50; padding: 0.75rem 1.5rem; border: none; border-radius: 4px; cursor: pointer; font-size: 1rem; }
        .btn-cancel:hover { background: #bdc3c7; }
        .error-message { color: #e74c3c; font-size: 0.9rem; margin-top: 0.3rem; }
        .success-message { color: #27ae60; font-size: 0.9rem; margin-top: 0.3rem; }
    </style>
</head>
<body>
    <div class="header">
        <h1>👤 My Profile</h1>
    </div>
    
    <div class="nav">
        <a href="/web/dashboard">Dashboard</a>
        <a href="/web/services">Services</a>
        <a href="/web/bookings">My Bookings</a>
        <a href="/web/profile">Profile</a>
        <span id="user-info" style="color: white; margin-left: auto;">Loading...</span>
        <a href="#" id="logout-link" style="display:none; color: white;" onclick="logout(); return false;">Logout</a>
    </div>
    
    <div class="container">
        <div class="card">
            <div class="profile-header">
                <div class="avatar" id="avatar">
                    <span>👤</span>
                </div>
                <div class="user-basic">
                    <h1 id="user-name">Loading...</h1>
                    <p id="user-email">Loading...</p>
                    <p><span class="status status-active">✅ Active Member</span></p>
                </div>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number" id="booking-count">0</div>
                    <div class="stat-label">Total Bookings</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #27ae60, #229954);">
                    <div class="stat-number" id="completed-count">0</div>
                    <div class="stat-label">Completed Services</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #f39c12, #e67e22);">
                    <div class="stat-number" id="pending-count">0</div>
                    <div class="stat-label">Pending Services</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="profile-section">
                <h2>📋 Profile Information</h2>
                <div class="info-grid">
                    <div class="info-item">
                        <label>Full Name</label>
                        <p id="profile-name">Loading...</p>
                    </div>
                    <div class="info-item">
                        <label>Email Address</label>
                        <p id="profile-email">Loading...</p>
                    </div>
                    <div class="info-item">
                        <label>Phone Number</label>
                        <p id="profile-phone">Not provided</p>
                    </div>
                    <div class="info-item">
                        <label>City / Location</label>
                        <p id="profile-city">Not provided</p>
                    </div>
                    <div class="info-item">
                        <label>Account Role</label>
                        <p id="profile-role">User</p>
                    </div>
                    <div class="info-item">
                        <label>Member Since</label>
                        <p id="profile-created">Loading...</p>
                    </div>
                </div>
            </div>
            
            <div class="profile-section">
                <h2>🔐 Account Settings</h2>
                <div class="btn-group">
                    <button class="btn" onclick="openChangePasswordModal()">🔑 Change Password</button>
                    <button class="btn btn-logout" onclick="logout(); return false;">🚪 Logout</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Change Password Modal -->
    <div id="changePasswordModal" class="modal" style="display: none;">
        <div class="modal-content">
            <div class="modal-header">🔐 Change Password</div>
            <form onsubmit="submitChangePassword(event)">
                <div class="form-group">
                    <label for="currentPassword">Current Password:</label>
                    <input type="password" id="currentPassword" required>
                    <div id="currentError" class="error-message"></div>
                </div>
                <div class="form-group">
                    <label for="newPassword">New Password:</label>
                    <input type="password" id="newPassword" required>
                    <div id="newError" class="error-message"></div>
                </div>
                <div class="form-group">
                    <label for="confirmPassword">Confirm Password:</label>
                    <input type="password" id="confirmPassword" required>
                    <div id="confirmError" class="error-message"></div>
                </div>
                <div class="form-buttons">
                    <button type="button" class="btn-cancel" onclick="closeChangePasswordModal()">Cancel</button>
                    <button type="submit" class="btn-submit">Update Password</button>
                </div>
                <div id="successMessage" class="success-message"></div>
            </form>
        </div>
    </div>
    
    <script>
        async function loadProfile() {
            const token = localStorage.getItem('token');
            if (!token) {
                window.location.href = '/web/login';
                return;
            }
            
            try {
                const response = await fetch('/api/user/me', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                
                if (!response.ok) {
                    logout();
                    return;
                }
                
                const user = await response.json();
                displayProfile(user);
                await loadBookingStats(token);
                
            } catch (error) {
                alert('Error loading profile');
                logout();
            }
        }
        
        function displayProfile(user) {
            document.getElementById('user-name').textContent = user.full_name || user.email;
            document.getElementById('user-email').textContent = user.email;
            document.getElementById('user-info').textContent = `Hello, ${user.full_name || user.email}!`;
            document.getElementById('logout-link').style.display = 'inline';
            
            document.getElementById('profile-name').textContent = user.full_name || 'Not provided';
            document.getElementById('profile-email').textContent = user.email;
            document.getElementById('profile-phone').textContent = user.phone || 'Not provided';
            document.getElementById('profile-city').textContent = user.city || 'Not provided';
            document.getElementById('profile-role').textContent = (user.role || 'user').charAt(0).toUpperCase() + (user.role || 'user').slice(1);
            
            // Format created date
            const createdDate = new Date(user.created_at || new Date());
            document.getElementById('profile-created').textContent = createdDate.toLocaleDateString();
            
            // Set avatar initial
            const firstLetter = (user.full_name || user.email).charAt(0).toUpperCase();
            const colors = ['#3498db', '#27ae60', '#e74c3c', '#f39c12', '#9b59b6'];
            const colorIndex = firstLetter.charCodeAt(0) % colors.length;
            const avatar = document.getElementById('avatar');
            avatar.textContent = firstLetter;
            avatar.style.background = colors[colorIndex];
        }
        
        async function loadBookingStats(token) {
            try {
                const response = await fetch('/api/bookings', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    const bookings = data.bookings || [];
                    
                    const totalCount = bookings.length;
                    const completedCount = bookings.filter(b => b.status === 'completed').length;
                    const pendingCount = bookings.filter(b => b.status === 'pending' || b.status === 'confirmed').length;
                    
                    document.getElementById('booking-count').textContent = totalCount;
                    document.getElementById('completed-count').textContent = completedCount;
                    document.getElementById('pending-count').textContent = pendingCount;
                }
            } catch (error) {
                console.log('Could not load booking stats');
            }
        }
        
        function logout() {
            localStorage.removeItem('token');
            localStorage.removeItem('userId');
            window.location.href = '/web/login';
        }
        
        function openChangePasswordModal() {
            document.getElementById('changePasswordModal').style.display = 'flex';
            // Clear form
            document.getElementById('currentPassword').value = '';
            document.getElementById('newPassword').value = '';
            document.getElementById('confirmPassword').value = '';
            document.getElementById('currentError').textContent = '';
            document.getElementById('newError').textContent = '';
            document.getElementById('confirmError').textContent = '';
            document.getElementById('successMessage').textContent = '';
        }
        
        function closeChangePasswordModal() {
            document.getElementById('changePasswordModal').style.display = 'none';
        }
        
        // Close modal on background click
        document.addEventListener('DOMContentLoaded', function() {
            const modal = document.getElementById('changePasswordModal');
            if (modal) {
                modal.addEventListener('click', function(e) {
                    if (e.target === modal) closeChangePasswordModal();
                });
            }
        });
        
        async function submitChangePassword(event) {
            event.preventDefault();
            
            const currentPassword = document.getElementById('currentPassword').value;
            const newPassword = document.getElementById('newPassword').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            
            // Clear previous errors
            document.getElementById('currentError').textContent = '';
            document.getElementById('newError').textContent = '';
            document.getElementById('confirmError').textContent = '';
            document.getElementById('successMessage').textContent = '';
            
            // Validation
            let hasError = false;
            if (!currentPassword) {
                document.getElementById('currentError').textContent = 'Current password is required';
                hasError = true;
            }
            if (!newPassword) {
                document.getElementById('newError').textContent = 'New password is required';
                hasError = true;
            }
            if (newPassword.length < 6) {
                document.getElementById('newError').textContent = 'Password must be at least 6 characters';
                hasError = true;
            }
            if (newPassword !== confirmPassword) {
                document.getElementById('confirmError').textContent = 'Passwords do not match';
                hasError = true;
            }
            if (currentPassword === newPassword) {
                document.getElementById('newError').textContent = 'New password must be different from current password';
                hasError = true;
            }
            
            if (hasError) return;
            
            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/api/change-password', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        current_password: currentPassword,
                        new_password: newPassword
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    document.getElementById('successMessage').textContent = '✅ Password updated successfully!';
                    document.getElementById('successMessage').style.color = '#27ae60';
                    setTimeout(() => {
                        closeChangePasswordModal();
                    }, 1500);
                } else {
                    document.getElementById('currentError').textContent = data.error || 'Failed to update password';
                }
            } catch (error) {
                console.error('Error:', error);
                document.getElementById('currentError').textContent = 'Network error. Please try again.';
            }
        }
        
        loadProfile();
    </script>
</body>
</html>"""

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {format % args}")

# ==================== MAIN ====================
if __name__ == '__main__':
    port = 5000
    
    # Find available port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while sock.connect_ex(('127.0.0.1', port)) == 0:
        port += 1
    sock.close()
    
    server = HTTPServer(('0.0.0.0', port), TrustedHomeHandler)
    
    print(f"Trusted Home Platform Server")
    print(f"Running on http://localhost:{port}")
    print(f"Test: user@example.com / User@12345")
    print(f"Press Ctrl+C to stop")
    print("")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
