"""
Enhanced Logging Configuration for ASOUD Platform
"""

import os
import logging
import logging.handlers
from django.conf import settings

# Log levels
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}

# Get log level from environment
LOG_LEVEL = LOG_LEVELS.get(os.environ.get('LOG_LEVEL', 'INFO'), logging.INFO)

# Log directory
LOG_DIR = os.path.join(settings.BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Log formatters
LOGGING_FORMATTERS = {
    'verbose': {
        'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
        'style': '{',
    },
    'simple': {
        'format': '{levelname} {message}',
        'style': '{',
    },
    'detailed': {
        'format': '{levelname} {asctime} {name} {module} {funcName} {lineno:d} {message}',
        'style': '{',
    },
    'security': {
        'format': 'SECURITY {levelname} {asctime} {name} {module} {funcName} {lineno:d} {message}',
        'style': '{',
    },
    'performance': {
        'format': 'PERFORMANCE {levelname} {asctime} {name} {module} {funcName} {lineno:d} {message}',
        'style': '{',
    },
    'business': {
        'format': 'BUSINESS {levelname} {asctime} {name} {module} {funcName} {lineno:d} {message}',
        'style': '{',
    },
}

# Log handlers
LOGGING_HANDLERS = {
    'console': {
        'class': 'logging.StreamHandler',
        'level': LOG_LEVEL,
        'formatter': 'simple',
        'stream': 'ext://sys.stdout',
    },
    'file': {
        'class': 'logging.handlers.RotatingFileHandler',
        'level': LOG_LEVEL,
        'formatter': 'verbose',
        'filename': os.path.join(LOG_DIR, 'django.log'),
        'maxBytes': 1024 * 1024 * 10,  # 10MB
        'backupCount': 5,
    },
    'security_file': {
        'class': 'logging.handlers.RotatingFileHandler',
        'level': logging.WARNING,
        'formatter': 'security',
        'filename': os.path.join(LOG_DIR, 'security.log'),
        'maxBytes': 1024 * 1024 * 10,  # 10MB
        'backupCount': 10,
    },
    'performance_file': {
        'class': 'logging.handlers.RotatingFileHandler',
        'level': logging.INFO,
        'formatter': 'performance',
        'filename': os.path.join(LOG_DIR, 'performance.log'),
        'maxBytes': 1024 * 1024 * 10,  # 10MB
        'backupCount': 5,
    },
    'business_file': {
        'class': 'logging.handlers.RotatingFileHandler',
        'level': logging.INFO,
        'formatter': 'business',
        'filename': os.path.join(LOG_DIR, 'business.log'),
        'maxBytes': 1024 * 1024 * 10,  # 10MB
        'backupCount': 5,
    },
    'error_file': {
        'class': 'logging.handlers.RotatingFileHandler',
        'level': logging.ERROR,
        'formatter': 'detailed',
        'filename': os.path.join(LOG_DIR, 'error.log'),
        'maxBytes': 1024 * 1024 * 10,  # 10MB
        'backupCount': 10,
    },
    'admin_email': {
        'class': 'django.utils.log.AdminEmailHandler',
        'level': logging.ERROR,
        'formatter': 'detailed',
        'include_html': True,
    },
}

# Loggers
LOGGING_LOGGERS = {
    'django': {
        'handlers': ['console', 'file'],
        'level': LOG_LEVEL,
        'propagate': False,
    },
    'django.request': {
        'handlers': ['console', 'file', 'error_file'],
        'level': logging.WARNING,
        'propagate': False,
    },
    'django.security': {
        'handlers': ['console', 'security_file', 'admin_email'],
        'level': logging.WARNING,
        'propagate': False,
    },
    'django.db.backends': {
        'handlers': ['console', 'file'],
        'level': logging.WARNING,
        'propagate': False,
    },
    'apps.core': {
        'handlers': ['console', 'file'],
        'level': LOG_LEVEL,
        'propagate': False,
    },
    'apps.core.security': {
        'handlers': ['console', 'security_file', 'admin_email'],
        'level': logging.WARNING,
        'propagate': False,
    },
    'apps.core.performance': {
        'handlers': ['console', 'performance_file'],
        'level': logging.INFO,
        'propagate': False,
    },
    'apps.core.business': {
        'handlers': ['console', 'business_file'],
        'level': logging.INFO,
        'propagate': False,
    },
    'apps.users': {
        'handlers': ['console', 'file'],
        'level': LOG_LEVEL,
        'propagate': False,
    },
    'apps.payment': {
        'handlers': ['console', 'business_file', 'security_file'],
        'level': LOG_LEVEL,
        'propagate': False,
    },
    'apps.cart': {
        'handlers': ['console', 'business_file'],
        'level': LOG_LEVEL,
        'propagate': False,
    },
    'apps.market': {
        'handlers': ['console', 'business_file'],
        'level': LOG_LEVEL,
        'propagate': False,
    },
    'apps.product': {
        'handlers': ['console', 'business_file'],
        'level': LOG_LEVEL,
        'propagate': False,
    },
    'config': {
        'handlers': ['console', 'file'],
        'level': LOG_LEVEL,
        'propagate': False,
    },
    'config.security': {
        'handlers': ['console', 'security_file', 'admin_email'],
        'level': logging.WARNING,
        'propagate': False,
    },
}

# Complete logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': LOGGING_FORMATTERS,
    'handlers': LOGGING_HANDLERS,
    'loggers': LOGGING_LOGGERS,
    'root': {
        'handlers': ['console', 'file'],
        'level': LOG_LEVEL,
    },
}

# Security logging configuration
SECURITY_LOGGING = {
    'LOG_FAILED_LOGINS': True,
    'LOG_SUCCESSFUL_LOGINS': True,
    'LOG_PASSWORD_CHANGES': True,
    'LOG_PERMISSION_CHANGES': True,
    'LOG_DATA_ACCESS': True,
    'LOG_SUSPICIOUS_ACTIVITY': True,
    'LOG_RATE_LIMIT_VIOLATIONS': True,
    'LOG_CSRF_VIOLATIONS': True,
    'LOG_SQL_INJECTION_ATTEMPTS': True,
    'LOG_XSS_ATTEMPTS': True,
}

# Performance logging configuration
PERFORMANCE_LOGGING = {
    'LOG_SLOW_QUERIES': True,
    'SLOW_QUERY_THRESHOLD': 0.1,  # seconds
    'LOG_API_RESPONSE_TIMES': True,
    'API_RESPONSE_TIME_THRESHOLD': 0.5,  # seconds
    'LOG_MEMORY_USAGE': True,
    'MEMORY_USAGE_THRESHOLD': 100,  # MB
    'LOG_CACHE_HIT_RATES': True,
    'CACHE_HIT_RATE_THRESHOLD': 0.8,  # 80%
}

# Business logging configuration
BUSINESS_LOGGING = {
    'LOG_ORDER_CREATIONS': True,
    'LOG_ORDER_UPDATES': True,
    'LOG_ORDER_CANCELLATIONS': True,
    'LOG_PAYMENT_ATTEMPTS': True,
    'LOG_PAYMENT_SUCCESSES': True,
    'LOG_PAYMENT_FAILURES': True,
    'LOG_INVENTORY_CHANGES': True,
    'LOG_USER_REGISTRATIONS': True,
    'LOG_USER_LOGINS': True,
    'LOG_USER_LOGOUTS': True,
    'LOG_PRODUCT_CREATIONS': True,
    'LOG_PRODUCT_UPDATES': True,
    'LOG_MARKET_CREATIONS': True,
    'LOG_MARKET_UPDATES': True,
}

# Custom loggers
class SecurityLogger:
    """Security-specific logger"""
    
    def __init__(self):
        self.logger = logging.getLogger('config.security')
    
    def log_failed_login(self, user, ip_address, user_agent):
        """Log failed login attempt"""
        self.logger.warning(
            f"Failed login attempt: user={user}, ip={ip_address}, user_agent={user_agent}"
        )
    
    def log_successful_login(self, user, ip_address, user_agent):
        """Log successful login"""
        self.logger.info(
            f"Successful login: user={user}, ip={ip_address}, user_agent={user_agent}"
        )
    
    def log_password_change(self, user, ip_address):
        """Log password change"""
        self.logger.info(
            f"Password changed: user={user}, ip={ip_address}"
        )
    
    def log_permission_change(self, user, target_user, permission, ip_address):
        """Log permission change"""
        self.logger.info(
            f"Permission changed: user={user}, target_user={target_user}, "
            f"permission={permission}, ip={ip_address}"
        )
    
    def log_suspicious_activity(self, user, activity, details, ip_address):
        """Log suspicious activity"""
        self.logger.warning(
            f"Suspicious activity: user={user}, activity={activity}, "
            f"details={details}, ip={ip_address}"
        )
    
    def log_rate_limit_violation(self, ip_address, endpoint, user=None):
        """Log rate limit violation"""
        self.logger.warning(
            f"Rate limit violation: ip={ip_address}, endpoint={endpoint}, user={user}"
        )
    
    def log_csrf_violation(self, ip_address, endpoint, user=None):
        """Log CSRF violation"""
        self.logger.warning(
            f"CSRF violation: ip={ip_address}, endpoint={endpoint}, user={user}"
        )
    
    def log_sql_injection_attempt(self, ip_address, query, user=None):
        """Log SQL injection attempt"""
        self.logger.warning(
            f"SQL injection attempt: ip={ip_address}, query={query}, user={user}"
        )
    
    def log_xss_attempt(self, ip_address, payload, user=None):
        """Log XSS attempt"""
        self.logger.warning(
            f"XSS attempt: ip={ip_address}, payload={payload}, user={user}"
        )

class PerformanceLogger:
    """Performance-specific logger"""
    
    def __init__(self):
        self.logger = logging.getLogger('config.performance')
    
    def log_slow_query(self, query, execution_time, user=None):
        """Log slow query"""
        self.logger.warning(
            f"Slow query: execution_time={execution_time}s, query={query[:100]}..., user={user}"
        )
    
    def log_api_response_time(self, endpoint, response_time, user=None):
        """Log API response time"""
        if response_time > PERFORMANCE_LOGGING['API_RESPONSE_TIME_THRESHOLD']:
            self.logger.warning(
                f"Slow API response: endpoint={endpoint}, response_time={response_time}s, user={user}"
            )
        else:
            self.logger.info(
                f"API response: endpoint={endpoint}, response_time={response_time}s, user={user}"
            )
    
    def log_memory_usage(self, memory_usage, user=None):
        """Log memory usage"""
        if memory_usage > PERFORMANCE_LOGGING['MEMORY_USAGE_THRESHOLD']:
            self.logger.warning(
                f"High memory usage: {memory_usage}MB, user={user}"
            )
        else:
            self.logger.info(
                f"Memory usage: {memory_usage}MB, user={user}"
            )
    
    def log_cache_hit_rate(self, cache_name, hit_rate, user=None):
        """Log cache hit rate"""
        if hit_rate < PERFORMANCE_LOGGING['CACHE_HIT_RATE_THRESHOLD']:
            self.logger.warning(
                f"Low cache hit rate: cache={cache_name}, hit_rate={hit_rate}, user={user}"
            )
        else:
            self.logger.info(
                f"Cache hit rate: cache={cache_name}, hit_rate={hit_rate}, user={user}"
            )

class BusinessLogger:
    """Business-specific logger"""
    
    def __init__(self):
        self.logger = logging.getLogger('config.business')
    
    def log_order_creation(self, order_id, user, total_amount):
        """Log order creation"""
        self.logger.info(
            f"Order created: order_id={order_id}, user={user}, total_amount={total_amount}"
        )
    
    def log_order_update(self, order_id, user, changes):
        """Log order update"""
        self.logger.info(
            f"Order updated: order_id={order_id}, user={user}, changes={changes}"
        )
    
    def log_order_cancellation(self, order_id, user, reason):
        """Log order cancellation"""
        self.logger.info(
            f"Order cancelled: order_id={order_id}, user={user}, reason={reason}"
        )
    
    def log_payment_attempt(self, payment_id, user, amount, method):
        """Log payment attempt"""
        self.logger.info(
            f"Payment attempt: payment_id={payment_id}, user={user}, amount={amount}, method={method}"
        )
    
    def log_payment_success(self, payment_id, user, amount, method):
        """Log payment success"""
        self.logger.info(
            f"Payment success: payment_id={payment_id}, user={user}, amount={amount}, method={method}"
        )
    
    def log_payment_failure(self, payment_id, user, amount, method, error):
        """Log payment failure"""
        self.logger.warning(
            f"Payment failure: payment_id={payment_id}, user={user}, amount={amount}, method={method}, error={error}"
        )
    
    def log_inventory_change(self, product_id, change_type, quantity, user):
        """Log inventory change"""
        self.logger.info(
            f"Inventory change: product_id={product_id}, change_type={change_type}, quantity={quantity}, user={user}"
        )
    
    def log_user_registration(self, user_id, email, ip_address):
        """Log user registration"""
        self.logger.info(
            f"User registered: user_id={user_id}, email={email}, ip={ip_address}"
        )
    
    def log_user_login(self, user_id, ip_address):
        """Log user login"""
        self.logger.info(
            f"User login: user_id={user_id}, ip={ip_address}"
        )
    
    def log_user_logout(self, user_id, ip_address):
        """Log user logout"""
        self.logger.info(
            f"User logout: user_id={user_id}, ip={ip_address}"
        )

# Global logger instances
security_logger = SecurityLogger()
performance_logger = PerformanceLogger()
business_logger = BusinessLogger()



