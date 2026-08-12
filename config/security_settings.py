"""
Enhanced Security Configuration for ASOUD Platform
This module contains comprehensive security settings and utilities
"""

import os
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

class SecurityConfig:
    """Centralized security configuration management"""
    
    # CSRF Configuration
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SAMESITE = "Strict"
    CSRF_COOKIE_DOMAIN = None
    CSRF_COOKIE_PATH = '/'
    CSRF_COOKIE_AGE = 31449600  # 1 year
    CSRF_USE_SESSIONS = True
    CSRF_FAILURE_VIEW = 'config.views.csrf_failure_view'
    
    # Session Configuration
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Strict"
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True
    SESSION_COOKIE_AGE = 3600  # 1 hour
    
    # Security Headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_REDIRECT_EXEMPT = []
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # Password Validation
    AUTH_PASSWORD_VALIDATORS = [
        {
            'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
            'OPTIONS': {
                'min_length': 12,
            }
        },
        {
            'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        },
        {
            'NAME': 'config.validators.CustomPasswordValidator',
        },
    ]
    
    # Rate Limiting
    RATELIMIT_ENABLE = True
    RATELIMIT_USE_CACHE = 'default'
    RATELIMIT_VIEW = 'config.views.rate_limit_view'
    
    # API Security
    API_RATE_LIMIT = {
        'DEFAULT': '1000/hour',
        'AUTH': '10/minute',
        'PAYMENT': '5/minute',
        'UPLOAD': '20/hour',
    }
    
    # File Upload Security
    ALLOWED_FILE_TYPES = [
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        'application/pdf', 'text/plain'
    ]
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    UPLOAD_VIRUS_SCAN = True
    
    # Database Security
    DATABASE_CONNECTION_OPTIONS = {
        'sslmode': 'require',
        'sslcert': None,
        'sslkey': None,
        'sslrootcert': None,
    }
    
    # Logging Security
    SECURITY_LOGGING = {
        'LOG_FAILED_LOGINS': True,
        'LOG_SUCCESSFUL_LOGINS': True,
        'LOG_PASSWORD_CHANGES': True,
        'LOG_PERMISSION_CHANGES': True,
        'LOG_DATA_ACCESS': True,
    }
    
    @classmethod
    def get_csrf_trusted_origins(cls):
        """Get CSRF trusted origins from environment"""
        origins = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
        if origins:
            return [origin.strip() for origin in origins.split(",") if origin.strip()]
        return []
    
    @classmethod
    def get_allowed_hosts(cls):
        """Get allowed hosts from environment"""
        hosts = os.environ.get("ALLOWED_HOSTS", "")
        if hosts:
            return [host.strip() for host in hosts.split(",") if host.strip()]
        return ['localhost', '127.0.0.1']
    
    @classmethod
    def validate_configuration(cls):
        """Validate security configuration"""
        required_settings = [
            'SECRET_KEY',
            'DATABASE_URL',
            'REDIS_URL',
        ]
        
        for setting in required_settings:
            if not hasattr(settings, setting) or not getattr(settings, setting):
                raise ImproperlyConfigured(f"Required setting {setting} is not configured")
        
        return True

# Security Middleware
class SecurityHeadersMiddleware:
    """Add security headers to all responses"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # HSTS header
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response

# Input Validation Utilities
class InputValidator:
    """Comprehensive input validation utilities"""
    
    @staticmethod
    def sanitize_string(value, max_length=None):
        """Sanitize string input"""
        if not isinstance(value, str):
            return ""
        
        # Remove null bytes and control characters
        value = value.replace('\x00', '').replace('\r', '').replace('\n', '')
        
        # Limit length
        if max_length and len(value) > max_length:
            value = value[:max_length]
        
        return value.strip()
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_phone(phone):
        """Validate phone number format"""
        import re
        # Iranian phone number pattern
        pattern = r'^09\d{9}$'
        return re.match(pattern, phone) is not None
    
    @staticmethod
    def validate_file_type(file, allowed_types):
        """Validate uploaded file type"""
        return file.content_type in allowed_types
    
    @staticmethod
    def validate_file_size(file, max_size):
        """Validate uploaded file size"""
        return file.size <= max_size

# SQL Injection Prevention
class SQLInjectionPrevention:
    """SQL injection prevention utilities"""
    
    @staticmethod
    def escape_like_query(value):
        """Escape LIKE query parameters"""
        return value.replace('%', '\\%').replace('_', '\\_')
    
    @staticmethod
    def validate_sql_identifier(identifier):
        """Validate SQL identifier"""
        import re
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        return re.match(pattern, identifier) is not None

# XSS Prevention
class XSSPrevention:
    """XSS prevention utilities"""
    
    @staticmethod
    def escape_html(value):
        """Escape HTML characters"""
        if not isinstance(value, str):
            return str(value)
        
        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&#x27;",
            ">": "&gt;",
            "<": "&lt;",
        }
        
        return "".join(html_escape_table.get(c, c) for c in value)
    
    @staticmethod
    def escape_js(value):
        """Escape JavaScript characters"""
        if not isinstance(value, str):
            return str(value)
        
        js_escape_table = {
            "\\": "\\\\",
            "'": "\\'",
            '"': '\\"',
            "\n": "\\n",
            "\r": "\\r",
            "\t": "\\t",
        }
        
        return "".join(js_escape_table.get(c, c) for c in value)



