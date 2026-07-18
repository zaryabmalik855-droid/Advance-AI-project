#Complete Setup Guide for Trusted Home Platform

## Quick Start - Using Django (Recommended for Python 3.14)

Since you're on Python 3.14, FastAPI has compatibility issues. The Django backend is better supported.

### 1. Install Django Dependencies
```bash
cd c:\amna uni\SEMESTER 6\Advance AI\trusted_home_services
pip install Django==4.2 djangorestframework==3.14 django-cors-headers==3.14
```

### 2. Configure Django Settings
Create `settings.py` in `trusted_home_services/` directory:
```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'trusted-home-secret-key-2024'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'users',
    'workers',
    'bookings',
    'payments',
    'reviews',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.security.SecurityMiddleware',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}

CORS_ALLOWED_ORIGINS = ["*"]

ROOT_URLCONF = 'trusted_home_services.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

### 3. Create URLConfiguration
Create `trusted_home_services/urls.py`:
```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/workers/', include('workers.urls')),
    path('api/bookings/', include('bookings.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/reviews/', include('reviews.urls')),
]
```

### 4. Run Django Server
```bash
cd c:\amna uni\SEMESTER 6\Advance AI\trusted_home_services
python manage.py migrate
python manage.py createsuperuser  # Create admin user
python manage.py runserver 0.0.0.0:8000
```

### 5. API Endpoints
- Admin: http://localhost:8000/admin/
- API: http://localhost:8000/api/

---

## Alternative: Simple Python Web Server (No Dependencies)

If you want a quick working version without FastAPI/Django issues, run:

```bash
python c:\amna uni\SEMESTER 6\Advance AI\SIMPLE_SERVER.py
```

Then visit: http://localhost:5000

---

## Test Credentials
- Admin: admin / admin123
- User: user1 / user123
- Worker: worker1 / worker123

---

## Troubleshooting

**"pydantic.errors.ConfigError" Error:**
- This is a Python 3.14 + FastAPI compatibility issue
- Solution: Use the Django backend instead (recommended)

**Database not found:**
```bash
python manage.py migrate
```

**Port already in use:**
Change port: `python manage.py runserver 0.0.0.0:9000`
