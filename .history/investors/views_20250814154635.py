import logging
from django.db import IntegrityError
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from investors.models import Investor, SavedStartup
from investors.serializers import InvestorSerializer, SavedStartupSerializer

logger = logging.getLogger(__name__)


class InvestorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing investors.
    Optimized to avoid N+1 queries when accessing related fields.
    """
    queryset = Investor.objects.select_related("user", "industry", "location")
    serializer_class = InvestorSerializer
    permission_classes = [IsAuthenticated]


class SavedStartupViewSet(viewsets.ModelViewSet):
    """
    Endpoints:
      - GET    /api/v1/investors/saved/
      - POST   /api/v1/investors/saved/
      - GET    /api/v1/investors/saved/{id}/
      - PATCH  /api/v1/investors/saved/{id}/
      - DELETE /api/v1/investors/saved/{id}/

    Permissions:
      - Auth required for all actions.
      - Only users with an Investor profile may list/create.
      - Queryset is scoped to the current investor.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SavedStartupSerializer

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, "investor"):
            # Non-investors get 403 on list
            raise PermissionDenied("Only investors can list saved startups.")
        return (
            SavedStartup.objects
            .select_related("startup", "investor")
            .filter(investor=user.investor)
            .order_by("-saved_at")
        )

    def perform_create(self, serializer):
        """
        - Non-investor on create → 400 (as tests expect).
        - Forbid saving own startup.
        - Inject investor from request.user.
        - Catch duplicate and return friendly error.
        """
        user = self.request.user
        if not hasattr(user, "investor"):
            raise ValidationError({"non_field_errors": ["Only investors can save startups."]})

        startup = serializer.validated_data.get("startup")
        if startup and startup.user_id == user.pk:
            # Expected by tests: HTTP 400 with own-startup message
            raise ValidationError({"startup": "You cannot save your own startup."})

        try:
            instance = serializer.save(investor=user.investor)
        except IntegrityError:
            # Unique (investor, startup) already exists
            raise ValidationError({"non_field_errors": ["Already saved."]})

        logger.info(
            "SavedStartup created",
            extra={
                "investor_id": user.investor.pk,
                "startup_id": startup.pk if startup else None,
                "saved_id": instance.pk,
                "by_user": user.pk,
            },
        )
        return instance

    def partial_update(self, request, *args, **kwargs):
        """
        Do not allow changing investor/startup via PATCH.
        Silently drop those fields and update only allowed ones.
        """
        instance = self.get_object()
        data = request.data.copy()
        data.pop("investor", None)
        data.pop("startup", None)

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        logger.info(
            "SavedStartup updated",
            extra={"saved_id": serializer.instance.pk, "by_user": request.user.pk},
        )
        return Response(serializer.data)

    def perform_destroy(self, instance):
        logger.info(
            "SavedStartup deleted",
            extra={"saved_id": instance.pk, "by_user": self.request.user.pk},
        )
        super().perform_destroy(instance)
