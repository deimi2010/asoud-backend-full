from rest_framework import serializers
from apps.users.models import BankInfo, User, UserBankInfo, UserDocument, UserProfile


def _valid_card_checksum(value):
    if value[:8] == "00000000":
        return False
    total = 0
    for index, character in enumerate(value):
        weighted = int(character) * (2 if index % 2 == 0 else 1)
        total += weighted - 9 if weighted > 9 else weighted
    return total % 10 == 0


def _valid_iranian_iban_checksum(value):
    numeric = f"{value[4:]}1827{value[2:4]}"
    return int(numeric) % 97 == 1


class UserSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "mobile_number"]


class BankInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankInfo
        fields = ("id", "name", "logo")


class BankInfoListEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = BankInfoSerializer(many=True)
    message = serializers.CharField()


class UserBankInfoCreateSerializer(serializers.ModelSerializer):
    bank_info = serializers.UUIDField(write_only=True)

    class Meta:
        model = UserBankInfo
        fields = (
            "bank_info",
            "card_number",
            "account_number",
            "iban",
            "full_name",
            "branch_id",
            "branch_name",
            "description",
        )

    def create(self, validated_data):
        bank_info_id = validated_data.pop("bank_info")
        try:
            bank_info = BankInfo.objects.get(id=bank_info_id)
        except BankInfo.DoesNotExist:
            raise serializers.ValidationError({"bank_info": "Bank info not found"})

        user_bank_info = UserBankInfo.objects.create(
            bank_info=bank_info, **validated_data
        )
        return user_bank_info

    def validate_card_number(self, value):
        if len(value) != 16 or not value.isascii() or not value.isdecimal():
            raise serializers.ValidationError("Card number must contain 16 digits.")
        if not _valid_card_checksum(value):
            raise serializers.ValidationError("Card number checksum is invalid.")
        return value

    def validate_account_number(self, value):
        if not value.isascii() or not value.isdecimal():
            raise serializers.ValidationError("Account number must contain digits only.")
        return value

    def validate_iban(self, value):
        if not value:
            return value
        normalized = value.replace(" ", "").upper()
        if (
            len(normalized) != 26
            or not normalized.startswith("IR")
            or not normalized[2:].isascii()
            or not normalized[2:].isdecimal()
        ):
            raise serializers.ValidationError(
                "IBAN must contain IR followed by 24 digits."
            )
        if not _valid_iranian_iban_checksum(normalized):
            raise serializers.ValidationError("IBAN checksum is invalid.")
        return normalized

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["bank_info"] = (
            instance.bank_info.name if instance.bank_info else None
        )
        return representation


class UserBankInfoUpdateSerializer(UserBankInfoCreateSerializer):
    bank_info = serializers.UUIDField(required=False)  # Make it optional for updates

    class Meta:
        model = UserBankInfo
        fields = (
            "id",
            "bank_info",
            "card_number",
            "account_number",
            "iban",
            "full_name",
            "branch_id",
            "branch_name",
            "description",
        )
        extra_kwargs = {
            "card_number": {"required": False},
            "account_number": {"required": False},
            "iban": {"required": False},
            "full_name": {"required": False},
            "branch_id": {"required": False},
            "branch_name": {"required": False},
            "description": {"required": False},
        }

    def update(self, instance, validated_data):
        bank_info_id = validated_data.pop("bank_info", None)

        if bank_info_id is not None:
            try:
                bank_info = BankInfo.objects.get(id=bank_info_id)
                instance.bank_info = bank_info
            except BankInfo.DoesNotExist:
                raise serializers.ValidationError({"bank_info": "Bank info not found"})

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["bank_info"] = (
            instance.bank_info.name if instance.bank_info else None
        )
        return representation


class UserBankInfoListSerializer(serializers.ModelSerializer):
    bank_info = serializers.CharField(source="bank_info.name", read_only=True)
    bank_info_id = serializers.UUIDField(source="bank_info.id", read_only=True)

    class Meta:
        model = UserBankInfo
        fields = (
            "id",
            "bank_info_id",
            "bank_info",
            "card_number",
            "account_number",
            "iban",
            "full_name",
            "branch_id",
            "branch_name",
            "description",
        )


class UserBankInfoEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = UserBankInfoListSerializer()
    message = serializers.CharField()


class UserBankInfoListEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = UserBankInfoListSerializer(many=True)
    message = serializers.CharField()


class PublicUserBankInfoSerializer(serializers.ModelSerializer):
    """Explicit fields intentionally exposed by an unguessable share link."""

    bank_info = serializers.CharField(source="bank_info.name", read_only=True)

    class Meta:
        model = UserBankInfo
        fields = ("id", "bank_info", "card_number", "full_name")


class UserProfileSerializer(serializers.ModelSerializer):
    documents = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = (
            "id",
            "address",
            "national_code",
            "birth_date",
            "iban_number",
            "picture",
            "status",
            "phone_ownership_status",
            "review_note",
            "submitted_at",
            "documents",
        )
        read_only_fields = fields

    def get_documents(self, obj):
        return UserDocumentSerializer(obj.user.userdocument_set.all(), many=True).data

    def validate_national_code(self, value):
        if len(value) != 10 or not value.isascii() or not value.isdecimal():
            raise serializers.ValidationError("National code must contain 10 digits.")
        return value


class SelfProfileUpdateSerializer(serializers.ModelSerializer):
    """Writable profile fields supported by the reconciled persistence contract."""

    class Meta:
        model = UserProfile
        fields = ("address", "national_code", "birth_date", "iban_number", "picture")
        extra_kwargs = {"national_code": {"required": False}}

    def validate_national_code(self, value):
        if len(value) != 10 or not value.isascii() or not value.isdecimal():
            raise serializers.ValidationError("National code must contain 10 digits.")
        return value

    def validate_iban_number(self, value):
        if not value:
            return value
        normalized = value.replace(' ', '').upper()
        if len(normalized) != 26 or not normalized.startswith('IR') or not normalized[2:].isdigit():
            raise serializers.ValidationError('IBAN must contain IR followed by 24 digits.')
        if not _valid_iranian_iban_checksum(normalized):
            raise serializers.ValidationError('IBAN checksum is invalid.')
        return normalized


class UserDocumentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = UserDocument
        fields = ('id', 'document_type', 'file', 'download_url', 'status', 'review_note', 'created_at')
        read_only_fields = ('id', 'status', 'review_note', 'created_at')
        extra_kwargs = {'file': {'write_only': True}}

    def get_download_url(self, obj):
        request = self.context.get('request')
        path = f'/api/v1/user/profile/documents/{obj.id}/download/'
        return request.build_absolute_uri(path) if request else path

    def validate_file(self, value):
        if value.size > 8 * 1024 * 1024:
            raise serializers.ValidationError('حداکثر حجم هر مدرک ۸ مگابایت است.')
        extension = value.name.lower().rsplit('.', 1)[-1] if '.' in value.name else ''
        if extension not in {'jpg', 'jpeg', 'png', 'pdf'}:
            raise serializers.ValidationError('فرمت مجاز JPG، PNG یا PDF است.')
        return value


class SelfProfileDataSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    mobile_number = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    profile = UserProfileSerializer(allow_null=True)


class SelfProfileEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = SelfProfileDataSerializer()


class WebSocketTicketRequestSerializer(serializers.Serializer):
    scope = serializers.ChoiceField(choices=("chat", "support", "notifications"))
    room_id = serializers.UUIDField(required=False)
    ticket_id = serializers.UUIDField(required=False)

    def validate(self, attrs):
        scope = attrs["scope"]
        if scope == "chat" and "room_id" not in attrs:
            raise serializers.ValidationError({"room_id": "This field is required."})
        if scope == "support" and "ticket_id" not in attrs:
            raise serializers.ValidationError({"ticket_id": "This field is required."})
        if scope == "notifications" and (
            "room_id" in attrs or "ticket_id" in attrs
        ):
            raise serializers.ValidationError(
                "Notification tickets do not accept a resource identifier."
            )
        return attrs
