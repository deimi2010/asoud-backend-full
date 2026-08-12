from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.chat.models import ChatRoom, ChatMessage
from apps.cart.models import Cart, Order

User = get_user_model()


class ChatModelsTestCase(TestCase):
    """Test cases for Chat models"""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            mobile_number='09120000001',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            mobile_number='09120000002',
            password='testpass123'
        )
        
    def test_chat_conversation_str(self):
        """Test ChatConversation __str__ method"""
        conversation = ChatRoom.objects.create(name="Test room", created_by=self.user1)
        self.assertIn("Test room", str(conversation))

        conversation.add_participant(self.user1)
        conversation.add_participant(self.user2)
        self.assertEqual(conversation.get_participant_count(), 2)
        
    def test_chat_message_str(self):
        """Test ChatMessage __str__ method"""
        conversation = ChatRoom.objects.create(name="Test room", created_by=self.user1)
        conversation.add_participant(self.user1)
        
        # Test text message
        message = ChatMessage.objects.create(
            chat_room=conversation,
            sender=self.user1,
            content="Hello, this is a test message"
        )
        self.assertIn("Hello, this is a test message", str(message))
        self.assertIn(self.user1.mobile_number, str(message))
        
        # Test empty message
        empty_message = ChatMessage.objects.create(
            chat_room=conversation,
            sender=self.user1
        )
        self.assertIn(self.user1.mobile_number, str(empty_message))


class CartModelsTestCase(TestCase):
    """Test cases for Cart models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            mobile_number='09120000003',
            password='testpass123'
        )
        
    def test_cart_str(self):
        """Test Cart __str__ method"""
        cart = Cart.objects.create(user=self.user)
        self.assertEqual(str(cart), f"Cart for {self.user.username}")
        
    def test_cart_total_calculations(self):
        """Test Cart total price and items calculations"""
        cart = Cart.objects.create(user=self.user)
        
        # Test empty cart
        self.assertEqual(cart.total_price(), 0)
        self.assertEqual(cart.total_items(), 0)


class OrderModelsTestCase(TestCase):
    """Test cases for Order models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            mobile_number='09120000004',
            password='testpass123'
        )
        
    def test_order_str(self):
        """Test Order __str__ method"""
        order = Order.objects.create(
            user=self.user,
            type=Order.ONLINE
        )
        self.assertIn("Order", str(order))
        
    def test_order_get_or_create(self):
        """Test Order get_or_create_order method"""
        # First call should create a new order
        order1 = Order.get_or_create_order(self.user)
        self.assertEqual(order1.user, self.user)
        self.assertEqual(order1.status, Order.DRAFT)
        
        # Second call should return the same order
        order2 = Order.get_or_create_order(self.user)
        self.assertEqual(order1.id, order2.id)
        
    def test_order_total_calculations(self):
        """Test Order total price and items calculations"""
        order = Order.objects.create(
            user=self.user,
            type=Order.ONLINE
        )
        
        # Test empty order
        self.assertEqual(order.total_price(), 0)
        self.assertEqual(order.total_items(), 0)
