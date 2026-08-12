from decimal import Decimal

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django_comments_xtd.models import XtdComment
from rest_framework.test import APIClient

from apps.category.models import Category, Group, SubCategory
from apps.market.models import Market
from apps.product.models import Product
from apps.users.models import User


class CommentIntegrityTests(TestCase):
    def setUp(self):
        Site.objects.update_or_create(
            id=settings.SITE_ID,
            defaults={'domain': 'testserver', 'name': 'testserver'},
        )
        self.user = User.objects.create_user('09126660001', None)
        self.other_user = User.objects.create_user('09126660002', None)
        self.owner = User.objects.create_user('09126660003', None)
        group = Group.objects.create(title='Comment group', market_fee=0)
        category = Category.objects.create(group=group, title='Comment category', market_fee=0)
        self.subcategory = SubCategory.objects.create(
            category=category,
            title='Comment subcategory',
            market_fee=0,
        )
        self.market = Market.objects.create(
            user=self.owner,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            business_id='COMMENT-1',
            name='Comment market',
            sub_category=self.subcategory,
        )
        self.product = self.create_product('Comment product')
        self.other_product = self.create_product('Other product')
        self.client = APIClient()

    def create_product(self, name):
        return Product.objects.create(
            market=self.market,
            type=Product.GOOD,
            name=name,
            sub_category=self.subcategory,
            stock=1,
            main_price=Decimal('1000.000'),
            status=Product.PUBLISHED,
            sell_type=Product.ONLINE,
            ship_cost_pay_type=Product.FREE,
        )

    def create_comment(self, *, product=None, user=None, text='Root', parent_id=0):
        return XtdComment.objects.create(
            content_type=ContentType.objects.get_for_model(Product),
            object_pk=str((product or self.product).id),
            site_id=settings.SITE_ID,
            user=user or self.user,
            comment=text,
            parent_id=parent_id,
        )

    def test_flutter_create_and_list_contract_returns_root_with_reply(self):
        self.client.force_authenticate(self.user)
        create = self.client.post(
            '/api/v1/user/comment/create/',
            {'content_type': 'product', 'object_id': str(self.product.id), 'comment': 'Root'},
            format='json',
        )
        reply = self.client.post(
            '/api/v1/user/comment/create/',
            {
                'content_type': 'product',
                'object_id': str(self.product.id),
                'comment': 'Reply',
                'parent_id': create.data['id'],
            },
            format='json',
        )
        nested = self.client.post(
            '/api/v1/user/comment/create/',
            {
                'content_type': 'product',
                'object_id': str(self.product.id),
                'comment': 'Hidden third level',
                'parent_id': reply.data['id'],
            },
            format='json',
        )
        listing = self.client.get(
            f'/api/v1/user/comment/comments/product/{self.product.id}/'
        )

        self.assertEqual(create.status_code, 201)
        self.assertEqual(reply.status_code, 201)
        self.assertEqual(nested.status_code, 400)
        self.assertEqual(len(listing.data), 1)
        self.assertEqual(listing.data[0]['comment'], 'Root')
        self.assertEqual(listing.data[0]['children'][0]['comment'], 'Reply')

    def test_create_rejects_unsupported_or_unpublished_target(self):
        self.product.status = Product.DRAFT
        self.product.save(update_fields=['status', 'updated_at'])
        self.client.force_authenticate(self.user)
        unpublished = self.client.post(
            '/api/v1/user/comment/create/',
            {'content_type': 'product', 'object_id': str(self.product.id), 'comment': 'Hidden'},
            format='json',
        )
        unsupported = self.client.post(
            '/api/v1/user/comment/create/',
            {'content_type': 'user', 'object_id': str(self.product.id), 'comment': 'Wrong'},
            format='json',
        )

        self.assertEqual(unpublished.status_code, 400)
        self.assertEqual(unsupported.status_code, 400)
        self.assertFalse(XtdComment.objects.exists())

    def test_reply_parent_must_belong_to_same_target(self):
        parent = self.create_comment(product=self.other_product)
        self.client.force_authenticate(self.user)
        response = self.client.post(
            '/api/v1/user/comment/create/',
            {
                'content_type': 'product',
                'object_id': str(self.product.id),
                'comment': 'Cross-target reply',
                'parent_id': parent.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(XtdComment.objects.count(), 1)

    def test_private_and_removed_comments_are_not_public(self):
        private = self.create_comment(text='Private')
        private.is_public = False
        private.save(update_fields=['is_public'])
        removed = self.create_comment(text='Removed')
        removed.is_removed = True
        removed.save(update_fields=['is_removed'])

        listing = self.client.get(
            f'/api/v1/user/comment/comments/product/{self.product.id}/'
        )
        self.assertEqual(listing.data, [])
        self.assertEqual(self.client.get(f'/api/v1/user/comment/{private.id}/').status_code, 404)
        self.assertEqual(self.client.get(f'/api/v1/user/comment/{removed.id}/').status_code, 404)

    def test_update_is_owner_scoped_and_only_changes_content(self):
        comment = self.create_comment()
        self.client.force_authenticate(self.other_user)
        denied = self.client.put(
            f'/api/v1/user/comment/update/{comment.id}/',
            {'comment': 'stolen'},
            format='json',
        )
        self.client.force_authenticate(self.user)
        updated = self.client.put(
            f'/api/v1/user/comment/update/{comment.id}/',
            {'comment': 'Edited', 'user': self.other_user.id, 'parent_id': 999},
            format='json',
        )

        self.assertEqual(denied.status_code, 404)
        self.assertEqual(updated.status_code, 200)
        comment.refresh_from_db()
        self.assertEqual(comment.comment, 'Edited')
        self.assertEqual(comment.user, self.user)
        self.assertEqual(comment.parent_id, comment.id)

        self.product.status = Product.DRAFT
        self.product.save(update_fields=['status', 'updated_at'])
        self.assertEqual(
            self.client.get(f'/api/v1/user/comment/{comment.id}/').status_code,
            404,
        )
        self.assertEqual(
            self.client.put(
                f'/api/v1/user/comment/update/{comment.id}/',
                {'comment': 'hidden edit'},
                format='json',
            ).status_code,
            404,
        )

    def test_public_list_caps_roots_without_per_root_queries(self):
        for index in range(105):
            self.create_comment(text=f'Root {index}')
        url = f'/api/v1/user/comment/comments/product/{self.product.id}/'

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 100)
        self.assertLessEqual(len(queries), 6)
