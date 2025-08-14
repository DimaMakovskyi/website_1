import logging
from django.db import IntegrityError

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, BasePermission
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


class IsSavedStartupOwner(BasePermission):
    """Allow update/delete only for the owner of the SavedStartup."""
    def has_object_permission(self, request, view, obj):
        if not hasattr(request.user, "investor"):
            logger.warning(
                "SavedStartup object access denied: user has no investor",
                extra={"by_user": getattr(request.user, "pk", None), "saved_id": getattr(obj, "pk", None)},
            )
            return False
        allowed = (obj.investor_id == request.user.investor.pk)
        if not allowed:
            logger.warning(
                "SavedStartup object access denied: not owner",
                extra={"by_user": request.user.pk, "saved_id": getattr(obj, "pk", None), "owner_investor_id": obj.investor_id},
            )
        return allowed


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
    permission_classes = [IsAuthenticated, IsSavedStartupOwner]
    serializer_class = SavedStartupSerializer

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, "investor"):
            logger.warning(
                "SavedStartup list denied: non-investor",
                extra={"by_user": getattr(user, "pk", None)},
            )
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
            logger.warning(
                "SavedStartup create denied: non-investor",
                extra={"by_user": getattr(user, "pk", None)},
            )
            raise ValidationError({"non_field_errors": ["Only investors can save startups."]})

        startup = serializer.validated_data.get("startup")
        if startup is None:
            logger.warning(
                "SavedStartup create validation error: missing startup",
                extra={"by_user": user.pk},
            )
            raise ValidationError({"startup": "This field is required."})

        status_field = SavedStartup._meta.get_field("status")
        valid_status = {choice[0] for choice in status_field.choices}
        status_val = serializer.validated_data.get("status")
        if status_val and status_val not in valid_status:
            logger.warning(
                "SavedStartup create validation error: invalid status",
                extra={"by_user": user.pk, "status": status_val},
            )
            raise ValidationError({"status": f"Invalid status '{status_val}'."})

        if startup.user_id == user.pk:
            logger.warning(
                "SavedStartup create denied: own startup",
                extra={"by_user": user.pk, "startup_id": startup.pk},
            )
            raise ValidationError({"startup": "You cannot save your own startup."})

        try:
            instance = serializer.save(investor=user.investor)
        except IntegrityError:
            logger.warning(
                "SavedStartup create duplicate",
                extra={"by_user": user.pk, "investor_id": user.investor.pk, "startup_id": startup.pk},
            )
            raise ValidationError({"non_field_errors": ["Already saved."]})

        logger.info(
            "SavedStartup created",
            extra={
                "investor_id": user.investor.pk,
                "startup_id": startup.pk,
                "saved_id": instance.pk,
                "by_user": user.pk,
            },
        )

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
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            logger.warning(
                "SavedStartup update validation error",
                extra={"saved_id": instance.pk, "by_user": request.user.pk, "errors": getattr(e, "detail", None)},
            )
            raise
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