"""
Management command to create default notification templates
"""

from django.core.management.base import BaseCommand
from apps.notification.models import NotificationTemplate


class Command(BaseCommand):
    help = 'Create default notification templates'
    
    def handle(self, *args, **options):
        self.stdout.write('Creating default notification templates...')
        
        templates = [
            # Order notifications
            {
                'name': 'order_confirmed_push',
                'notification_type': 'order_confirmed',
                'channel': 'push',
                'subject': 'Order Confirmed',
                'title': 'Order Confirmed',
                'body': 'Your order #{{order_id}} has been confirmed and is being processed.',
                'variables': {'order_id': 'Order ID'}
            },
            {
                'name': 'order_confirmed_email',
                'notification_type': 'order_confirmed',
                'channel': 'email',
                'subject': 'Order Confirmed - #{{order_id}}',
                'title': 'Order Confirmed',
                'body': 'Dear {{user_name}},\n\nYour order #{{order_id}} has been confirmed and is being processed.\n\nOrder Details:\n- Total: {{order_total}}\n- Items: {{item_count}}\n\nThank you for your business!',
                'variables': {'user_name': 'User name', 'order_id': 'Order ID', 'order_total': 'Order total', 'item_count': 'Item count'}
            },
            {
                'name': 'payment_success_push',
                'notification_type': 'payment_success',
                'channel': 'push',
                'subject': 'Payment Successful',
                'title': 'Payment Successful',
                'body': 'Your payment of {{amount}} has been processed successfully.',
                'variables': {'amount': 'Payment amount'}
            },
            {
                'name': 'payment_success_email',
                'notification_type': 'payment_success',
                'channel': 'email',
                'subject': 'Payment Successful - {{amount}}',
                'title': 'Payment Successful',
                'body': 'Dear {{user_name}},\n\nYour payment of {{amount}} has been processed successfully.\n\nTransaction ID: {{transaction_id}}\n\nThank you!',
                'variables': {'user_name': 'User name', 'amount': 'Payment amount', 'transaction_id': 'Transaction ID'}
            },
            
            # Message notifications
            {
                'name': 'new_message_push',
                'notification_type': 'new_message',
                'channel': 'push',
                'subject': 'New Message',
                'title': 'New Message',
                'body': 'You have a new message from {{sender_name}}.',
                'variables': {'sender_name': 'Sender name'}
            },
            {
                'name': 'new_message_websocket',
                'notification_type': 'new_message',
                'channel': 'websocket',
                'subject': 'New Message',
                'title': 'New Message',
                'body': 'You have a new message from {{sender_name}}.',
                'variables': {'sender_name': 'Sender name'}
            },
            
            # Market notifications
            {
                'name': 'market_approved_push',
                'notification_type': 'market_approved',
                'channel': 'push',
                'subject': 'Market Approved',
                'title': 'Market Approved',
                'body': 'Your market "{{market_name}}" has been approved and is now live!',
                'variables': {'market_name': 'Market name'}
            },
            {
                'name': 'market_approved_email',
                'notification_type': 'market_approved',
                'channel': 'email',
                'subject': 'Market Approved - {{market_name}}',
                'title': 'Market Approved',
                'body': 'Dear {{user_name}},\n\nCongratulations! Your market "{{market_name}}" has been approved and is now live.\n\nYou can now start selling your products.\n\nGood luck!',
                'variables': {'user_name': 'User name', 'market_name': 'Market name'}
            },
            
            # Product notifications
            {
                'name': 'product_published_push',
                'notification_type': 'product_published',
                'channel': 'push',
                'subject': 'Product Published',
                'title': 'Product Published',
                'body': 'Your product "{{product_name}}" has been published and is now available for sale.',
                'variables': {'product_name': 'Product name'}
            },
            
            # Marketing notifications
            {
                'name': 'discount_available_push',
                'notification_type': 'discount_available',
                'channel': 'push',
                'subject': 'Special Discount Available',
                'title': 'Special Discount Available',
                'body': 'Get {{discount_percent}}% off on {{product_name}}! Limited time offer.',
                'variables': {'discount_percent': 'Discount percentage', 'product_name': 'Product name'}
            },
            {
                'name': 'discount_available_email',
                'notification_type': 'discount_available',
                'channel': 'email',
                'subject': 'Special Discount - {{discount_percent}}% off!',
                'title': 'Special Discount Available',
                'body': 'Dear {{user_name}},\n\nDon\'t miss out on this amazing offer!\n\nGet {{discount_percent}}% off on {{product_name}}.\n\nUse code: {{discount_code}}\n\nValid until {{expiry_date}}.\n\nShop now!',
                'variables': {'user_name': 'User name', 'discount_percent': 'Discount percentage', 'product_name': 'Product name', 'discount_code': 'Discount code', 'expiry_date': 'Expiry date'}
            },
            
            # System notifications
            {
                'name': 'system_maintenance_push',
                'notification_type': 'system_maintenance',
                'channel': 'push',
                'subject': 'Scheduled Maintenance',
                'title': 'Scheduled Maintenance',
                'body': 'System maintenance scheduled for {{maintenance_time}}. The app may be temporarily unavailable.',
                'variables': {'maintenance_time': 'Maintenance time'}
            },
            {
                'name': 'system_maintenance_email',
                'notification_type': 'system_maintenance',
                'channel': 'email',
                'subject': 'Scheduled Maintenance - {{maintenance_time}}',
                'title': 'Scheduled Maintenance',
                'body': 'Dear {{user_name}},\n\nWe will be performing scheduled maintenance on {{maintenance_time}}.\n\nThe app may be temporarily unavailable during this time.\n\nWe apologize for any inconvenience.\n\nThank you for your understanding.',
                'variables': {'user_name': 'User name', 'maintenance_time': 'Maintenance time'}
            },
            {
                'name': 'security_alert_push',
                'notification_type': 'security_alert',
                'channel': 'push',
                'subject': 'Security Alert',
                'title': 'Security Alert',
                'body': 'Unusual activity detected on your account. Please review your account security.',
                'variables': {}
            },
            {
                'name': 'security_alert_email',
                'notification_type': 'security_alert',
                'channel': 'email',
                'subject': 'Security Alert - Unusual Activity',
                'title': 'Security Alert',
                'body': 'Dear {{user_name}},\n\nWe detected unusual activity on your account.\n\nActivity: {{activity_description}}\n\nTime: {{activity_time}}\n\nIf this was not you, please secure your account immediately.\n\nBest regards,\nSecurity Team',
                'variables': {'user_name': 'User name', 'activity_description': 'Activity description', 'activity_time': 'Activity time'}
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for template_data in templates:
            template, created = NotificationTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults=template_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'Created template: {template.name}')
            else:
                # Update existing template
                for key, value in template_data.items():
                    setattr(template, key, value)
                template.save()
                updated_count += 1
                self.stdout.write(f'Updated template: {template.name}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Template creation completed. Created: {created_count}, Updated: {updated_count}'
            )
        )

