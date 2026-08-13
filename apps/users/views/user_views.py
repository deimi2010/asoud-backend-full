import hashlib
import logging
import secrets

from rest_framework import views, status, permissions
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import OpenApiResponse, extend_schema
from utils.response import ApiResponse
from apps.users.models import BankInfo, User, UserBankInfo, UserProfile
from apps.sms.sms_core import SMSCoreHandler
from apps.users import serializers
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError, transaction
from django.db.models import Q
from redis import RedisError

from apps.core.rate_limit import AtomicRateThrottle
from apps.core.ws_tickets import WebSocketTicketStore


logger = logging.getLogger(__name__)
OTP_TTL_SECONDS = 120
OTP_MAX_ATTEMPTS = 5
OTP_ISSUANCE_LOCK_SECONDS = 60


class SelfProfileView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _response_data(self, user):
        profile = UserProfile.objects.filter(user=user).first()
        return {
            "id": user.id,
            "mobile_number": user.mobile_number,
            "profile": serializers.UserProfileSerializer(profile).data
            if profile
            else None,
        }

    @extend_schema(responses={200: serializers.SelfProfileEnvelopeSerializer})
    def get(self, request):
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=self._response_data(request.user),
            )
        )

    @extend_schema(
        request=serializers.SelfProfileUpdateSerializer,
        responses={200: serializers.SelfProfileEnvelopeSerializer},
        description=(
            "Partially updates the authenticated user profile. All request fields are "
            "optional for an existing profile; national_code is required on first creation."
        ),
    )
    @transaction.atomic
    def put(self, request):
        if "iban_number" in request.data:
            raise ValidationError(
                {
                    "iban_number": "IBAN updates are unavailable until schema reconciliation."
                }
            )
        user = User.objects.select_for_update().get(id=request.user.id)
        profile = UserProfile.objects.select_for_update().filter(user=user).first()
        if profile is None and not request.data.get("national_code"):
            raise ValidationError(
                {"national_code": "This field is required when creating a profile."}
            )
        serializer = serializers.SelfProfileUpdateSerializer(
            profile,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=self._response_data(user),
            )
        )


def _otp_cache_key(mobile_number):
    digest = hashlib.sha256(mobile_number.encode("utf-8")).hexdigest()
    return f"auth:otp:{digest}"


def _otp_invite_cache_key(mobile_number):
    return f"{_otp_cache_key(mobile_number)}:invite"


def _otp_cache_available():
    backend = settings.CACHES.get("default", {}).get("BACKEND", "")
    allow_local = getattr(settings, "OTP_ALLOW_LOCAL_CACHE", False)
    if not allow_local and not backend.endswith("RedisCache"):
        return False

    probe_key = f"auth:otp-health:{secrets.token_hex(8)}"
    try:
        if not cache.add(probe_key, "ok", 5):
            return False
        return cache.get(probe_key) == "ok"
    except Exception:
        logger.warning("OTP cache health check failed", exc_info=True)
        return False
    finally:
        try:
            cache.delete(probe_key)
        except Exception:
            pass


@extend_schema(
    summary="Create PIN Code",
    description="Generate and send a 4-digit PIN code to the provided mobile number for user authentication. Rate limited to 5 requests per minute.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "mobile_number": {
                    "type": "string",
                    "description": "Iranian mobile number (11 digits starting with 09)",
                    "example": "09123456789",
                },
                "invite_token": {
                    "type": "string",
                    "format": "uuid",
                    "description": "Optional store/app invitation token",
                },
            },
            "required": ["mobile_number"],
        }
    },
    responses={
        200: OpenApiResponse(description="PIN code created and sent successfully"),
        400: OpenApiResponse(description="Validation error"),
        429: OpenApiResponse(description="Rate limit exceeded"),
        500: OpenApiResponse(description="Internal server error"),
    },
    tags=["Authentication"],
)
class PinCreateAPIView(views.APIView):
    """
    API view for creating PIN codes for user authentication.

    This view handles user signup/login by creating a PIN code
    and sending it via SMS to the provided mobile number.

    Attributes:
        permission_classes: AllowAny - No authentication required
        throttle_classes: ScopedRateThrottle for pin_create rate limiting
        throttle_scope: 'pin_create' (5 requests per minute)
    """

    permission_classes = (AllowAny,)
    throttle_classes = [AtomicRateThrottle]
    throttle_scope = "pin_create"

    def post(self, request, format=None):
        """
        User Singup/Login
        required fields: mobile_number(Unique)
        return: 200: {}, 400: Validation Error, 500: Server Error
        """
        mobile_number = request.data.get("mobile_number")
        invite_token = request.data.get("invite_token")

        # Validation
        if not mobile_number:
            response = ApiResponse(
                success=False,
                code=400,
                error={
                    "code": "validation_error",
                    "detail": "mobile_number is required",
                },
            )
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        # Basic mobile number format validation (Iranian format)
        if (
            not isinstance(mobile_number, str)
            or not mobile_number.isdigit()
            or not mobile_number.startswith("09")
            or len(mobile_number) != 11
        ):
            response = ApiResponse(
                success=False,
                code=400,
                error={
                    "code": "validation_error",
                    "detail": "Invalid mobile number format. Must be 11 digits starting with 09",
                },
            )
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        if not _otp_cache_available():
            return Response(
                ApiResponse(
                    success=False,
                    code=503,
                    error={
                        "code": "otp_storage_unavailable",
                        "detail": "Verification service is unavailable.",
                    },
                ),
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        invite = None
        if invite_token:
            from apps.referral.services import get_valid_invite

            invite = get_valid_invite(invite_token)
            if invite is None:
                return Response(
                    ApiResponse(
                        success=False,
                        code=400,
                        error={"code": "invalid_invitation", "detail": "Invalid invitation."},
                    ),
                    status=status.HTTP_400_BAD_REQUEST,
                )

        issuance_lock_key = f"{_otp_cache_key(mobile_number)}:issuing"
        if not cache.add(issuance_lock_key, True, OTP_ISSUANCE_LOCK_SECONDS):
            return Response(
                ApiResponse(
                    success=False,
                    code=429,
                    error={
                        "code": "otp_request_in_progress",
                        "detail": "Please wait before requesting another code.",
                    },
                ),
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        otp_key = None
        try:
            pin = f"{secrets.randbelow(9000) + 1000:04d}"
            otp_key = _otp_cache_key(mobile_number)
            otp_hash = make_password(pin)
            cache.set(otp_key, otp_hash, OTP_TTL_SECONDS)
            cache.delete(f"{otp_key}:attempts")
            if cache.get(otp_key) != otp_hash:
                raise RuntimeError("OTP cache write was not durable")

            try:
                result = SMSCoreHandler.send_verification_code(mobile_number, pin)
            except Exception:
                logger.warning("OTP provider request failed", exc_info=True)
                result = None
            if not result or result.get("status") != 1:
                cache.delete(otp_key)
                return Response(
                    ApiResponse(
                        success=False,
                        code=503,
                        error={
                            "code": "otp_delivery_unavailable",
                            "detail": "Verification delivery is unavailable.",
                        },
                    ),
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            user_obj, user_created = User.objects.get_or_create(mobile_number=mobile_number)
            if invite is not None:
                cache.set(
                    _otp_invite_cache_key(mobile_number),
                    str(invite.token),
                    OTP_TTL_SECONDS,
                )
                if user_created:
                    from apps.referral.models import SignupInviteIntent

                    SignupInviteIntent.objects.get_or_create(
                        user=user_obj,
                        defaults={"invite_link": invite},
                    )
            else:
                cache.delete(_otp_invite_cache_key(mobile_number))
            # Clear legacy plaintext PIN storage. New OTP state lives only as a
            # salted hash in the shared cache with a hard TTL.
            User.objects.filter(id=user_obj.id).update(pin=None, pin_expiry=None)

            success_response = ApiResponse(
                success=True,
                code=200,
                data={},
                message="Pin has been created successfully",
            )

            return Response(success_response, status=HTTP_200_OK)

        except Exception:
            logger.exception("OTP creation failed")
            if otp_key:
                cache.delete(otp_key)
            response = ApiResponse(
                success=False,
                code=500,
                error={
                    "code": "server_error",
                    "detail": "Server error",
                },
            )

            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Verify PIN Code",
    description="Verify the PIN code sent to user's mobile number and receive an authentication token.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "mobile_number": {
                    "type": "string",
                    "description": "Iranian mobile number",
                    "example": "09123456789",
                },
                "pin": {
                    "type": "integer",
                    "description": "4-digit PIN code",
                    "example": 1234,
                },
            },
            "required": ["mobile_number", "pin"],
        }
    },
    responses={
        200: OpenApiResponse(description="PIN verified; authentication token returned"),
        400: OpenApiResponse(description="Validation error or incorrect PIN"),
        404: OpenApiResponse(description="User not found"),
        500: OpenApiResponse(description="Internal server error"),
    },
    tags=["Authentication"],
)
class PinVerifyAPIView(views.APIView):
    """
    API view for verifying PIN codes and creating authentication tokens.

    This view verifies the PIN code sent to the user's mobile number
    and creates a Django REST Framework token for authentication.

    Attributes:
        permission_classes: AllowAny - No authentication required
        throttle_classes: ScopedRateThrottle for pin_verify rate limiting
        throttle_scope: 'pin_verify' (10 requests per minute)
    """

    permission_classes = (AllowAny,)
    throttle_classes = [AtomicRateThrottle]
    throttle_scope = "pin_verify"

    def post(self, request, format=None):
        mobile_number = request.data.get("mobile_number")
        pin = request.data.get("pin")

        # Validation
        if not mobile_number:
            response = ApiResponse(
                success=False,
                code=400,
                error={
                    "code": "validation_error",
                    "detail": "mobile_number is required",
                },
            )
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        if not pin:
            response = ApiResponse(
                success=False,
                code=400,
                error={
                    "code": "validation_error",
                    "detail": "pin is required",
                },
            )
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        if not _otp_cache_available():
            return Response(
                ApiResponse(
                    success=False,
                    code=503,
                    error={
                        "code": "otp_storage_unavailable",
                        "detail": "Verification service is unavailable.",
                    },
                ),
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            pin = str(pin)
            if len(pin) != 4 or not pin.isdigit():
                raise ValueError("invalid OTP format")

            otp_key = _otp_cache_key(str(mobile_number))
            invite_token = cache.get(_otp_invite_cache_key(str(mobile_number)))
            otp_hash = cache.get(otp_key)
            if not otp_hash or not check_password(pin, otp_hash):
                attempts_key = f"{otp_key}:attempts"
                cache.add(attempts_key, 0, OTP_TTL_SECONDS)
                try:
                    attempts = cache.incr(attempts_key)
                except ValueError:
                    attempts = 1
                    cache.set(attempts_key, attempts, OTP_TTL_SECONDS)
                if attempts >= OTP_MAX_ATTEMPTS:
                    cache.delete(otp_key)
                raise ValueError("invalid OTP")

            consume_digest = hashlib.sha256(otp_hash.encode("utf-8")).hexdigest()
            if not cache.add(
                f"auth:otp-consumed:{consume_digest}",
                True,
                OTP_TTL_SECONDS,
            ):
                raise ValueError("OTP already consumed")

            cache.delete_many([
                otp_key,
                f"{otp_key}:attempts",
                _otp_invite_cache_key(str(mobile_number)),
            ])
            with transaction.atomic():
                user = User.objects.select_for_update().get(mobile_number=mobile_number)
                if not user.is_active:
                    raise ValueError("inactive user")
                Token.objects.filter(user=user).delete()
                token = Token.objects.create(user=user)
                user.pin = None
                user.pin_expiry = None
                user.save(update_fields=["pin", "pin_expiry"])

                store_access = None
                if invite_token:
                    from apps.referral.models import SignupInviteIntent
                    from apps.referral.services import accept_store_invite, get_valid_invite

                    invite = get_valid_invite(invite_token, for_update=True)
                    if invite is not None:
                        intent = SignupInviteIntent.objects.select_for_update().filter(
                            user=user,
                            invite_link=invite,
                            consumed_at__isnull=True,
                        ).first()
                        store_access, _ = accept_store_invite(
                            user=user,
                            invite=invite,
                            allow_referral_attribution=intent is not None,
                        )
                        if intent is not None:
                            from django.utils import timezone

                            intent.consumed_at = timezone.now()
                            intent.save(update_fields=["consumed_at", "updated_at"])

            from apps.analytics.models import AnalyticsEvent
            from apps.analytics.services import AnalyticsRecorder
            AnalyticsRecorder.record(
                AnalyticsEvent.LOGIN,
                user=user,
                dedupe_key=f'login:{token.created.isoformat()}:{user.pk}',
            )

            return Response(
                ApiResponse(
                    success=True,
                    code=200,
                    data={
                        "token": token.key,
                        "market_id": str(store_access.market_id) if store_access else None,
                        "business_id": store_access.market.business_id if store_access else None,
                    },
                    message="Token has been created successfully",
                ),
                status=status.HTTP_200_OK,
            )

        except (ValueError, User.DoesNotExist):
            return Response(
                ApiResponse(
                    success=False,
                    code=401,
                    error={
                        "code": "pin_not_valid",
                        "detail": "Incorrect or expired verification code.",
                    },
                ),
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except Exception:
            logger.exception("OTP verification failed")
            response = ApiResponse(
                success=False,
                code=500,
                error={
                    "code": "server_error",
                    "detail": "Server error",
                },
            )

            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutAPIView(views.APIView):
    """Revoke the authenticated user's only active v1 token."""

    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(request=None, responses={204: None}, tags=["Authentication"])
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WebSocketTicketAPIView(views.APIView):
    """Issue a path-bound, short-lived and single-use WebSocket ticket."""

    permission_classes = (permissions.IsAuthenticated,)
    throttle_classes = (AtomicRateThrottle,)
    throttle_scope = "ws_ticket"

    @extend_schema(
        request=serializers.WebSocketTicketRequestSerializer,
        responses={201: OpenApiResponse(description="One-time WebSocket ticket")},
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = serializers.WebSocketTicketRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        scope = data["scope"]

        if scope == "chat":
            from apps.chat.models import ChatParticipant

            room_id = data["room_id"]
            allowed = ChatParticipant.objects.filter(
                chat_room_id=room_id,
                user=request.user,
                chat_room__status="active",
            ).exists()
            if not allowed:
                return Response(status=status.HTTP_404_NOT_FOUND)
            path = f"/ws/chat/{room_id}/"
        elif scope == "support":
            from apps.chat.models import SupportTicket

            ticket_id = data["ticket_id"]
            tickets = SupportTicket.objects.filter(id=ticket_id)
            if not request.user.is_staff:
                tickets = tickets.filter(
                    Q(user=request.user) | Q(assigned_to=request.user)
                )
            allowed = tickets.exists()
            if not allowed:
                return Response(status=status.HTTP_404_NOT_FOUND)
            path = f"/ws/support/{ticket_id}/"
        else:
            path = "/ws/notifications"

        try:
            ticket, expires_in = WebSocketTicketStore.issue(
                user_id=request.user.pk,
                scope=scope,
                path=path,
            )
        except RedisError:
            logger.error("WebSocket ticket store unavailable")
            return Response(
                ApiResponse(
                    success=False,
                    code=503,
                    error={
                        "code": "ws_ticket_unavailable",
                        "detail": "WebSocket authentication is unavailable.",
                    },
                ),
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            ApiResponse(
                success=True,
                code=201,
                data={
                    "ticket": ticket,
                    "expires_in": expires_in,
                    "path": path,
                },
            ),
            status=status.HTTP_201_CREATED,
        )


class BanksListView(views.APIView):
    permission_classes = [
        AllowAny,
    ]

    @extend_schema(
        operation_id="bank_catalog_list",
        responses={200: serializers.BankInfoListEnvelopeSerializer},
    )
    def get(self, request):
        objs = BankInfo.objects.order_by("name")
        serializer = serializers.BankInfoSerializer(objs, many=True)
        success_response = ApiResponse(
            success=True,
            code=200,
            data=serializer.data,
            message="successful.",
        )
        return Response(success_response, status=status.HTTP_200_OK)


class BankInfoCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=serializers.UserBankInfoCreateSerializer,
        responses={201: serializers.UserBankInfoEnvelopeSerializer},
    )
    def post(self, request):
        user = request.user
        serializer = serializers.UserBankInfoCreateSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid(raise_exception=True):
            try:
                with transaction.atomic():
                    user_bank_info = serializer.save(user=user)
            except IntegrityError as exc:
                raise ValidationError(
                    {"detail": "Card or account number is already registered."}
                ) from exc
            success_response = ApiResponse(
                success=True,
                code=201,
                data=serializers.UserBankInfoListSerializer(user_bank_info).data,
                message="Created successfully.",
            )
            return Response(success_response, status=status.HTTP_201_CREATED)


class BankInfoUpdateView(views.APIView):
    """
    Update bank info with ownership verification

    Security: Only owner can update their bank information
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=serializers.UserBankInfoUpdateSerializer,
        responses={200: serializers.UserBankInfoEnvelopeSerializer},
    )
    @transaction.atomic
    def put(self, request, pk):
        try:
            # ✅ FIXED: Add ownership check in query
            user_bank_info = UserBankInfo.objects.select_for_update().get(
                id=pk,
                user=request.user,  # Ownership check!
            )
        except UserBankInfo.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    "code": "Not Found",
                    "detail": "Bank information not found",
                },
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        serializer = serializers.UserBankInfoUpdateSerializer(
            user_bank_info,
            data=request.data,
            partial=True,
            context={"request": request},
        )

        if serializer.is_valid(raise_exception=True):
            try:
                with transaction.atomic():
                    serializer.save()
            except IntegrityError as exc:
                raise ValidationError(
                    {"detail": "Card or account number is already registered."}
                ) from exc

            success_response = ApiResponse(
                success=True,
                code=200,
                data=serializers.UserBankInfoListSerializer(user_bank_info).data,
                message="User Bank Info updated successfully.",
            )
            return Response(success_response, status=status.HTTP_200_OK)


class BankInfoListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="self_bank_info_list",
        responses={200: serializers.UserBankInfoListEnvelopeSerializer},
    )
    def get(self, request):
        user = request.user

        user_bank_info_list = UserBankInfo.objects.filter(
            user=user,
        ).select_related("bank_info").order_by("-created_at")

        serializer = serializers.UserBankInfoListSerializer(
            user_bank_info_list,
            many=True,
            context={"request": request},
        )

        success_response = ApiResponse(
            success=True,
            code=200,
            data=serializer.data,
            message="Data retrieved successfully",
        )

        return Response(success_response, status=status.HTTP_200_OK)


class BankInfoDeleteView(views.APIView):
    """
    Delete bank info with ownership verification

    Security: Only owner can delete their bank information
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={204: None})
    @transaction.atomic
    def delete(self, request, pk):
        try:
            # ✅ FIXED: Add ownership check in query
            user_bank_info = UserBankInfo.objects.select_for_update().get(
                id=pk,
                user=request.user,  # Ownership check!
            )
        except UserBankInfo.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    "code": "Not Found",
                    "detail": "Bank information not found",
                },
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        user_bank_info.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BankInfoDetailView(views.APIView):
    """
    Get bank info details with ownership verification

    Security: Only owner can view their bank information
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: serializers.UserBankInfoEnvelopeSerializer})
    def get(self, request, pk):
        try:
            # ✅ FIXED: Add ownership check in query
            user_bank_info = UserBankInfo.objects.select_related("bank_info").get(
                id=pk,
                user=request.user,  # Ownership check!
            )
        except UserBankInfo.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    "code": "Not Found",
                    "detail": "Bank information not found",
                },
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        serializer = serializers.UserBankInfoListSerializer(
            user_bank_info,
            context={"request": request},
        )

        success_response = ApiResponse(
            success=True,
            code=200,
            data=serializer.data,
            message="Data retrieved successfully.",
        )
        return Response(success_response, status=status.HTTP_200_OK)
