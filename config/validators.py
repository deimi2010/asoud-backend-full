"""
Custom validators for ASOUD platform
"""

import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError

class CustomPasswordValidator:
    """
    Custom password validator with enhanced security requirements
    """
    
    def validate(self, password, user=None):
        """Validate password strength"""
        errors = []
        
        # Check minimum length
        if len(password) < 12:
            errors.append(ValidationError(
                _("Password must be at least 12 characters long."),
                code='password_too_short',
            ))
        
        # Check for uppercase letters
        if not re.search(r'[A-Z]', password):
            errors.append(ValidationError(
                _("Password must contain at least one uppercase letter."),
                code='password_no_upper',
            ))
        
        # Check for lowercase letters
        if not re.search(r'[a-z]', password):
            errors.append(ValidationError(
                _("Password must contain at least one lowercase letter."),
                code='password_no_lower',
            ))
        
        # Check for numbers
        if not re.search(r'\d', password):
            errors.append(ValidationError(
                _("Password must contain at least one number."),
                code='password_no_number',
            ))
        
        # Check for special characters
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append(ValidationError(
                _("Password must contain at least one special character."),
                code='password_no_special',
            ))
        
        # Check for common patterns
        if re.search(r'(.)\1{2,}', password):
            errors.append(ValidationError(
                _("Password cannot contain more than 2 consecutive identical characters."),
                code='password_repeated_chars',
            ))
        
        # Check for common sequences
        common_sequences = [
            '123456', 'abcdef', 'qwerty', 'password', 'admin',
            '123456789', 'abcdefgh', 'qwertyui', 'password123'
        ]
        
        password_lower = password.lower()
        for sequence in common_sequences:
            if sequence in password_lower:
                errors.append(ValidationError(
                    _("Password cannot contain common sequences."),
                    code='password_common_sequence',
                ))
                break
        
        # Check for user information
        if user:
            if user.first_name and user.first_name.lower() in password_lower:
                errors.append(ValidationError(
                    _("Password cannot contain your first name."),
                    code='password_contains_name',
                ))
            
            if user.last_name and user.last_name.lower() in password_lower:
                errors.append(ValidationError(
                    _("Password cannot contain your last name."),
                    code='password_contains_surname',
                ))
            
            if hasattr(user, 'mobile_number') and user.mobile_number:
                if user.mobile_number in password:
                    errors.append(ValidationError(
                        _("Password cannot contain your mobile number."),
                        code='password_contains_mobile',
                    ))
        
        if errors:
            raise ValidationError(errors)
    
    def get_help_text(self):
        """Return help text for password requirements"""
        return _(
            "Your password must be at least 12 characters long, contain at least one "
            "uppercase letter, one lowercase letter, one number, and one special character. "
            "It cannot contain common sequences or your personal information."
        )

class MobileNumberValidator:
    """
    Validator for Iranian mobile numbers
    """
    
    def __call__(self, value):
        if not re.match(r'^09\d{9}$', value):
            raise ValidationError(
                _('Enter a valid Iranian mobile number (e.g., 09123456789).'),
                code='invalid_mobile',
            )

class NationalCodeValidator:
    """
    Validator for Iranian national code
    """
    
    def __call__(self, value):
        if not self.is_valid_national_code(value):
            raise ValidationError(
                _('Enter a valid Iranian national code.'),
                code='invalid_national_code',
            )
    
    def is_valid_national_code(self, code):
        """Check if national code is valid"""
        if not re.match(r'^\d{10}$', code):
            return False
        
        # Check for all same digits
        if code == code[0] * 10:
            return False
        
        # Calculate check digit
        check = 0
        for i in range(9):
            check += int(code[i]) * (10 - i)
        
        remainder = check % 11
        if remainder < 2:
            return int(code[9]) == remainder
        else:
            return int(code[9]) == 11 - remainder

class FileTypeValidator:
    """
    Validator for file types
    """
    
    def __init__(self, allowed_types):
        self.allowed_types = allowed_types
    
    def __call__(self, value):
        if value.content_type not in self.allowed_types:
            raise ValidationError(
                _('File type not allowed. Allowed types: %(types)s'),
                code='invalid_file_type',
                params={'types': ', '.join(self.allowed_types)},
            )

class FileSizeValidator:
    """
    Validator for file size
    """
    
    def __init__(self, max_size):
        self.max_size = max_size
    
    def __call__(self, value):
        if value.size > self.max_size:
            raise ValidationError(
                _('File size cannot exceed %(size)s bytes.'),
                code='file_too_large',
                params={'size': self.max_size},
            )

class BusinessIdValidator:
    """
    Validator for business ID format
    """
    
    def __call__(self, value):
        if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', value):
            raise ValidationError(
                _('Business ID must be 3-50 characters long and contain only letters, numbers, hyphens, and underscores.'),
                code='invalid_business_id',
            )

class PriceValidator:
    """
    Validator for price values
    """
    
    def __call__(self, value):
        if value <= 0:
            raise ValidationError(
                _('Price must be greater than zero.'),
                code='invalid_price',
            )
        
        if value > 999999999:  # 999 million
            raise ValidationError(
                _('Price cannot exceed 999,999,999.'),
                code='price_too_high',
            )

class QuantityValidator:
    """
    Validator for quantity values
    """
    
    def __call__(self, value):
        if value < 0:
            raise ValidationError(
                _('Quantity cannot be negative.'),
                code='invalid_quantity',
            )
        
        if value > 99999:  # 99,999
            raise ValidationError(
                _('Quantity cannot exceed 99,999.'),
                code='quantity_too_high',
            )

class DiscountPercentageValidator:
    """
    Validator for discount percentage
    """
    
    def __call__(self, value):
        if value < 0 or value > 100:
            raise ValidationError(
                _('Discount percentage must be between 0 and 100.'),
                code='invalid_discount_percentage',
            )

class DateRangeValidator:
    """
    Validator for date ranges
    """
    
    def __init__(self, start_field, end_field):
        self.start_field = start_field
        self.end_field = end_field
    
    def __call__(self, data):
        start_date = data.get(self.start_field)
        end_date = data.get(self.end_field)
        
        if start_date and end_date and start_date >= end_date:
            raise ValidationError(
                _('End date must be after start date.'),
                code='invalid_date_range',
            )

class UniqueTogetherValidator:
    """
    Validator for unique together constraints
    """
    
    def __init__(self, fields, model, message=None):
        self.fields = fields
        self.model = model
        self.message = message or _('This combination already exists.')
    
    def __call__(self, data):
        filters = {field: data.get(field) for field in self.fields if data.get(field)}
        
        if len(filters) == len(self.fields):
            if self.model.objects.filter(**filters).exists():
                raise ValidationError(self.message, code='duplicate_combination')



