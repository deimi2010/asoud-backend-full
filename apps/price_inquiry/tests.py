from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APIClient
from django.test import TestCase

from apps.category.models import Category, Group, SubCategory
from apps.market.models import Market
from apps.price_inquiry.models import Inquiry, InquiryAnswer
from apps.users.models import BankInfo, User, UserBankInfo


class InquiryAndBankPrivacyTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user('09123330001', None)
        self.other_user = User.objects.create_user('09123330002', None)
        self.owner = User.objects.create_user('09123330003', None)
        group = Group.objects.create(title='Inquiry group', market_fee=Decimal('0'))
        category = Category.objects.create(
            group=group,
            title='Inquiry category',
            market_fee=Decimal('0'),
        )
        subcategory = SubCategory.objects.create(
            category=category,
            title='Inquiry subcategory',
            market_fee=Decimal('0'),
        )
        self.market = Market.objects.create(
            user=self.owner,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            business_id='INQUIRY-OWNER',
            name='Inquiry owner market',
            sub_category=subcategory,
        )
        self.client = APIClient()

    def create_inquiry(self, user=None, **overrides):
        data = {
            'user': user or self.buyer,
            'type': Inquiry.GOOD,
            'name': 'Laptop quote',
            'expiry': timezone.now() + timedelta(days=2),
        }
        data.update(overrides)
        return Inquiry.objects.create(**data)

    def test_public_bank_share_exposes_only_intended_fields(self):
        bank = BankInfo.objects.create(name='Test Bank')
        bank_info = UserBankInfo.objects.create(
            user=self.buyer,
            bank_info=bank,
            card_number='6037991234567890',
            account_number='SECRET-ACCOUNT',
            iban='IR-SECRET-IBAN',
            full_name='Buyer Name',
            branch_id=123,
            branch_name='Secret Branch',
            description='private note',
        )

        response = self.client.get(f'/bank/share/{bank_info.id}')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertEqual(
            set(response.data['data']),
            {'id', 'bank_info', 'card_number', 'full_name'},
        )
        self.assertNotIn('SECRET-ACCOUNT', str(response.data))

    def test_user_cannot_read_update_or_delete_another_users_inquiry(self):
        inquiry = self.create_inquiry()
        self.client.force_authenticate(self.other_user)
        base = f'/api/v1/user/inquiries/{inquiry.id}'

        self.assertEqual(self.client.get(f'{base}/').status_code, 404)
        self.assertEqual(
            self.client.put(f'{base}/update/', {'name': 'stolen'}, format='json').status_code,
            404,
        )
        self.assertEqual(self.client.delete(f'{base}/delete/').status_code, 404)
        inquiry.refresh_from_db()
        self.assertEqual(inquiry.name, 'Laptop quote')

    def test_flutter_finalize_contract_is_idempotent_and_freezes_content(self):
        inquiry = self.create_inquiry()
        self.client.force_authenticate(self.buyer)
        url = f'/api/v1/user/inquiries/{inquiry.id}/send/'

        first = self.client.post(url, {'send': True}, format='json')
        second = self.client.post(url, {'send': True}, format='json')
        update = self.client.put(
            f'/api/v1/user/inquiries/{inquiry.id}/update/',
            {'name': 'changed after send'},
            format='json',
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(update.status_code, 409)
        inquiry.refresh_from_db()
        self.assertEqual(inquiry.send, Inquiry.CHAT)
        self.assertEqual(inquiry.name, 'Laptop quote')

    def test_create_and_renew_reject_past_expiry(self):
        self.client.force_authenticate(self.buyer)
        past = timezone.now() - timedelta(minutes=1)
        create = self.client.post(
            '/api/v1/user/inquiries/create/',
            {
                'type': Inquiry.GOOD,
                'name': 'Expired',
                'expiry': past.isoformat(),
            },
            format='json',
        )
        inquiry = self.create_inquiry()
        renew = self.client.post(
            f'/api/v1/user/inquiries/{inquiry.id}/expiry/',
            {'expiry': past.isoformat()},
            format='json',
        )

        self.assertEqual(create.status_code, 400)
        self.assertEqual(renew.status_code, 400)

    def test_owner_feed_contains_only_finalized_active_inquiries(self):
        active = self.create_inquiry(send=Inquiry.CHAT)
        self.create_inquiry(name='Draft inquiry')
        self.create_inquiry(
            name='Expired inquiry',
            send=Inquiry.CHAT,
            expiry=timezone.now() - timedelta(minutes=1),
        )
        self.client.force_authenticate(self.other_user)
        self.assertEqual(self.client.get('/api/v1/owner/inquiries/').status_code, 403)

        self.client.force_authenticate(self.owner)
        response = self.client.get('/api/v1/owner/inquiries/')

        self.assertEqual(response.status_code, 200)
        payload = str(response.data)
        self.assertIn(str(active.id), payload)
        self.assertNotIn('Draft inquiry', payload)
        self.assertNotIn('Expired inquiry', payload)
        self.assertNotIn(self.buyer.mobile_number, payload)

    def test_only_market_owner_can_answer_active_inquiry_once(self):
        inquiry = self.create_inquiry(send=Inquiry.CHAT)
        payload = {
            'inquiry': str(inquiry.id),
            'detail': 'Available tomorrow',
            'total': '125000',
        }
        self.client.force_authenticate(self.other_user)
        self.assertEqual(
            self.client.post(
                '/api/v1/owner/inquiries/answers/create/',
                payload,
                format='json',
            ).status_code,
            403,
        )

        self.client.force_authenticate(self.owner)
        first = self.client.post(
            '/api/v1/owner/inquiries/answers/create/',
            payload,
            format='json',
        )
        duplicate = self.client.post(
            '/api/v1/owner/inquiries/answers/create/',
            payload,
            format='json',
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(InquiryAnswer.objects.filter(inquiry=inquiry).count(), 1)

    def test_answer_visibility_is_scoped_to_inquiry_creator(self):
        inquiry = self.create_inquiry(send=Inquiry.CHAT)
        answer = InquiryAnswer.objects.create(
            inquiry=inquiry,
            user=self.owner,
            detail='Quote',
            total='1000',
        )
        list_url = f'/api/v1/user/inquiries/{inquiry.id}/answers/'
        detail_url = f'{list_url}{answer.id}'
        self.client.force_authenticate(self.other_user)
        self.assertEqual(self.client.get(list_url).status_code, 404)
        self.assertEqual(self.client.get(detail_url).status_code, 404)

        self.client.force_authenticate(self.buyer)
        self.assertEqual(self.client.get(list_url).status_code, 200)
        self.assertEqual(self.client.get(detail_url).status_code, 200)

    def test_flutter_delete_method_removes_only_owned_inquiry(self):
        draft = self.create_inquiry()
        sent = self.create_inquiry(name='Finalized', send=Inquiry.CHAT)
        answer = InquiryAnswer.objects.create(
            inquiry=sent,
            user=self.owner,
            detail='Preserved quote',
            total='1000',
        )
        self.client.force_authenticate(self.buyer)

        draft_response = self.client.delete(
            f'/api/v1/user/inquiries/{draft.id}/delete/'
        )
        sent_response = self.client.delete(
            f'/api/v1/user/inquiries/{sent.id}/delete/'
        )

        self.assertEqual(draft_response.status_code, 200)
        self.assertEqual(sent_response.status_code, 409)
        self.assertFalse(Inquiry.objects.filter(id=draft.id).exists())
        self.assertTrue(Inquiry.objects.filter(id=sent.id).exists())
        self.assertTrue(InquiryAnswer.objects.filter(id=answer.id).exists())
