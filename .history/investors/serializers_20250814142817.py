from rest_framework import serializers

from rest_framework.validators import UniqueTogetherValidator
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
    # якщо notes у БД NOT NULL — підстрахуємо дефолтом через create(); а тут дозволимо пусте значення
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    class Meta:
        model = SavedStartup
        fields = [
            'id',
            'investor',       
            'startup',        
            'startup_name',   
            'status', 'notes',
            'saved_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'investor', 'startup_name',
            'saved_at', 'created_at', 'updated_at'
        ]
        validators = [
            UniqueTogetherValidator(
                queryset=SavedStartup.objects.all(),
                fields=['investor', 'startup'],
                message="This startup is already saved."
            )
        ]

def validate(self, attrs):
    request = self.context.get('request')
    user = getattr(request, 'user', None)
    investor = getattr(user, 'investor', None)
    startup = attrs.get('startup')

    errors = {}

    if not investor:
        errors.setdefault('non_field_errors', []).append('Only investors can save startups.')

    if startup is None:
        errors['startup'] = 'This field is required.'
    else:
        if getattr(startup, 'user_id', None) == getattr(user, 'id', None):
            errors.setdefault('startup', 'You cannot save your own startup.')

    if errors:
        raise serializers.ValidationError(errors)
    return attrs

def create(self, validated_data):
    request = self.context.get('request')
    user = getattr(request, 'user', None)
    
    if not user or not hasattr(user, 'investor'):
        raise serializers.ValidationError(
            {'non_field_errors': ['Only authenticated investors can save startups.']}
        )
    investor = getattr(user, 'investor', None)

    if validated_data.get('notes') is None:
            validated_data['notes'] = ''
    
    try:
        return SavedStartup.objects.create(investor=investor, **validated_data)
    except IntegrityError:
        raise serializers.ValidationError({'non_field_errors': ['Already saved.']})