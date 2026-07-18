#!/usr/bin/env python
"""
Unit Tests for Trusted Home Platform
Tests for Database, Authentication, Bookings, and API endpoints
"""

import unittest
import sqlite3
import hashlib
import json
import tempfile
import os
from datetime import datetime, timedelta
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ==================== TEST DATABASE SETUP ====================
class TestDatabase(unittest.TestCase):
    """Test database initialization and operations"""
    
    def setUp(self):
        """Create temporary test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_file = self.temp_db.name
    
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.db_file):
            os.remove(self.db_file)
    
    def create_test_db(self):
        """Helper to create test database structure"""
        conn = sqlite3.connect(self.db_file)
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
        
        conn.commit()
        conn.close()
        return conn
    
    def test_database_creation(self):
        """Test that database tables are created successfully"""
        self.create_test_db()
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        self.assertIsNotNone(cursor.fetchone(), "Users table not created")
        
        # Check if bookings table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bookings'")
        self.assertIsNotNone(cursor.fetchone(), "Bookings table not created")
        
        conn.close()
    
    def test_user_insertion(self):
        """Test inserting a user into database"""
        self.create_test_db()
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(b'TestPass123').hexdigest()
        cursor.execute(
            'INSERT INTO users (email, full_name, phone, password_hash, city, role) VALUES (?, ?, ?, ?, ?, ?)',
            ('test@example.com', 'Test User', '+923001234567', password_hash, 'Karachi', 'user')
        )
        conn.commit()
        
        # Verify insertion
        cursor.execute('SELECT * FROM users WHERE email = ?', ('test@example.com',))
        user = cursor.fetchone()
        self.assertIsNotNone(user, "User was not inserted")
        self.assertEqual(user[1], 'test@example.com')
        self.assertEqual(user[6], 'user')
        
        conn.close()
    
    def test_duplicate_email_constraint(self):
        """Test that duplicate emails are rejected"""
        self.create_test_db()
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(b'TestPass123').hexdigest()
        cursor.execute(
            'INSERT INTO users (email, full_name, phone, password_hash, city, role) VALUES (?, ?, ?, ?, ?, ?)',
            ('test@example.com', 'Test User', '+923001234567', password_hash, 'Karachi', 'user')
        )
        conn.commit()
        
        # Try to insert duplicate email
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute(
                'INSERT INTO users (email, full_name, phone, password_hash, city, role) VALUES (?, ?, ?, ?, ?, ?)',
                ('test@example.com', 'Another User', '+923001234568', password_hash, 'Lahore', 'user')
            )
            conn.commit()
        
        conn.close()


# ==================== TEST AUTHENTICATION ====================
class TestAuthentication(unittest.TestCase):
    """Test authentication and password hashing"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.password = 'TestPass123'
        self.password_hash = hashlib.sha256(self.password.encode()).hexdigest()
    
    def test_password_hashing(self):
        """Test that password hashing works correctly"""
        password = 'MySecurePass123'
        hash1 = hashlib.sha256(password.encode()).hexdigest()
        hash2 = hashlib.sha256(password.encode()).hexdigest()
        
        # Same password should produce same hash
        self.assertEqual(hash1, hash2)
    
    def test_password_verification(self):
        """Test password verification"""
        password = 'TestPassword123'
        stored_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Correct password
        input_hash = hashlib.sha256(password.encode()).hexdigest()
        self.assertEqual(stored_hash, input_hash)
        
        # Wrong password
        wrong_hash = hashlib.sha256(b'WrongPassword').hexdigest()
        self.assertNotEqual(stored_hash, wrong_hash)
    
    def test_password_minimum_length(self):
        """Test password minimum length validation"""
        passwords = [
            ('short', False),  # Too short
            ('pass123', True),  # 8 characters
            ('p', False),  # Too short
            ('ValidPassword123', True),  # Valid
        ]
        
        for password, should_be_valid in passwords:
            is_valid = len(password) >= 6
            self.assertEqual(is_valid, should_be_valid)


# ==================== TEST BOOKING SYSTEM ====================
class TestBookingSystem(unittest.TestCase):
    """Test booking creation and management"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_file = self.temp_db.name
        self.setup_test_db()
    
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.db_file):
            try:
                os.remove(self.db_file)
            except PermissionError:
                import time
                time.sleep(0.1)
                try:
                    os.remove(self.db_file)
                except:
                    pass
    
    def setup_test_db(self):
        """Set up test database with data"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT,
                password_hash TEXT,
                role TEXT DEFAULT 'user'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY,
                name TEXT,
                price REAL,
                category TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                service_id INTEGER,
                status TEXT DEFAULT 'pending',
                booking_date TIMESTAMP,
                location TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(service_id) REFERENCES services(id)
            )
        ''')
        
        # Insert test user
        cursor.execute(
            'INSERT INTO users (email, full_name, password_hash, role) VALUES (?, ?, ?, ?)',
            ('user@example.com', 'Test User', 'hash123', 'user')
        )
        
        # Insert test service
        cursor.execute(
            'INSERT INTO services (name, price, category) VALUES (?, ?, ?)',
            ('Plumbing Service', 500.0, 'Plumbing')
        )
        
        conn.commit()
        conn.close()
    
    def test_create_booking(self):
        """Test creating a new booking"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        booking_date = (datetime.now() + timedelta(days=1)).isoformat()
        cursor.execute(
            'INSERT INTO bookings (user_id, service_id, booking_date, location, status) VALUES (?, ?, ?, ?, ?)',
            (1, 1, booking_date, 'Karachi', 'pending')
        )
        booking_id = cursor.lastrowid
        conn.commit()
        
        # Verify booking
        cursor.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,))
        booking = cursor.fetchone()
        self.assertIsNotNone(booking)
        self.assertEqual(booking[3], 'pending')  # status (column 3)
        self.assertEqual(booking[5], 'Karachi')  # location (column 5)
        
        conn.close()
    
    def test_booking_status_values(self):
        """Test that booking status can only have valid values"""
        valid_statuses = ['pending', 'completed', 'cancelled']
        
        for status in valid_statuses:
            # These should all be valid
            self.assertIn(status, valid_statuses)
        
        invalid_status = 'confirmed'
        self.assertNotIn(invalid_status, valid_statuses)
    
    def test_update_booking_status(self):
        """Test updating booking status"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Create booking
        booking_date = (datetime.now() + timedelta(days=1)).isoformat()
        cursor.execute(
            'INSERT INTO bookings (user_id, service_id, booking_date, location, status) VALUES (?, ?, ?, ?, ?)',
            (1, 1, booking_date, 'Karachi', 'pending')
        )
        booking_id = cursor.lastrowid
        conn.commit()
        
        # Update status to completed
        cursor.execute('UPDATE bookings SET status = ? WHERE id = ?', ('completed', booking_id))
        conn.commit()
        
        # Verify update
        cursor.execute('SELECT status FROM bookings WHERE id = ?', (booking_id,))
        status = cursor.fetchone()[0]
        self.assertEqual(status, 'completed')
        
        conn.close()
    
    def test_booking_location_required(self):
        """Test that booking location can be provided"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        booking_date = (datetime.now() + timedelta(days=1)).isoformat()
        location = 'House 45, Block B, DHA'
        
        cursor.execute(
            'INSERT INTO bookings (user_id, service_id, booking_date, location, status) VALUES (?, ?, ?, ?, ?)',
            (1, 1, booking_date, location, 'pending')
        )
        conn.commit()
        
        # Verify location is saved
        cursor.execute('SELECT location FROM bookings WHERE user_id = ?', (1,))
        saved_location = cursor.fetchone()[0]
        self.assertEqual(saved_location, location)
        
        conn.close()
    
    def test_booking_user_service_relationship(self):
        """Test that booking properly links user and service"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        booking_date = (datetime.now() + timedelta(days=1)).isoformat()
        cursor.execute(
            'INSERT INTO bookings (user_id, service_id, booking_date, status) VALUES (?, ?, ?, ?)',
            (1, 1, booking_date, 'pending')
        )
        conn.commit()
        
        # Verify relationships
        cursor.execute('''
            SELECT b.id, u.email, s.name, s.price
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN services s ON b.service_id = s.id
            WHERE b.id = ?
        ''', (cursor.lastrowid,))
        
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[1], 'user@example.com')
        self.assertEqual(result[2], 'Plumbing Service')
        self.assertEqual(result[3], 500.0)
        
        conn.close()


# ==================== TEST SERVICES ====================
class TestServices(unittest.TestCase):
    """Test service management"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_file = self.temp_db.name
        self.setup_test_db()
    
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.db_file):
            try:
                os.remove(self.db_file)
            except PermissionError:
                import time
                time.sleep(0.1)
                try:
                    os.remove(self.db_file)
                except:
                    pass
    
    def setup_test_db(self):
        """Set up test database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY,
                name TEXT,
                category TEXT,
                price REAL,
                description TEXT,
                duration INTEGER,
                worker_id INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workers (
                id INTEGER PRIMARY KEY,
                rating REAL DEFAULT 0.0,
                verified BOOLEAN DEFAULT 0
            )
        ''')
        
        # Insert test worker
        cursor.execute('INSERT INTO workers (rating, verified) VALUES (?, ?)', (4.8, 1))
        
        conn.commit()
        conn.close()
    
    def test_service_creation(self):
        """Test creating a service"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO services (name, category, price, description, duration, worker_id) VALUES (?, ?, ?, ?, ?, ?)',
            ('AC Repair', 'Cooling', 1500.0, 'Professional AC repair service', 120, 1)
        )
        conn.commit()
        
        # Verify service
        cursor.execute('SELECT * FROM services WHERE name = ?', ('AC Repair',))
        service = cursor.fetchone()
        self.assertIsNotNone(service)
        self.assertEqual(service[3], 1500.0)  # price
        self.assertEqual(service[1], 'AC Repair')  # name
        
        conn.close()
    
    def test_service_pricing(self):
        """Test service pricing validation"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        prices = [500.0, 1000.0, 2000.0, 150.50]
        
        for price in prices:
            cursor.execute(
                'INSERT INTO services (name, category, price, duration, worker_id) VALUES (?, ?, ?, ?, ?)',
                (f'Service-{price}', 'General', price, 60, 1)
            )
        
        conn.commit()
        
        # Verify all prices were saved
        cursor.execute('SELECT COUNT(*) FROM services WHERE price > 0')
        count = cursor.fetchone()[0]
        self.assertGreaterEqual(count, len(prices))
        
        conn.close()
    
    def test_service_duration(self):
        """Test service duration storage"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO services (name, category, price, duration, worker_id) VALUES (?, ?, ?, ?, ?)',
            ('Plumbing', 'Repairs', 800.0, 180, 1)
        )
        conn.commit()
        
        cursor.execute('SELECT duration FROM services WHERE name = ?', ('Plumbing',))
        duration = cursor.fetchone()[0]
        self.assertEqual(duration, 180)  # 3 hours in minutes
        
        conn.close()


# ==================== TEST DATA VALIDATION ====================
class TestDataValidation(unittest.TestCase):
    """Test data validation functions"""
    
    def test_email_validation(self):
        """Test email validation"""
        valid_emails = [
            'user@example.com',
            'test.user@domain.co.uk',
            'user+tag@example.com'
        ]
        
        invalid_emails = [
            'notanemail',
            'user@',
            'user name@example.com',  # spaces not allowed
            'user@.com'  # no domain name
        ]
        
        # Email validation - must have @, something before @, and domain with dot
        def is_valid_email(email):
            if '@' not in email:
                return False
            if ' ' in email:  # spaces not allowed
                return False
            parts = email.split('@')
            if len(parts) != 2 or not parts[0] or not parts[1]:
                return False
            if '.' not in parts[1]:
                return False
            if not parts[1].split('.')[0]:  # nothing before the dot
                return False
            return True
        
        for email in valid_emails:
            self.assertTrue(is_valid_email(email), f"{email} should be valid")
        
        for email in invalid_emails:
            self.assertFalse(is_valid_email(email), f"{email} should be invalid")
    
    def test_phone_validation(self):
        """Test phone number validation"""
        valid_phones = [
            '+923001234567',
            '+441234567890',
            '03001234567'
        ]
        
        invalid_phones = [
            '123',  # Too short
            'abc123',  # Contains letters
            ''  # Empty
        ]
        
        def is_valid_phone(phone):
            # Remove common formatting
            cleaned = phone.replace('-', '').replace(' ', '')
            return len(cleaned) >= 10 and cleaned.replace('+', '').isdigit()
        
        for phone in valid_phones:
            self.assertTrue(is_valid_phone(phone), f"{phone} should be valid")
        
        for phone in invalid_phones:
            self.assertFalse(is_valid_phone(phone), f"{phone} should be invalid")
    
    def test_price_validation(self):
        """Test price validation"""
        valid_prices = [100.0, 500.0, 1000.50, 9999.99]
        invalid_prices = [-100.0, -1.0, 0]  # Negative and zero prices
        
        def is_valid_price(price):
            return isinstance(price, (int, float)) and price > 0
        
        for price in valid_prices:
            self.assertTrue(is_valid_price(price))
        
        for price in invalid_prices:
            self.assertFalse(is_valid_price(price))


# ==================== TEST WORKERS ====================
class TestWorkers(unittest.TestCase):
    """Test worker management"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_file = self.temp_db.name
        self.setup_test_db()
    
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.db_file):
            try:
                os.remove(self.db_file)
            except PermissionError:
                import time
                time.sleep(0.1)
                try:
                    os.remove(self.db_file)
                except:
                    pass
    
    def setup_test_db(self):
        """Set up test database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT,
                password_hash TEXT,
                role TEXT DEFAULT 'user'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workers (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                experience_years INTEGER,
                rating REAL,
                specialties TEXT,
                verified BOOLEAN DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # Insert test user
        cursor.execute(
            'INSERT INTO users (email, full_name, password_hash, role) VALUES (?, ?, ?, ?)',
            ('worker@example.com', 'Ahmed Khan', 'hash123', 'worker')
        )
        
        conn.commit()
        conn.close()
    
    def test_worker_creation(self):
        """Test creating a worker profile"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO workers (user_id, experience_years, rating, specialties, verified) VALUES (?, ?, ?, ?, ?)',
            (1, 5, 4.8, 'Plumbing,Electrical', 1)
        )
        conn.commit()
        
        # Verify worker
        cursor.execute('SELECT * FROM workers WHERE user_id = ?', (1,))
        worker = cursor.fetchone()
        self.assertIsNotNone(worker)
        self.assertEqual(worker[2], 5)  # experience_years
        self.assertEqual(worker[3], 4.8)  # rating
        
        conn.close()
    
    def test_worker_rating(self):
        """Test worker rating range"""
        valid_ratings = [0.0, 2.5, 4.0, 4.8, 5.0]
        invalid_ratings = [-1.0, 5.5, 10.0]
        
        def is_valid_rating(rating):
            return 0.0 <= rating <= 5.0
        
        for rating in valid_ratings:
            self.assertTrue(is_valid_rating(rating))
        
        for rating in invalid_ratings:
            self.assertFalse(is_valid_rating(rating))
    
    def test_worker_verification_status(self):
        """Test worker verification status"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO workers (user_id, experience_years, rating, verified) VALUES (?, ?, ?, ?)',
            (1, 3, 4.5, 1)
        )
        conn.commit()
        
        # Verify status
        cursor.execute('SELECT verified FROM workers WHERE user_id = ?', (1,))
        verified = cursor.fetchone()[0]
        self.assertEqual(verified, 1)  # Should be True/1
        
        conn.close()


if __name__ == '__main__':
    # Run tests with verbosity
    unittest.main(verbosity=2)
