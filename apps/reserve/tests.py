from datetime import date, time
from uuid import uuid4

from django.test import TestCase
from django.urls import resolve
from rest_framework.test import APIClient

from apps.category.models import Category, Group, SubCategory
from apps.market.models import Market, MarketMembership
from apps.reserve.models import DayOff, Reservation, ReserveTime, Service, Specialist
from apps.reserve.views.user.reservation import (
    ReservationCreateView,
    ReservationDetailView,
    ReservationListView,
)
from apps.users.models import User


class ReservationIntegrityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('09128880001', None)
        self.other_owner = User.objects.create_user('09128880002', None)
        self.buyer = User.objects.create_user('09128880003', None)
        self.other_buyer = User.objects.create_user('09128880004', None)
        group = Group.objects.create(title='Reserve group', market_fee=0)
        category = Category.objects.create(
            group=group,
            title='Reserve category',
            market_fee=0,
        )
        self.subcategory = SubCategory.objects.create(
            category=category,
            title='Reserve subcategory',
            market_fee=0,
        )
        self.market = self.create_market(self.owner, 'RESERVE-1')
        self.other_market = self.create_market(self.other_owner, 'RESERVE-2')
        self.service = Service.objects.create(market=self.market, name='Consulting')
        self.other_service = Service.objects.create(
            market=self.other_market,
            name='Foreign service',
        )
        self.specialist = Specialist.objects.create(user='Specialist One', field='General')
        self.specialist.services.add(self.service)
        self.other_specialist = Specialist.objects.create(
            user='Specialist Two',
            field='Other',
        )
        self.other_specialist.services.add(self.other_service)
        self.reserve = ReserveTime.objects.create(
            service=self.service,
            day=ReserveTime.SATURDAY,
            start=time(9),
            end=time(10),
        )
        self.client = APIClient()

    def create_market(self, owner, business_id):
        return Market.objects.create(
            user=owner,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            business_id=business_id,
            name=business_id,
            sub_category=self.subcategory,
        )

    def test_user_reservation_routes_resolve_to_correct_views(self):
        reservation_id = uuid4()
        self.assertIs(
            resolve('/api/v1/reservation/user/reservation/create').func.view_class,
            ReservationCreateView,
        )
        self.assertIs(
            resolve(
                f'/api/v1/reservation/user/reservation/{reservation_id}'
            ).func.view_class,
            ReservationDetailView,
        )
        self.assertIs(
            resolve('/api/v1/reservation/user/reservation/').func.view_class,
            ReservationListView,
        )

    def test_user_catalog_requires_published_market(self):
        DayOff.objects.create(market=self.market, date=date(2026, 7, 20))
        self.client.force_authenticate(self.buyer)
        urls = [
            f'/api/v1/reservation/user/service/?market={self.market.id}',
            f'/api/v1/reservation/user/specialist/?service={self.service.id}',
            f'/api/v1/reservation/user/reserve-time/?service={self.service.id}',
            f'/api/v1/reservation/user/dayoff/?market={self.market.id}',
        ]
        self.assertTrue(all(self.client.get(url).status_code == 200 for url in urls))

        self.market.status = Market.DRAFT
        self.market.save(update_fields=['status', 'updated_at'])

        self.assertTrue(all(self.client.get(url).status_code == 404 for url in urls))

    def test_colleague_roles_scope_reservation_management(self):
        MarketMembership.objects.create(
            market=self.market,
            user=self.buyer,
            role=MarketMembership.EDITOR,
        )
        self.client.force_authenticate(self.buyer)
        listing = self.client.get('/api/v1/reservation/owner/service/')
        updated = self.client.put(
            f'/api/v1/reservation/owner/service/{self.service.id}/update',
            {'name': 'Updated by colleague'},
            format='json',
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(updated.status_code, 200)

        membership = MarketMembership.objects.get(market=self.market, user=self.buyer)
        membership.role = MarketMembership.VIEWER
        membership.save(update_fields=('role', 'updated_at'))
        forbidden_write = self.client.put(
            f'/api/v1/reservation/owner/service/{self.service.id}/update',
            {'name': 'Forbidden'},
            format='json',
        )
        self.assertEqual(forbidden_write.status_code, 404)
        self.assertEqual(
            self.client.get('/api/v1/reservation/owner/service/').status_code,
            200,
        )

    def test_reservation_create_is_server_unpaid_and_validates_relationships(self):
        self.client.force_authenticate(self.buyer)
        paid = self.client.post(
            '/api/v1/reservation/user/reservation/create',
            {
                'reserve': str(self.reserve.id),
                'specialist': str(self.specialist.id),
                'is_paid': True,
            },
            format='json',
        )
        wrong_specialist = self.client.post(
            '/api/v1/reservation/user/reservation/create',
            {
                'reserve': str(self.reserve.id),
                'specialist': str(self.other_specialist.id),
            },
            format='json',
        )
        created = self.client.post(
            '/api/v1/reservation/user/reservation/create',
            {
                'reserve': str(self.reserve.id),
                'specialist': str(self.specialist.id),
            },
            format='json',
        )

        self.assertEqual(paid.status_code, 400)
        self.assertEqual(wrong_specialist.status_code, 400)
        self.assertEqual(created.status_code, 201)
        reservation = Reservation.objects.get()
        self.assertEqual(reservation.user, self.buyer)
        self.assertFalse(reservation.is_paid)

    def test_reservation_create_rejects_withdrawn_market(self):
        self.market.status = Market.DRAFT
        self.market.save(update_fields=['status', 'updated_at'])
        self.client.force_authenticate(self.buyer)

        response = self.client.post(
            '/api/v1/reservation/user/reservation/create',
            {
                'reserve': str(self.reserve.id),
                'specialist': str(self.specialist.id),
            },
            format='json',
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Reservation.objects.exists())

    def test_user_and_owner_reservation_details_are_scoped(self):
        reservation = Reservation.objects.create(
            user=self.buyer,
            reserve=self.reserve,
            specialist=self.specialist,
        )
        self.client.force_authenticate(self.other_buyer)
        user_detail = self.client.get(
            f'/api/v1/reservation/user/reservation/{reservation.id}'
        )
        self.client.force_authenticate(self.other_owner)
        owner_detail = self.client.get(
            f'/api/v1/reservation/owner/reservation/{reservation.id}'
        )

        self.assertEqual(user_detail.status_code, 404)
        self.assertEqual(owner_detail.status_code, 404)

    def test_specialist_services_must_all_exist_and_be_owned(self):
        self.client.force_authenticate(self.owner)
        foreign_create = self.client.post(
            '/api/v1/reservation/owner/specialist/create',
            {
                'user': 'Injected specialist',
                'services': [str(self.other_service.id)],
            },
            format='json',
        )
        foreign_update = self.client.put(
            f'/api/v1/reservation/owner/specialist/{self.specialist.id}/update',
            {'services': [str(self.other_service.id)]},
            format='json',
        )
        field_only = self.client.put(
            f'/api/v1/reservation/owner/specialist/{self.specialist.id}/update',
            {'field': 'Updated'},
            format='json',
        )

        self.assertEqual(foreign_create.status_code, 400)
        self.assertEqual(foreign_update.status_code, 400)
        self.assertEqual(field_only.status_code, 200)
        self.assertEqual(list(self.specialist.services.all()), [self.service])

    def test_mixed_legacy_specialist_is_hidden_from_both_owners(self):
        mixed = Specialist.objects.create(user='Mixed legacy')
        mixed.services.set([self.service, self.other_service])

        self.client.force_authenticate(self.owner)
        first = self.client.get(
            f'/api/v1/reservation/owner/specialist/{mixed.id}'
        )
        self.client.force_authenticate(self.other_owner)
        second = self.client.get(
            f'/api/v1/reservation/owner/specialist/{mixed.id}'
        )

        self.assertEqual(first.status_code, 404)
        self.assertEqual(second.status_code, 404)

    def test_reserve_time_create_is_owned_validated_and_idempotent_per_day(self):
        self.client.force_authenticate(self.owner)
        missing = self.client.post(
            '/api/v1/reservation/owner/reserve-time/create',
            {
                'service': str(uuid4()),
                'day': ReserveTime.SUNDAY,
                'start': '10:00',
                'end': '11:00',
            },
            format='json',
        )
        invalid = self.client.post(
            '/api/v1/reservation/owner/reserve-time/create',
            {
                'service': str(self.service.id),
                'day': ReserveTime.SUNDAY,
                'start': '11:00',
                'end': '10:00',
            },
            format='json',
        )
        created = self.client.post(
            '/api/v1/reservation/owner/reserve-time/create',
            {
                'service': str(self.service.id),
                'day': ReserveTime.SUNDAY,
                'start': '10:00',
                'end': '11:00',
            },
            format='json',
        )
        retried = self.client.post(
            '/api/v1/reservation/owner/reserve-time/create',
            {
                'service': str(self.service.id),
                'day': ReserveTime.SUNDAY,
                'start': '12:00',
                'end': '13:00',
            },
            format='json',
        )

        self.assertEqual(missing.status_code, 404)
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(retried.status_code, 200)
        self.assertEqual(
            ReserveTime.objects.filter(service=self.service, day=ReserveTime.SUNDAY).count(),
            1,
        )

        reserve_move = self.client.put(
            f'/api/v1/reservation/owner/reserve-time/{self.reserve.id}/update',
            {'service': str(self.other_service.id)},
            format='json',
        )
        service_move = self.client.put(
            f'/api/v1/reservation/owner/service/{self.service.id}/update',
            {'market': str(self.other_market.id)},
            format='json',
        )
        self.assertEqual(reserve_move.status_code, 400)
        self.assertEqual(service_move.status_code, 400)

    def test_reservation_history_blocks_destructive_owner_deletes(self):
        reservation = Reservation.objects.create(
            user=self.buyer,
            reserve=self.reserve,
            specialist=self.specialist,
        )
        self.client.force_authenticate(self.owner)
        alternate_service = Service.objects.create(
            market=self.market,
            name='Alternate',
        )

        reserve_delete = self.client.delete(
            f'/api/v1/reservation/owner/reserve-time/{self.reserve.id}/delete'
        )
        service_delete = self.client.delete(
            f'/api/v1/reservation/owner/service/{self.service.id}/delete'
        )
        specialist_delete = self.client.delete(
            f'/api/v1/reservation/owner/specialist/{self.specialist.id}/delete'
        )
        reserve_update = self.client.put(
            f'/api/v1/reservation/owner/reserve-time/{self.reserve.id}/update',
            {'start': '11:00', 'end': '12:00'},
            format='json',
        )
        reserve_exact_retry = self.client.put(
            f'/api/v1/reservation/owner/reserve-time/{self.reserve.id}/update',
            {'start': '09:00', 'end': '10:00'},
            format='json',
        )
        reserve_upsert = self.client.post(
            '/api/v1/reservation/owner/reserve-time/create',
            {
                'service': str(self.service.id),
                'day': ReserveTime.SATURDAY,
                'start': '11:00',
                'end': '12:00',
            },
            format='json',
        )
        specialist_detach = self.client.put(
            f'/api/v1/reservation/owner/specialist/{self.specialist.id}/update',
            {'services': [str(alternate_service.id)]},
            format='json',
        )

        self.assertEqual(reserve_delete.status_code, 409)
        self.assertEqual(service_delete.status_code, 409)
        self.assertEqual(specialist_delete.status_code, 409)
        self.assertEqual(reserve_update.status_code, 409)
        self.assertEqual(reserve_exact_retry.status_code, 200)
        self.assertEqual(reserve_upsert.status_code, 409)
        self.assertEqual(specialist_detach.status_code, 409)
        self.assertTrue(Reservation.objects.filter(id=reservation.id).exists())

    def test_day_off_create_is_owned_and_idempotent(self):
        self.client.force_authenticate(self.owner)
        payload = {'market': str(self.market.id), 'date': '2026-07-20'}
        created = self.client.post(
            '/api/v1/reservation/owner/dayoff/create',
            payload,
            format='json',
        )
        repeated = self.client.post(
            '/api/v1/reservation/owner/dayoff/create',
            payload,
            format='json',
        )
        foreign = self.client.post(
            '/api/v1/reservation/owner/dayoff/create',
            {'market': str(self.other_market.id), 'date': '2026-07-21'},
            format='json',
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(DayOff.objects.count(), 1)
