import os
import uuid

def upload_market_logo(instance, filename):
    _, extension = os.path.splitext(filename)
    extension = extension.lower()
    return f"market/logo/{uuid.uuid4()}{extension}"

def upload_market_background(instance, filename):
    _, extension = os.path.splitext(filename)
    extension = extension.lower()
    return f"market/background/{uuid.uuid4()}{extension}"

def upload_market_userOnly(instance, filename):
    _, extension = os.path.splitext(filename)
    extension = extension.lower()
    return f"market/user-only/{uuid.uuid4()}{extension}"

def upload_market_slider(instance, filename):
    _, extension = os.path.splitext(filename)
    extension = extension.lower()
    return f"market/slider/{uuid.uuid4()}{extension}"

