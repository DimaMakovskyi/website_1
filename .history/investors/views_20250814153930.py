import logging
from django.db import IntegrityError
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
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
      - GET    /api/v1/investors/saved/       — list the current investor's saved startups
      - POST   /api/v1/investors/saved/       — save a startup (investor taken from request.user)
      - GET    /api/v1/investors/saved/{id}/  — detail
      - PATCH  /api/v1/investors/saved/{id}/  — update status/notes (cannot change investor/startup)
      - DELETE /api/v1/investors/saved/{id}/  — delete own saved startup

    Permissions:
      - Auth required for all actions
      - Only users with an Investor profile may list/create
      - Queryset is scoped to the current investor (others will see 404 on detail/patch/delete)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SavedStartupSerializer

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, "investor"):
            # Non-investors get 403 on list (tests accept 400/403; 403 is more correct)
            raise PermissionDenied("Only investors can list saved startups.")
        return (
            SavedStartup.objects
            .select_related("startup", "investor")
            .filter(investor=user.investor)
            .order_by("-saved_at")
        )

    def perform_create(self, serializer):
        """
        - Non-investor on create → 400 (as test `test_only_investor_can_save` expects)
        - Forbid saving own startup
        - Inject investor from request.user (do not require it in payload)
        - Catch duplicate and return friendly error
        """
        user = self.request.user
        if not hasattr(user, "investor"):
            raise ValidationError({"non_field_errors": ["Only investors can save startups."]})

        startup = serializer.validated_data.get("startup")
        if startup and startup.user_id == user.id:
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
                "investor_id": user.investor.id,
                "startup_id": startup.id if startup else None,
                "saved_id": instance.id,
            },
        )
        return instance

    def partial_update(self, request, *args, **kwargs):
        """
        Do not allow changing investor/startup via PATCH.
        Silently ignore those fields (keeps test simple with 200 response).
        """
        data = request.data.copy()
        data.pop("investor", None)
        data.pop("startup", None)
        serializer = self.get_serializer(self.get_object(), data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        logger.info(
            "SavedStartup updated",
            extra={"saved_id": serializer.instance.id, "by_user": request.user.id},
        )
        return self.get_response(serializer.data)

    # DRF does not have get_response by default — tiny helper:
    def get_response(self, data, status_code=None):
        from rest_framework.response import Response
        if status_code is None:
            return Response(data)
        return Response(data, status=status_code)

    def perform_destroy(self, instance):
        logger.info(
            "SavedStartup deleted",
            extra={"saved_id": instance.id, "by_user": self.request.user.id},
        )
        super().perform_destroy(instance)