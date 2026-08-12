from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APITestCase

from config.asgi import application

from .models import ChatMembershipEvent, ChatParticipant, ChatRoom
from .services import ChatMembershipError, ChatService
from apps.users.models import User


class GroupMembershipAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user('09123000001', None)
        self.admin = User.objects.create_user('09123000002', None)
        self.member = User.objects.create_user('09123000003', None)
        self.outsider = User.objects.create_user('09123000004', None)
        self.extra = User.objects.create_user('09123000005', None)
        self.room = ChatService().create_chat_room(
            name='Group',
            room_type=ChatRoom.GROUP,
            created_by=self.owner,
            participants=[self.admin, self.member],
        )
        ChatService().change_group_role(self.room, self.admin, self.owner, ChatParticipant.ADMIN)
        self.base = f'/api/v1/chat/rooms/{self.room.id}'

    def auth(self, user):
        self.client.force_authenticate(user)

    def test_01_group_creator_is_the_single_owner(self):
        owners = self.room.chat_participants.filter(role=ChatParticipant.OWNER)
        self.assertEqual(owners.count(), 1)
        self.assertEqual(owners.get().user, self.owner)

    def test_01b_group_creation_does_not_accept_enumerable_user_ids(self):
        self.auth(self.owner)
        response = self.client.post(
            '/api/v1/chat/rooms/',
            {
                'name': 'Unsafe initial members',
                'room_type': ChatRoom.GROUP,
                'participants': [self.outsider.id],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ChatRoom.objects.count(), 1)

    def test_02_owner_adds_member_by_exact_mobile(self):
        self.auth(self.owner)
        response = self.client.post(
            f'{self.base}/participants/',
            {'mobile_number': self.outsider.mobile_number, 'role': 'member'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['role'], 'member')
        self.assertEqual(
            ChatMembershipEvent.objects.filter(action=ChatMembershipEvent.MEMBER_ADDED).count(),
            4,
        )

    def test_03_duplicate_member_returns_stable_409(self):
        self.auth(self.owner)
        response = self.client.post(
            f'{self.base}/participants/',
            {'mobile_number': self.member.mobile_number},
            format='json',
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'participant_already_member')

    def test_04_admin_can_add_member_but_not_admin(self):
        self.auth(self.admin)
        added = self.client.post(
            f'{self.base}/participants/',
            {'mobile_number': self.outsider.mobile_number, 'role': 'member'},
            format='json',
        )
        rejected = self.client.post(
            f'{self.base}/participants/',
            {'mobile_number': self.extra.mobile_number, 'role': 'admin'},
            format='json',
        )
        self.assertEqual(added.status_code, 201)
        self.assertEqual(rejected.status_code, 403)

    def test_05_member_cannot_manage_members(self):
        self.auth(self.member)
        response = self.client.post(
            f'{self.base}/participants/',
            {'mobile_number': self.outsider.mobile_number},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(CHAT_GROUP_MAX_PARTICIPANTS=3)
    def test_06_room_capacity_returns_stable_409(self):
        self.auth(self.owner)
        response = self.client.post(
            f'{self.base}/participants/',
            {'mobile_number': self.outsider.mobile_number},
            format='json',
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'participant_limit_reached')

    def test_07_owner_changes_role(self):
        self.auth(self.owner)
        response = self.client.patch(
            f'{self.base}/participants/{self.member.id}/',
            {'role': 'admin'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], 'admin')

    def test_08_admin_removes_member_but_not_an_admin(self):
        self.auth(self.admin)
        removed = self.client.delete(f'{self.base}/participants/{self.member.id}/')
        rejected = self.client.delete(f'{self.base}/participants/{self.owner.id}/')
        self.assertEqual(removed.status_code, 204)
        self.assertEqual(rejected.status_code, 409)

    def test_09_owner_removes_admin(self):
        self.auth(self.owner)
        response = self.client.delete(f'{self.base}/participants/{self.admin.id}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(self.room.chat_participants.filter(user=self.admin).exists())

    def test_10_owner_with_other_members_must_transfer_before_leave(self):
        self.auth(self.owner)
        response = self.client.post(f'{self.base}/leave/', {}, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'ownership_transfer_required')

    def test_11_transfer_is_atomic_and_previous_owner_becomes_admin(self):
        self.auth(self.owner)
        response = self.client.post(
            f'{self.base}/transfer-ownership/',
            {'user_id': self.member.id},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], 'owner')
        self.assertEqual(self.room.chat_participants.get(user=self.owner).role, 'admin')
        self.assertEqual(self.room.chat_participants.filter(role='owner').count(), 1)

    def test_12_sole_owner_leave_archives_room(self):
        room = ChatService().create_chat_room(
            name='Solo', room_type=ChatRoom.GROUP, created_by=self.owner,
        )
        self.auth(self.owner)
        response = self.client.post(f'/api/v1/chat/rooms/{room.id}/leave/', {}, format='json')
        room.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(room.status, ChatRoom.ARCHIVED)
        self.assertFalse(room.chat_participants.exists())

    def test_13_private_room_membership_is_system_managed(self):
        direct = ChatService().create_chat_room(
            name='Direct',
            room_type=ChatRoom.PRIVATE,
            created_by=self.owner,
            participants=[self.member],
        )
        self.auth(self.owner)
        response = self.client.post(
            f'/api/v1/chat/rooms/{direct.id}/participants/',
            {'mobile_number': self.outsider.mobile_number},
            format='json',
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'membership_system_managed')

    def test_14_participant_list_does_not_expose_email_or_mobile(self):
        self.auth(self.member)
        response = self.client.get(f'{self.base}/participants/')
        self.assertEqual(response.status_code, 200)
        for participant in response.data:
            self.assertNotIn('email', participant)
            self.assertNotIn('mobile_number', participant)

    def test_15_only_owner_can_archive_and_delete_is_soft(self):
        self.auth(self.admin)
        forbidden = self.client.delete(f'{self.base}/')
        self.auth(self.owner)
        archived = self.client.delete(f'{self.base}/')
        self.room.refresh_from_db()
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(archived.status_code, 204)
        self.assertEqual(self.room.status, ChatRoom.ARCHIVED)
        self.assertTrue(ChatRoom.objects.filter(pk=self.room.pk).exists())

    def test_16_legacy_add_and_remove_delegate_to_same_contract(self):
        self.auth(self.owner)
        added = self.client.post(
            f'{self.base}/add_participant/',
            {'mobile_number': self.outsider.mobile_number},
            format='json',
        )
        removed = self.client.post(
            f'{self.base}/remove_participant/',
            {'user_id': self.outsider.id},
            format='json',
        )
        self.assertEqual(added.status_code, 201)
        self.assertEqual(removed.status_code, 200)


class GroupMembershipConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def test_17_concurrent_adds_cannot_exceed_capacity(self):
        if connection.vendor != 'postgresql':
            self.skipTest('Row-lock concurrency contract requires PostgreSQL')
        owner = User.objects.create_user('09123100001', None)
        candidates = [
            User.objects.create_user('09123100002', None),
            User.objects.create_user('09123100003', None),
        ]
        room = ChatService().create_chat_room(
            name='Capacity',
            room_type=ChatRoom.GROUP,
            created_by=owner,
            max_participants=2,
        )

        def add(candidate_id):
            close_old_connections()
            try:
                candidate = User.objects.get(pk=candidate_id)
                locked_owner = User.objects.get(pk=owner.pk)
                ChatService().add_group_participant(room, candidate, locked_owner)
                return 'created'
            except ChatMembershipError as exc:
                return exc.code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(add, [candidate.pk for candidate in candidates]))
        self.assertCountEqual(results, ['created', 'participant_limit_reached'])
        self.assertEqual(room.chat_participants.count(), 2)


class GroupMembershipWebSocketTests(TransactionTestCase):
    def test_18_removed_member_is_evicted_from_open_socket(self):
        owner = User.objects.create_user('09123200001', None)
        member = User.objects.create_user('09123200002', None)
        room = ChatService().create_chat_room(
            name='Socket group',
            room_type=ChatRoom.GROUP,
            created_by=owner,
            participants=[member],
        )
        async def scenario():
            payload = {'user_id': str(member.pk), 'scope': 'chat'}
            with patch(
                'apps.core.ws_auth.WebSocketTicketStore.consume',
                return_value=payload,
            ):
                communicator = WebsocketCommunicator(
                    application,
                    f'/ws/chat/{room.id}/?ticket=test-ticket',
                    headers=[(b'host', b'localhost'), (b'origin', b'http://localhost')],
                )
                connected, _ = await communicator.connect()
                self.assertTrue(connected)
                await communicator.receive_json_from()
                await database_sync_to_async(ChatService().remove_group_participant)(room, member, owner)
                revoked = None
                for _ in range(3):
                    frame = await communicator.receive_json_from(timeout=2)
                    if frame.get('type') == 'membership_revoked':
                        revoked = frame
                        break
                self.assertIsNotNone(revoked)
                self.assertEqual(revoked['type'], 'membership_revoked')
                await communicator.wait(timeout=2)

        async_to_sync(scenario)()
