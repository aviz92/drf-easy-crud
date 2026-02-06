import re
from typing import Any

from custom_python_logger import get_logger
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from drf_easy_crud.const import INTEGER_FIELDS, OPERATOR_MAPPING, RELATED_LOOKUP, RESERVED_PARAMS

logger = get_logger(__name__)


class FilterUtils:
    """Utility class for applying filtering and pagination to Django REST Framework views."""

    @staticmethod
    def _wildcard_to_regex(pattern: str) -> str:
        """Convert wildcard pattern to regex pattern."""

        return re.escape(pattern).replace(r"\*", ".*")

    @staticmethod
    def _has_middle_wildcard(value: str) -> bool:
        """Check if wildcard appears in the middle of the string."""

        return len(value) > 2 and "*" in value[1:-1]

    @staticmethod
    def _apply_text_wildcard_filter(
        queryset: models.QuerySet,
        param_name: str,
        param_value: str,
    ) -> models.QuerySet:
        """Apply wildcard filtering to text fields."""

        if "*" not in param_value:
            return queryset.filter(**{f"{param_name}__iexact": param_value})
        if FilterUtils._has_middle_wildcard(param_value) or param_value.count("*") > 1:
            return queryset.filter(**{f"{param_name}__iregex": FilterUtils._wildcard_to_regex(param_value)})
        if param_value.startswith("*") and param_value.endswith("*"):
            if clean_value := param_value.strip("*"):
                return queryset.filter(**{f"{param_name}__icontains": clean_value})
        if param_value.startswith("*"):
            if clean_value := param_value.lstrip("*"):
                return queryset.filter(**{f"{param_name}__iendswith": clean_value})
        if param_value.endswith("*"):
            if clean_value := param_value.rstrip("*"):
                return queryset.filter(**{f"{param_name}__istartswith": clean_value})
        return queryset

    @staticmethod
    def _convert_number_value(value: str, field: models.Field) -> int | float:
        """Convert string to int or float based on field type."""

        return int(value) if isinstance(field, INTEGER_FIELDS) else float(value)

    @staticmethod
    def _apply_number_filter(
        queryset: models.QuerySet,
        param_name: str,
        param_value: str,
        field: models.Field,
    ) -> models.QuerySet:
        """Apply filtering to number fields with support for comparison operators."""

        param_value = param_value.strip()
        lookup_suffix = ""
        value_str = param_value
        for operator, suffix in OPERATOR_MAPPING.items():
            if param_value.startswith(operator):
                lookup_suffix = suffix
                value_str = param_value[len(operator) :].strip()
                break

        try:
            value = FilterUtils._convert_number_value(value_str, field)
            filter_key = f"{param_name}{lookup_suffix}" if lookup_suffix else param_name
            return queryset.filter(**{filter_key: value})
        except (ValueError, TypeError):
            return queryset.none()

    @staticmethod
    def _apply_wildcard_to_field(
        queryset: models.QuerySet,
        param_name: str,
        param_value: str,
        field: models.Field,
        django_models: Any,
    ) -> models.QuerySet:
        """Apply wildcard filtering to a specific field.

        Supports:
        - Text fields: wildcard patterns (*test*, test*, *test, t*t)
        - Number fields: comparison operators (>=10, <=100, >5, <20) and ranges (10-20)
        - Other fields: exact match

        Args:
            queryset: The queryset to filter.
            param_name: The parameter name (field or lookup path).
            param_value: The parameter value (may contain wildcards or operators).
            field: The Django field object.
            django_models: Django models module.

        Returns:
            Filtered queryset.
        """
        is_number_field = isinstance(
            field,
            django_models.IntegerField
            | django_models.BigIntegerField
            | django_models.SmallIntegerField
            | django_models.PositiveIntegerField
            | django_models.PositiveSmallIntegerField
            | django_models.FloatField
            | django_models.DecimalField,
        )

        if is_number_field:
            return FilterUtils._apply_number_filter(queryset, param_name, param_value, field)

        if isinstance(field, django_models.CharField | django_models.TextField):  # is_text_field
            return FilterUtils._apply_text_wildcard_filter(queryset, param_name, param_value)

        return queryset.filter(**{param_name: param_value})  # For other field types (bool, date, etc.), use exact match

    @staticmethod
    def _get_lookup_target_field(model: type[models.Model], lookup_path: str) -> models.Field | None:
        """Get the target field from a Django lookup path."""

        parts = lookup_path.split(RELATED_LOOKUP)
        current_model = model

        for part in parts[:-1]:
            try:
                field = current_model._meta.get_field(part)  # pylint: disable=W0212
                if isinstance(field, (models.ForeignKey | models.OneToOneField)):
                    current_model = field.related_model
                elif isinstance(field, models.ManyToManyField):
                    current_model = field.related_model
                else:
                    return None
            except FieldDoesNotExist:
                return None

        # Get the final field
        try:
            return current_model._meta.get_field(parts[-1])  # pylint: disable=W0212
        except FieldDoesNotExist:
            return None

    @staticmethod
    def apply_wildcard_filtering(
        queryset: models.QuerySet,
        request: Request,
    ) -> models.QuerySet:
        """Apply generic wildcard filtering directly to queryset."""

        query_params = request.query_params.copy()
        model = queryset.model
        model_fields = {f.name for f in model._meta.get_fields()}  # pylint: disable=W0212

        filtered_queryset = queryset
        for param_name, param_value in query_params.items():
            if param_name in RESERVED_PARAMS or not param_value:  # Skip reserved params and empty values
                continue

            if RELATED_LOOKUP in param_name:  # Check if this is a ForeignKey lookup (contains "__")
                if not (target_field := FilterUtils._get_lookup_target_field(model=model, lookup_path=param_name)):
                    raise ValidationError({param_name: f"Field '{param_name}' does not exist"})
            else:  # Direct field lookup
                if param_name not in model_fields:
                    raise ValidationError({param_name: f"Field '{param_name}' does not exist on {model.__name__}"})

                # Get field type to determine appropriate lookup
                try:
                    target_field = model._meta.get_field(param_name)  # pylint: disable=W0212
                except FieldDoesNotExist as err:
                    raise ValidationError(
                        {param_name: f"Field '{param_name}' does not exist on {model.__name__}"}
                    ) from err

            filtered_queryset = FilterUtils._apply_wildcard_to_field(
                queryset=filtered_queryset,
                param_name=param_name,
                param_value=param_value,
                field=target_field,
                django_models=models,
            )
        return filtered_queryset
