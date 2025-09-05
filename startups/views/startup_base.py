import logging
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError as DRFValidationError

logger = logging.getLogger(__name__)


class BaseValidatedModelViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet that runs model full_clean() validation
    and logs creation and update events.
    """

    def _validate_and_log(self, serializer, action):
        """ Validates the model and saves the instance. """
        Model = serializer.Meta.model
        instance = serializer.instance or Model()
        for attr, value in serializer.validated_data.items():
            setattr(instance, attr, value)
        if action == 'create' and hasattr(instance, 'user') and getattr(instance, 'user', None) is None:
            instance.user = self.request.user

        try:
            instance.full_clean()
        except DjangoValidationError as e:
            logger.warning(f"Validation error during {action}: {e}")
            raise DRFValidationError(e.message_dict)

        if action == 'create':
            instance = serializer.save(user=self.request.user)
        elif action == 'update':
            instance = serializer.save()

        logger.info(f"{instance.__class__.__name__} {action}d: {instance}")
        return instance

    def perform_create(self, serializer):
        self._validate_and_log(serializer, 'create')

    def perform_update(self, serializer):
        ''' Update first so instance exists for validation '''
        return self._validate_and_log(serializer, "update")
