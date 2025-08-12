from rest_framework import serializers

from investors.models import Investor
from startups.models import Startup
from .models import SavedStartup
from startups.serializers import StartupSerializer


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
    startup = StartupSerializer(read_only=True)
    startup_id = serializers.PrimaryKeyRelatedField(
        queryset=Startup.objects.all(), source='startup', write_only=True
    )

    class Meta:
        model = SavedStartup
        fields = ['id', 'startup', 'startup_id', 'status', 'notes', 'saved_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'saved_at', 'created_at', 'updated_at']

    def validate(self, attrs):
        request = self.context.get('request')
        investor = getattr(request.user, 'investor', None) if request else None
        startup = attrs.get('startup')

        if not investor:
            raise serializers.ValidationError({'detail': 'Only investors can save startups.'})

        if hasattr(request.user, 'startup') and request.user.startup_id == getattr(startup, 'id', None):
            raise serializers.ValidationError({'startup_id': 'You cannot save your own startup.'})

        if SavedStartup.objects.filter(investor=investor, startup=startup).exists():
            raise serializers.ValidationError({'non_field_errors': ['Already saved.']})

        return attrs

    def create(self, validated_data):
        investor = self.context['request'].user.investor
        return SavedStartup.objects.create(investor=investor, **validated_data)