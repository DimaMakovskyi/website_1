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
    # Робимо investor тільки для читання (його підставимо з request.user)
    investor = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = SavedStartup
        fields = ['id', 'investor', 'startup', 'status', 'notes', 'saved_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'saved_at', 'created_at', 'updated_at']
        validators = [
            UniqueTogetherValidator(
                queryset=SavedStartup.objects.all(),
                fields=['investor', 'startup'],
                message="This startup is already saved."
            )
        ]

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'investor'):
            raise serializers.ValidationError("Only investors can save startups.")

        startup = attrs.get('startup')
        if startup and startup.user_id == request.user.id:
            raise serializers.ValidationError("You cannot save your own startup.")
        return attrs

    def create(self, validated_data):
        # Підставляємо інвестора з request
        investor = self.context['request'].user.investor
        return SavedStartup.objects.create(investor=investor, **validated_data)