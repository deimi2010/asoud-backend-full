from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where mobile_number is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, mobile_number, password, **extra_fields):
        """
        Create and save a user with the given Mobile Number and Password.
        """
        if not mobile_number:
            raise ValueError(_("The Mobile Number must be set"))
        mobile_number = self.normalize_mobile_number(mobile_number)
        user = self.model(mobile_number=mobile_number, **extra_fields)
        user.set_unusable_password()
        user.save()
        return user

    def create_superuser(self, mobile_number, password, **extra_fields):
        """
        Create and save a SuperUser with the given Mobile Number and Password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(mobile_number, password, **extra_fields)

    def normalize_mobile_number(self, mobile_number):
        # Implement mobile number normalization based on your needs.
        # This is just a simple example; you may need to customize it.
        return ''.join(char for char in mobile_number if char.isdigit())
