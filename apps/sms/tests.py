from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.sms.models import Line
from apps.sms.serializers.owner import BulkSmsCreateSerializer
from apps.sms.sms_core import SMSCoreHandler
from apps.sms.views.owner import BulkSmsView, PatternSmsView
from apps.sms.views.admin import BulkSmsUpdateView
from apps.users.models import User


class SMSContainmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('09120000111', None)
        self.factory = APIRequestFactory()

    @override_settings(SMS_BILLING_ENABLED=False)
    def test_bulk_and_pattern_sending_are_disabled_without_billing(self):
        for view, path in (
            (BulkSmsView, '/sms/send/bulk/'),
            (PatternSmsView, '/sms/send/pattern/'),
        ):
            request = self.factory.post(path, {}, format='json')
            force_authenticate(request, user=self.user)
            response = view.as_view()(request)
            self.assertEqual(response.status_code, 503)

        admin = User.objects.create_user('09120000112', None, is_staff=True)
        request = self.factory.put('/sms/admin/bulk/update/missing', {}, format='json')
        force_authenticate(request, user=admin)
        response = BulkSmsUpdateView.as_view()(request, pk='missing')
        self.assertEqual(response.status_code, 503)

    def test_client_cannot_write_billing_or_provider_fields(self):
        line = Line.objects.create(number='10000001', estimated_cost=1, is_active=True)
        serializer = BulkSmsCreateSerializer(
            data={
                'line': str(line.id),
                'content': 'test',
                'to': ['09120000000'],
                'cost': 0,
                'actual_cost': 0,
                'status': 'verified',
                'packId': 'client-provider-id',
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        for field in ('cost', 'actual_cost', 'status', 'packId'):
            self.assertNotIn(field, serializer.validated_data)

    @override_settings(SMS_API={}, SMS_MOCK_SEND=False)
    @patch.dict('os.environ', {}, clear=True)
    @patch('apps.sms.sms_core.requests.post')
    def test_missing_provider_config_is_failure_not_mock_success(self, post):
        result = SMSCoreHandler.send_verification_code('09120000000', '1234')

        self.assertEqual(result['status'], 0)
        post.assert_not_called()
