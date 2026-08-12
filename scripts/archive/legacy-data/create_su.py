from django.contrib.auth import get_user_model
U = get_user_model()
if not U.objects.filter(mobile_number='09123456789').exists():
    U.objects.create_superuser('09123456789', 'admin@asoud.ir', 'admin123')
    print('created')
else:
    print('exists')
