"""
Enhanced Serializers for ASOUD Platform with Security Features
"""

import re
import html
from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from config.validators import (
    MobileNumberValidator, NationalCodeValidator, BusinessIdValidator,
    PriceValidator, QuantityValidator, DiscountPercentageValidator
)

class SecureCharField(serializers.CharField):
    """
    Secure CharField with input sanitization
    """
    
    def __init__(self, **kwargs):
        self.max_length = kwargs.get('max_length', 255)
        self.allow_html = kwargs.pop('allow_html', False)
        self.sanitize = kwargs.pop('sanitize', True)
        super().__init__(**kwargs)
    
    def to_internal_value(self, data):
        """Sanitize input data"""
        if not isinstance(data, str):
            data = str(data)
        
        # Remove null bytes and control characters
        data = data.replace('\x00', '').replace('\r', '').replace('\n', '')
        
        # Limit length
        if len(data) > self.max_length:
            data = data[:self.max_length]
        
        # Sanitize HTML if not allowed
        if not self.allow_html and self.sanitize:
            data = html.escape(data)
        
        return super().to_internal_value(data)

class SecureTextField(serializers.CharField):
    """
    Secure TextField with input sanitization
    """
    
    def __init__(self, **kwargs):
        self.max_length = kwargs.get('max_length', 10000)
        self.allow_html = kwargs.pop('allow_html', False)
        self.sanitize = kwargs.pop('sanitize', True)
        super().__init__(**kwargs)
    
    def to_internal_value(self, data):
        """Sanitize input data"""
        if not isinstance(data, str):
            data = str(data)
        
        # Remove null bytes and control characters
        data = data.replace('\x00', '').replace('\r', '').replace('\n', '')
        
        # Limit length
        if len(data) > self.max_length:
            data = data[:self.max_length]
        
        # Sanitize HTML if not allowed
        if not self.allow_html and self.sanitize:
            data = html.escape(data)
        
        return super().to_internal_value(data)

class SecureEmailField(serializers.EmailField):
    """
    Secure EmailField with validation
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def to_internal_value(self, data):
        """Validate and sanitize email"""
        if not isinstance(data, str):
            data = str(data)
        
        # Basic sanitization
        data = data.strip().lower()
        
        # Validate email format
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', data):
            raise ValidationError('Enter a valid email address.')
        
        return super().to_internal_value(data)

class SecurePhoneField(serializers.CharField):
    """
    Secure PhoneField with Iranian mobile validation
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validators.append(MobileNumberValidator())
    
    def to_internal_value(self, data):
        """Validate and sanitize phone number"""
        if not isinstance(data, str):
            data = str(data)
        
        # Remove all non-digit characters
        data = re.sub(r'\D', '', data)
        
        # Add country code if missing
        if data.startswith('9') and len(data) == 10:
            data = '0' + data
        
        return super().to_internal_value(data)

class SecurePasswordField(serializers.CharField):
    """
    Secure PasswordField with strength validation
    """
    
    def __init__(self, **kwargs):
        self.min_length = kwargs.get('min_length', 12)
        super().__init__(**kwargs)
    
    def to_internal_value(self, data):
        """Validate password strength"""
        if not isinstance(data, str):
            data = str(data)
        
        # Check minimum length
        if len(data) < self.min_length:
            raise ValidationError(f'Password must be at least {self.min_length} characters long.')
        
        # Check for uppercase letters
        if not re.search(r'[A-Z]', data):
            raise ValidationError('Password must contain at least one uppercase letter.')
        
        # Check for lowercase letters
        if not re.search(r'[a-z]', data):
            raise ValidationError('Password must contain at least one lowercase letter.')
        
        # Check for numbers
        if not re.search(r'\d', data):
            raise ValidationError('Password must contain at least one number.')
        
        # Check for special characters
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', data):
            raise ValidationError('Password must contain at least one special character.')
        
        # Check for common patterns
        common_patterns = [
            '123456', 'abcdef', 'qwerty', 'password', 'admin',
            '123456789', 'abcdefgh', 'qwertyui', 'password123'
        ]
        
        data_lower = data.lower()
        for pattern in common_patterns:
            if pattern in data_lower:
                raise ValidationError('Password cannot contain common patterns.')
        
        return super().to_internal_value(data)

class SecurePriceField(serializers.DecimalField):
    """
    Secure PriceField with validation
    """
    
    def __init__(self, **kwargs):
        self.max_digits = kwargs.get('max_digits', 10)
        self.decimal_places = kwargs.get('decimal_places', 2)
        super().__init__(**kwargs)
        self.validators.append(PriceValidator())
    
    def to_internal_value(self, data):
        """Validate price value"""
        try:
            value = super().to_internal_value(data)
            if value <= 0:
                raise ValidationError('Price must be greater than zero.')
            if value > 999999999:  # 999 million
                raise ValidationError('Price cannot exceed 999,999,999.')
            return value
        except (ValueError, TypeError):
            raise ValidationError('Enter a valid price.')

class SecureQuantityField(serializers.IntegerField):
    """
    Secure QuantityField with validation
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validators.append(QuantityValidator())
    
    def to_internal_value(self, data):
        """Validate quantity value"""
        try:
            value = super().to_internal_value(data)
            if value < 0:
                raise ValidationError('Quantity cannot be negative.')
            if value > 99999:  # 99,999
                raise ValidationError('Quantity cannot exceed 99,999.')
            return value
        except (ValueError, TypeError):
            raise ValidationError('Enter a valid quantity.')

class SecureDiscountField(serializers.DecimalField):
    """
    Secure DiscountField with validation
    """
    
    def __init__(self, **kwargs):
        self.max_digits = kwargs.get('max_digits', 5)
        self.decimal_places = kwargs.get('decimal_places', 2)
        super().__init__(**kwargs)
        self.validators.append(DiscountPercentageValidator())
    
    def to_internal_value(self, data):
        """Validate discount percentage"""
        try:
            value = super().to_internal_value(data)
            if value < 0 or value > 100:
                raise ValidationError('Discount percentage must be between 0 and 100.')
            return value
        except (ValueError, TypeError):
            raise ValidationError('Enter a valid discount percentage.')

class SecureBusinessIdField(serializers.CharField):
    """
    Secure BusinessIdField with validation
    """
    
    def __init__(self, **kwargs):
        self.max_length = kwargs.get('max_length', 50)
        super().__init__(**kwargs)
        self.validators.append(BusinessIdValidator())
    
    def to_internal_value(self, data):
        """Validate business ID"""
        if not isinstance(data, str):
            data = str(data)
        
        # Sanitize input
        data = data.strip().lower()
        
        # Validate format
        if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', data):
            raise ValidationError(
                'Business ID must be 3-50 characters long and contain only letters, numbers, hyphens, and underscores.'
            )
        
        return super().to_internal_value(data)

class SecureFileField(serializers.FileField):
    """
    Secure FileField with validation
    """
    
    def __init__(self, **kwargs):
        self.allowed_types = kwargs.pop('allowed_types', [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'text/plain'
        ])
        self.max_size = kwargs.pop('max_size', 10 * 1024 * 1024)  # 10MB
        super().__init__(**kwargs)
    
    def to_internal_value(self, data):
        """Validate file upload"""
        if not data:
            return super().to_internal_value(data)
        
        # Check file type
        if data.content_type not in self.allowed_types:
            raise ValidationError(
                f'File type not allowed. Allowed types: {", ".join(self.allowed_types)}'
            )
        
        # Check file size
        if data.size > self.max_size:
            raise ValidationError(
                f'File size cannot exceed {self.max_size / (1024 * 1024):.1f}MB.'
            )
        
        return super().to_internal_value(data)

class SecureJSONField(serializers.JSONField):
    """
    Secure JSONField with validation
    """
    
    def __init__(self, **kwargs):
        self.max_depth = kwargs.pop('max_depth', 10)
        self.max_keys = kwargs.pop('max_keys', 100)
        super().__init__(**kwargs)
    
    def to_internal_value(self, data):
        """Validate JSON data"""
        try:
            value = super().to_internal_value(data)
            
            # Check depth
            if self.get_json_depth(value) > self.max_depth:
                raise ValidationError(f'JSON depth cannot exceed {self.max_depth} levels.')
            
            # Check number of keys
            if self.get_json_keys(value) > self.max_keys:
                raise ValidationError(f'JSON cannot have more than {self.max_keys} keys.')
            
            return value
        except (ValueError, TypeError):
            raise ValidationError('Enter valid JSON data.')
    
    def get_json_depth(self, obj, depth=0):
        """Calculate JSON depth"""
        if isinstance(obj, dict):
            return 1 + (max(map(self.get_json_depth, obj.values())) if obj else 0)
        elif isinstance(obj, list):
            return 1 + (max(map(self.get_json_depth, obj)) if obj else 0)
        else:
            return depth
    
    def get_json_keys(self, obj):
        """Count JSON keys"""
        if isinstance(obj, dict):
            return len(obj) + sum(self.get_json_keys(v) for v in obj.values())
        elif isinstance(obj, list):
            return sum(self.get_json_keys(v) for v in obj)
        else:
            return 0

class SecureURLField(serializers.URLField):
    """
    Secure URLField with validation
    """
    
    def __init__(self, **kwargs):
        self.allowed_schemes = kwargs.pop('allowed_schemes', ['http', 'https'])
        super().__init__(**kwargs)
    
    def to_internal_value(self, data):
        """Validate URL"""
        if not isinstance(data, str):
            data = str(data)
        
        # Basic sanitization
        data = data.strip()
        
        # Check scheme
        if '://' in data:
            scheme = data.split('://')[0].lower()
            if scheme not in self.allowed_schemes:
                raise ValidationError(f'URL scheme must be one of: {", ".join(self.allowed_schemes)}')
        
        return super().to_internal_value(data)

class SecureIPAddressField(serializers.IPAddressField):
    """
    Secure IPAddressField with validation
    """
    
    def __init__(self, **kwargs):
        self.allowed_versions = kwargs.pop('allowed_versions', [4, 6])
        super().__init__(**kwargs)
    
    def to_internal_value(self, data):
        """Validate IP address"""
        if not isinstance(data, str):
            data = str(data)
        
        # Basic sanitization
        data = data.strip()
        
        # Validate IP version
        try:
            import ipaddress
            ip = ipaddress.ip_address(data)
            if ip.version not in self.allowed_versions:
                raise ValidationError(f'IP address must be version {self.allowed_versions}')
        except ValueError:
            raise ValidationError('Enter a valid IP address.')
        
        return super().to_internal_value(data)



