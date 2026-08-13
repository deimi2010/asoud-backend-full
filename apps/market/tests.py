from datetime import time

from django.db import connection
from django.test import TestCase, skipUnlessDBFeature
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.category.models import Category, Group, SubCategory
from apps.market.models import (
    Market, MarketBookmark, MarketLocation, MarketMembership, MarketRevision,
    MarketSchedule, MarketTheme,
)
from apps.region.models import City, Country, Province
from apps.reserve.models import Service
from apps.users.models import User


class MarketRevisionWorkflowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('09126660001', None)
        self.admin = User.objects.create_superuser('09126660002', None)
        group = Group.objects.create(title='Revision group', market_fee=0)
        category = Category.objects.create(group=group, title='Revision category', market_fee=0)
        self.subcategory = SubCategory.objects.create(
            category=category, title='Revision subcategory', market_fee=0
        )
        self.market = Market.objects.create(
            user=self.owner,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            business_id='REVISION-STORE',
            name='Published name',
            sub_category=self.subcategory,
        )
        self.client = APIClient()

    def test_published_edit_stays_draft_until_admin_approval(self):
        payload = {
            'type': Market.SHOP,
            'business_id': self.market.business_id,
            'name': 'Draft name',
            'description': 'draft content',
            'national_code': '',
            'sub_category': str(self.subcategory.id),
            'slogan': '',
        }
        self.client.force_authenticate(self.owner)
        updated = self.client.put(
            f'/api/v1/owner/market/update/{self.market.id}/', payload, format='json'
        )
        self.assertEqual(updated.status_code, 202)
        self.market.refresh_from_db()
        self.assertEqual(self.market.name, 'Published name')
        revision = MarketRevision.objects.get(market=self.market, status='pending')

        self.client.force_authenticate(self.admin)
        approved = self.client.post(
            f'/api/v1/admin/markets/revisions/{revision.id}/',
            {'action': 'approve'},
            format='json',
        )
        self.assertEqual(approved.status_code, 200)
        self.market.refresh_from_db()
        revision.refresh_from_db()
        self.assertEqual(self.market.name, 'Draft name')
        self.assertEqual(revision.status, MarketRevision.APPROVED)

    def test_state_changes_reject_get_and_validate_transition(self):
        self.client.force_authenticate(self.owner)
        get_response = self.client.get(f'/api/v1/owner/market/queue/{self.market.id}/')
        post_response = self.client.post(f'/api/v1/owner/market/queue/{self.market.id}/')

        self.assertEqual(get_response.status_code, 405)
        self.assertEqual(post_response.status_code, 409)

        self.market.status = Market.DRAFT
        self.market.save(update_fields=['status', 'updated_at'])
        queued = self.client.post(f'/api/v1/owner/market/queue/{self.market.id}/')
        self.assertEqual(queued.status_code, 200)
        self.market.refresh_from_db()
        self.assertEqual(self.market.status, Market.QUEUE)

    def test_published_location_edit_is_draft_until_admin_approval(self):
        country = Country.objects.create(name='Iran')
        province = Province.objects.create(country=country, name='Tehran')
        city = City.objects.create(province=province, name='Tehran')
        location = MarketLocation.objects.create(
            market=self.market,
            city=city,
            address='Published address',
            zip_code='1234567890',
            latitude='35.000000',
            longitude='51.000000',
        )
        self.client.force_authenticate(self.owner)
        drafted = self.client.put(
            f'/api/v1/owner/market/location/update/{self.market.id}/',
            {
                'city': str(city.id),
                'address': 'Draft address',
                'zip_code': '1234567890',
                'latitude': '35.100000',
                'longitude': '51.100000',
            },
            format='json',
        )
        self.assertEqual(drafted.status_code, 202)
        location.refresh_from_db()
        self.assertEqual(location.address, 'Published address')

        revision = MarketRevision.objects.get(market=self.market, status='pending')
        self.client.force_authenticate(self.admin)
        approved = self.client.post(
            f'/api/v1/admin/markets/revisions/{revision.id}/',
            {'action': 'approve'},
            format='json',
        )
        self.assertEqual(approved.status_code, 200)
        location.refresh_from_db()
        self.assertEqual(location.address, 'Draft address')

    def test_published_theme_edit_is_draft_until_admin_approval(self):
        theme = MarketTheme.objects.create(market=self.market, color='#111111')
        self.client.force_authenticate(self.owner)
        drafted = self.client.post(
            f'/api/v1/owner/market/theme/{self.market.id}/',
            {'color': '#222222'},
            format='json',
        )
        self.assertEqual(drafted.status_code, 202)
        theme.refresh_from_db()
        self.assertEqual(theme.color, '#111111')

        revision = MarketRevision.objects.get(market=self.market, status='pending')
        self.client.force_authenticate(self.admin)
        approved = self.client.post(
            f'/api/v1/admin/markets/revisions/{revision.id}/',
            {'action': 'approve'},
            format='json',
        )
        self.assertEqual(approved.status_code, 200)
        theme.refresh_from_db()
        self.assertEqual(theme.color, '#222222')


class MarketScheduleIntegrityTests(TestCase):
    create_url = '/api/v1/owner/market/schedules/create/'

    def setUp(self):
        self.owner = User.objects.create_user('09127770001', None)
        self.other_owner = User.objects.create_user('09127770002', None)
        self.viewer = User.objects.create_user('09127770003', None)
        group = Group.objects.create(title='Schedule group', market_fee=0)
        category = Category.objects.create(
            group=group,
            title='Schedule category',
            market_fee=0,
        )
        subcategory = SubCategory.objects.create(
            category=category,
            title='Schedule subcategory',
            market_fee=0,
        )
        self.market = self.create_market(self.owner, subcategory, 'SCHEDULE-1')
        self.other_market = self.create_market(
            self.other_owner,
            subcategory,
            'SCHEDULE-2',
        )
        self.client = APIClient()

    def create_market(self, owner, subcategory, business_id):
        return Market.objects.create(
            user=owner,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            business_id=business_id,
            name=business_id,
            sub_category=subcategory,
        )

    def payload(self, **overrides):
        data = {
            'market': str(self.market.id),
            'day': 1,
            'start': '09:00',
            'end': '12:00',
        }
        data.update(overrides)
        return data

    def create_schedule(self, market=None, **overrides):
        return MarketSchedule.objects.create(
            market=market or self.market,
            day_of_week=overrides.get('day_of_week', 0),
            start_time=overrides.get('start_time', time(9)),
            end_time=overrides.get('end_time', time(12)),
        )

    def test_platform_admin_can_list_and_manage_any_market_schedule(self):
        admin = User.objects.create_superuser('09127770999', None)
        schedule = self.create_schedule(self.other_market)
        self.client.force_authenticate(admin)

        listing = self.client.get('/api/v1/owner/market/schedules/list/')
        updated = self.client.put(
            f'/api/v1/owner/market/schedules/{schedule.id}/update/',
            {'start': '13:00', 'end': '14:00'},
            format='json',
        )

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(updated.status_code, 200)

    def test_owner_can_add_and_revoke_store_colleague(self):
        self.client.force_authenticate(self.owner)
        created = self.client.post(
            f'/api/v1/owner/market/memberships/{self.market.id}/',
            {'mobile_number': self.viewer.mobile_number, 'role': 'editor'},
            format='json',
        )
        self.assertEqual(created.status_code, 201)
        membership = MarketMembership.objects.get(market=self.market, user=self.viewer)

        revoked = self.client.delete(
            f'/api/v1/owner/market/memberships/detail/{membership.id}/'
        )
        self.assertEqual(revoked.status_code, 204)
        membership.refresh_from_db()
        self.assertFalse(membership.is_active)

    def test_non_owner_cannot_manage_store_colleagues(self):
        self.client.force_authenticate(self.other_owner)
        response = self.client.post(
            f'/api/v1/owner/market/memberships/{self.market.id}/',
            {'mobile_number': self.viewer.mobile_number, 'role': 'manager'},
            format='json',
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(MarketMembership.objects.exists())

    def test_create_uses_real_schedule_model_and_is_idempotent(self):
        self.client.force_authenticate(self.owner)

        created = self.client.post(self.create_url, self.payload(), format='json')
        repeated = self.client.post(self.create_url, self.payload(), format='json')

        self.assertEqual(created.status_code, 201)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(MarketSchedule.objects.count(), 1)
        self.assertEqual(Service.objects.count(), 0)
        schedule = MarketSchedule.objects.get()
        self.assertEqual(schedule.day_of_week, 0)
        self.assertEqual(
            created.data['data'],
            {
                'id': str(schedule.id),
                'market': str(self.market.id),
                'day': '1',
                'start': '09:00:00',
                'end': '12:00:00',
            },
        )

    def test_create_requires_owned_market_and_complete_valid_interval(self):
        self.client.force_authenticate(self.owner)

        foreign = self.client.post(
            self.create_url,
            self.payload(market=str(self.other_market.id)),
            format='json',
        )
        missing_end = self.client.post(
            self.create_url,
            self.payload(end=None),
            format='json',
        )
        backwards = self.client.post(
            self.create_url,
            self.payload(start='12:00', end='09:00'),
            format='json',
        )

        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(missing_end.status_code, 400)
        self.assertEqual(backwards.status_code, 400)
        self.assertFalse(MarketSchedule.objects.exists())

    def test_create_rejects_overlap_but_allows_adjacent_intervals(self):
        self.create_schedule()
        self.client.force_authenticate(self.owner)

        overlap = self.client.post(
            self.create_url,
            self.payload(start='11:00', end='13:00'),
            format='json',
        )
        adjacent = self.client.post(
            self.create_url,
            self.payload(start='12:00', end='14:00'),
            format='json',
        )

        self.assertEqual(overlap.status_code, 400)
        self.assertEqual(adjacent.status_code, 201)
        self.assertEqual(MarketSchedule.objects.count(), 2)

    def test_owner_list_update_and_delete_are_owner_scoped(self):
        schedule = self.create_schedule()
        foreign_schedule = self.create_schedule(
            market=self.other_market,
            start_time=time(14),
            end_time=time(16),
        )
        self.client.force_authenticate(self.owner)

        listing = self.client.get('/api/v1/owner/market/schedules/list/')
        malformed_filter = self.client.get(
            '/api/v1/owner/market/schedules/list/?market=not-a-uuid'
        )
        foreign_update = self.client.put(
            f'/api/v1/owner/market/schedules/{foreign_schedule.id}/update/',
            {'end': '17:00'},
            format='json',
        )
        updated = self.client.put(
            f'/api/v1/owner/market/schedules/{schedule.id}/update/',
            {'day': 2, 'start': '10:00', 'end': '13:00', 'market': self.other_market.id},
            format='json',
        )
        foreign_delete = self.client.delete(
            f'/api/v1/owner/market/schedules/{foreign_schedule.id}/delete/'
        )
        deleted = self.client.delete(
            f'/api/v1/owner/market/schedules/{schedule.id}/delete/'
        )

        self.assertEqual([item['id'] for item in listing.data['data']], [str(schedule.id)])
        self.assertEqual(malformed_filter.status_code, 400)
        self.assertEqual(foreign_update.status_code, 404)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data['data']['day'], '2')
        self.assertEqual(updated.data['data']['market'], str(self.market.id))
        self.assertEqual(foreign_delete.status_code, 404)
        self.assertEqual(deleted.status_code, 204)
        self.assertTrue(MarketSchedule.objects.filter(id=foreign_schedule.id).exists())

    def test_update_rejects_overlap(self):
        first = self.create_schedule()
        second = self.create_schedule(start_time=time(13), end_time=time(15))
        self.client.force_authenticate(self.owner)

        response = self.client.put(
            f'/api/v1/owner/market/schedules/{second.id}/update/',
            {'start': '11:00'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        second.refresh_from_db()
        self.assertEqual(second.start_time, time(13))
        self.assertTrue(MarketSchedule.objects.filter(id=first.id).exists())

    def test_user_list_exposes_only_published_market_schedule(self):
        schedule = self.create_schedule()
        self.client.force_authenticate(self.viewer)
        url = f'/api/v1/user/market/schedule/{self.market.id}/'

        published = self.client.get(url)
        self.market.status = Market.DRAFT
        self.market.save(update_fields=['status', 'updated_at'])
        withdrawn = self.client.get(url)

        self.assertEqual(published.status_code, 200)
        self.assertEqual(published.data['data'][0]['id'], str(schedule.id))
        self.assertEqual(withdrawn.status_code, 404)

    @skipUnlessDBFeature('has_select_for_update')
    def test_update_locks_market_before_schedule_on_locking_databases(self):
        schedule = self.create_schedule()
        self.client.force_authenticate(self.owner)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.put(
                f'/api/v1/owner/market/schedules/{schedule.id}/update/',
                {'end': '13:00'},
                format='json',
            )

        locking_queries = [query['sql'] for query in queries if 'FOR UPDATE' in query['sql']]
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(locking_queries), 2)
        self.assertIn('"market"', locking_queries[0])
        self.assertIn('"market_schedule"', locking_queries[1])


class MarketBookmarkIntegrityTests(TestCase):
    list_url = '/api/v1/user/market/bookmark/'

    def setUp(self):
        self.user = User.objects.create_user('09127770101', None)
        self.other_user = User.objects.create_user('09127770102', None)
        owner = User.objects.create_user('09127770103', None)
        group = Group.objects.create(title='Bookmark group', market_fee=0)
        category = Category.objects.create(
            group=group,
            title='Bookmark category',
            market_fee=0,
        )
        subcategory = SubCategory.objects.create(
            category=category,
            title='Bookmark subcategory',
            market_fee=0,
        )
        self.market = Market.objects.create(
            user=owner,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            business_id='BOOKMARK-1',
            name='Published market',
            sub_category=subcategory,
        )
        self.draft_market = Market.objects.create(
            user=owner,
            type=Market.SHOP,
            status=Market.DRAFT,
            business_id='BOOKMARK-2',
            name='Draft market',
            sub_category=subcategory,
        )
        self.client = APIClient()

    def update_url(self, market):
        return f'/api/v1/user/market/bookmark/{market.id}/'

    def test_routes_require_auth_and_reject_unpublished_market(self):
        anonymous = self.client.get(self.list_url)
        self.client.force_authenticate(self.user)
        wrong_collection_method = self.client.put(
            self.list_url,
            {'bookmarked': True},
            format='json',
        )
        wrong_detail_method = self.client.get(self.update_url(self.market))
        missing_state = self.client.put(
            self.update_url(self.market),
            {},
            format='json',
        )
        draft = self.client.put(
            self.update_url(self.draft_market),
            {'bookmarked': True},
            format='json',
        )

        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(wrong_collection_method.status_code, 405)
        self.assertEqual(wrong_detail_method.status_code, 405)
        self.assertEqual(missing_state.status_code, 400)
        self.assertEqual(draft.status_code, 404)
        self.assertFalse(MarketBookmark.objects.exists())

    def test_put_is_idempotent_and_returns_authoritative_state(self):
        self.client.force_authenticate(self.user)
        url = self.update_url(self.market)

        first = self.client.put(url, {'bookmarked': True}, format='json')
        repeated = self.client.put(url, {'bookmarked': True}, format='json')
        removed = self.client.put(url, {'bookmarked': False}, format='json')
        repeated_removal = self.client.put(
            url,
            {'bookmarked': False},
            format='json',
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(repeated_removal.status_code, 200)
        self.assertTrue(first.data['data']['bookmarked'])
        self.assertFalse(removed.data['data']['bookmarked'])
        self.assertEqual(MarketBookmark.objects.count(), 1)
        self.assertFalse(MarketBookmark.objects.get().is_active)

    def test_list_is_user_scoped_and_hides_withdrawn_markets(self):
        MarketBookmark.objects.create(user=self.user, market=self.market)
        MarketBookmark.objects.create(user=self.user, market=self.draft_market)
        MarketBookmark.objects.create(user=self.other_user, market=self.market)
        self.client.force_authenticate(self.user)

        visible = self.client.get(self.list_url)
        self.market.status = Market.DRAFT
        self.market.save(update_fields=['status', 'updated_at'])
        withdrawn = self.client.get(self.list_url)

        self.assertEqual(visible.status_code, 200)
        self.assertEqual(len(visible.data['data']), 1)
        self.assertEqual(visible.data['data'][0]['id'], str(self.market.id))
        self.assertEqual(withdrawn.status_code, 200)
        self.assertEqual(withdrawn.data['data'], [])
