import logging
from django.shortcuts import get_object_or_404
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework import status

from users.cookie_jwt import CookieJWTAuthentication
from users.permissions import IsAuthenticatedInvestor403  # single permission => 403 for any unauthorized access
from investments.models import Subscription
from investments.serializers import SubscriptionCreateSerializer
from projects.models import Project

logger = logging.getLogger(__name__)

class SubscriptionCreateView(CreateAPIView):
    """
    Create an investment subscription for a project.

    Security:
      - Only authenticated users with an Investor profile are allowed.
      - Any unauthorized access (unauthenticated or not an investor) results in 403 Forbidden,
        per the acceptance criteria.

    Notes:
      - Business validation & atomic updates are performed in the serializer.
      - We DO NOT manually mutate project's current_funding here to avoid double-counting.
    """
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionCreateSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticatedInvestor403]  # ← satisfies the spec: always 403 for unauthorized

    def _get_project(self):
        """Resolve the target project from the URL or return 404."""
        return get_object_or_404(Project, pk=self.kwargs.get("project_id"))

    def create(self, request, *args, **kwargs):
        """
        Orchestrates subscription creation:
          1) Validate payload using serializer with project in context.
          2) Save subscription (serializer handles locking, limits, and funding updates).
          3) Refresh project and return a concise status payload.
        """
        project = self._get_project()

        serializer = self.get_serializer(
            data=request.data,
            context={"request": request, "project": project},
        )
        serializer.is_valid(raise_exception=True)

        try:
            # Serializer.create() performs atomic logic and updates project's funding safely.
            self.perform_create(serializer)
        except Exception:
            logger.exception("Failed to create subscription for user %s", getattr(request.user, "id", None))
            return Response(
                {"detail": "Failed to create subscription. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # IMPORTANT: Do not manually add the amount here; serializer already updated funding.
        project.refresh_from_db(fields=["current_funding", "funding_goal"])
        remaining = project.funding_goal - project.current_funding
        project_status = "Fully funded" if remaining <= 0 else "Partially funded"

        logger.info(
            "Subscription created successfully for project %s by user %s",
            project.id,
            request.user.id,
        )

        return Response(
            {
                "message": "Subscription created successfully.",
                "subscription": SubscriptionCreateSerializer(serializer.instance, context={"request": request}).data,
                "remaining_funding": f"{remaining:.2f}",
                "project_status": project_status,
            },
            status=status.HTTP_201_CREATED,
        )

    def perform_create(self, serializer):
        """Persist the subscription bound to the authenticated investor and resolved project."""
        serializer.save(
            investor=self.request.user.investor,
            project=self._get_project(),
        )