# Trusted Home Platform - Complete Application

## ✅ FULLY WORKING APPLICATION

Your complete Trusted Home Platform application is ready to run!

### 🚀 Quick Start (Recommended)

**Run the Simple HTTP Server (No Dependencies Installation):**

```bash
cd c:\amna uni\SEMESTER 6\Advance AI
python SIMPLE_SERVER.py
```

Then open: **http://localhost:5000/**

**That's it!** The server will start and display:
- API documentation
- Test credentials
- Example requests

---

## 📝 What You Get

### Complete Application Features:

✅ **User Management**
- User registration & login
- Password hashing & security
- Token-based authentication

✅ **Service Management**
- Browse available services
- List all services with pricing
- Service categories

✅ **Booking System**
- Create bookings
- View user bookings
- Booking status tracking

✅ **Database**
- SQLite database (auto-created)
- User table
- Services table
- Bookings table

✅ **API Endpoints**

#### Authentication
```
POST   /api/auth/register      Register new user
POST   /api/auth/login         Login (get token)
```

#### Services
```
GET    /api/services           List all services
```

#### Bookings
```
GET    /api/bookings           Get your bookings (requires token)
POST   /api/bookings           Create booking (requires token)
```

---

## 🔑 Test Credentials

After starting the server:

**Regular User:**
- Email: `user@example.com`
- Password: `User@12345`

**Admin User:**
- Email: `admin@example.com`
- Password: `Admin@12345`

---

## 📚 API Testing Examples

### 1. Register a New User

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "NewUser@12345",
    "full_name": "New User"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "User@12345"
  }'
```

**Response:**
```json
{
  "access_token": "token_string_here",
  "token_type": "bearer",
  "user_id": 1
}
```

### 3. Get All Services

```bash
curl http://localhost:5000/api/services
```

### 4. Create a Booking

```bash
curl -X POST http://localhost:5000/api/bookings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "service_id": 1,
    "booking_date": "2024-03-25T10:00:00"
  }'
```

### 5. View Your Bookings

```bash
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  http://localhost:5000/api/bookings
```

---

## 🛠️ Available Files

### Main Application Files

1. **`SIMPLE_SERVER.py`** ← **START HERE** 
   - Complete working web server
   - No framework dependencies
   - Works with Python 3.14
   - HTTP-based API

2. **`RUN_SERVER.py`**
   - FastAPI version (if you want to use it later)
   - Requires dependency fixes for Python 3.14

3. **`trusted_home_platform/`**
   - FastAPI/SQLAlchemy application
   - Complete models, schemas, routes
   - Requires dependency setup

4. **`trusted_home_services/`**
   - Django application
   - REST endpoints
   -  Admin interface

### Documentation

- **`SETUP_GUIDE.md`** - Full setup instructions
- **`COMPLETE_SETUP.md`** - FastAPI setup guide  
- **`README.md`** - This file

---

## 🎯 Next Steps

### Option 1: Use Simple Server (Recommended)
✅ Run `SIMPLE_SERVER.py` - already fully working!

### Option 2: Setup FastAPI
```bash
# Install dependencies
pip install fastapi==0.68.0 pydantic==1.8.2 uvicorn sqlalchemy

# Run
cd trusted_home_platform
python main.py
```

### Option 3: Setup Django
```bash
# Install dependencies  
pip install Django==4.2 djangorestframework==3.14

# Setup and run
cd trusted_home_services
python manage.py migrate
python manage.py runserver
```

---

## 📊 Database

The application uses SQLite with auto-created tables:

- **users**: Stores user accounts
- **services**: Lists available services
- **bookings**: Tracks all bookings

Database file: `trusted_home.db` (created automatically)

---

## 🔐 Security Features

✅ Password hashing (SHA-256)
✅ Token-based authentication (HMAC-SHA256)
✅ CORS support
✅ Input validation

---

## ⚙️ System Requirements

- Python 3.8 or higher (tested on 3.14)
- 10MB free disk space for database
- No external framework dependencies for Simple Server

---

## 🐛 Troubleshooting

### "Address already in use" Error
- Change port in `SIMPLE_SERVER.py` line that says `port = 5000`
- Or kill the existing process using that port

### "No such table" Error
- Delete `trusted_home.db` and restart
- Server will auto-create database with test data

### Can't connect to server
- Ensure server is running: `python SIMPLE_SERVER.py`
- Check firewall settings
- Try: `http://127.0.0.1:5000` instead of localhost

---

## 📞 Support

All endpoints return JSON responses with status codes:
- `200` - Success
- `201` - Created
- `400` - Bad request
- `401` - Unauthorized  
- `404` - Not found
- `500` - Server error

---

## ✨ Summary

You now have:

1. ✅ **WORKING Server** - Just run `SIMPLE_SERVER.py`
2. ✅ **Full API** - Users, Services, Bookings
3. ✅ **Database** - Auto-created SQLite
4. ✅ **Test Data** - Pre-loaded users & services
5. ✅ **Documentation** - API examples & guides

**Start coding!**

```bash
python SIMPLE_SERVER.py
```

Then visit: **http://localhost:5000/**
