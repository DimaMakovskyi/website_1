from rest_framework import serializers

from django.core.exceptions import ValidationError as DjangoValidationError
from investors.models import Investor, SavedStartup
from startups.models import Startup
from django.db import IntegrityError


class InvestorSerializer(serializers.ModelSerializer):
    """
    Serializer for the Investor model.
    Includes all fields defined in the abstract Company base class and Investor-specific fields.
    """
    class Meta:
        model = Investor
        fields = [
            'id',
            'user',
            'industry',
            'company_name',
            'location',
            'logo',
            'description',
            'website',
            'email',
            'founded_year',
            'team_size',
            'stage',
            'fund_size',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

    def validate_company_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Company name must not be empty.")
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)



class SavedStartupSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and retrieving SavedStartup records.

    Ensures:
    - Only authenticated investors can save startups.
    - Prevents saving own startup.
    - Avoids duplicates via validator and IntegrityError handling.
    """
    investor = serializers.PrimaryKeyRelatedField(read_only=True)
    startup = serializers.PrimaryKeyRelatedField(queryset=Startup.objects.all(), write_only=True)
    startup_name = serializers.CharField(source='startup.company_name', read_only=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = SavedStartup
        fields = [
            'id',
            'investor',
            'startup',
            'startup_name',
            'status', 'notes',
            'saved_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'investor', 'startup_name', 'saved_at', 'created_at', 'updated_at']
        extra_kwargs = {
            'investor': {'read_only': True, 'required': False},
            'startup': {'write_only': True},
        }

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        investor = getattr(user, 'investor', None)

        is_create = self.instance is None
        has_startup_in_payload = 'startup' in attrs
        startup = attrs.get('startup')

        errors = {}
        if not investor:
            errors.setdefault('non_field_errors', []).append('Only investors can save startups.')

        if is_create and startup is None:
            errors['startup'] = 'This field is required.'
        if has_startup_in_payload and startup is not None:
            if getattr(startup, 'user_id', None) == getattr(user, 'id', None):
                errors.setdefault('startup', 'You cannot save your own startup.')

        if errors:
            raise serializers.ValidationError(errors)
        return attrs

def create(self, validated_data):
    request = self.context.get('request')
    user = getattr(request, 'user', None)
    if not user or not hasattr(user, 'investor'):
        raise serializers.ValidationError({'non_field_errors': ['Only authenticated investors can save startups.']})

    # Створюємо об’єкт, проганяємо модельні валідації, потім зберігаємо
    obj = SavedStartup(investor=user.investor, **validated_data)
    try:
        obj.full_clean()  # викличе SavedStartup.clean() → заборона свого стартапу
        obj.save()
        return obj
    except DjangoValidationError as e:
        # Перетворюємо помилки моделі у 400 DRF
        # e.message_dict (dict полів) або e.messages (список рядків)
        payload = e.message_dict if hasattr(e, 'message_dict') and e.message_dict else {'non_field_errors': e.messages}
        raise serializers.ValidationError(payload)
    except IntegrityError:
        # Дублікат (унікальний констрейнт investor+startup)
        raise serializers.ValidationError({'non_field_errors': ['Already saved.']})