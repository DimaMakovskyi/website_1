import logging
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from investors.models import Investor, SavedStartup
from investors.serializers import InvestorSerializer, SavedStartupSerializer

logger = logging.getLogger(__name__)


class InvestorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Investor investors.
    Optimized to avoid N+1 queries when accessing startup_details.
    """
    queryset = Investor.objects.select_related('user', 'industry', 'location')
    serializer_class = InvestorSerializer
    permission_classes = [IsAuthenticated]
    
class SavedStartupViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SavedStartupSerializer

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'investor'):
            raise PermissionDenied("Only investors can list saved startups.")
        return (SavedStartup.objects
                .select_related('startup', 'investor')
                .filter(investor=user.investor)
                .order_by('-saved_at'))

    def perform_create(self, serializer):
        serializer.save()
