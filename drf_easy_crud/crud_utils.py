from collections.abc import Callable
from typing import Any

from custom_python_logger import get_logger
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, models
from django.db.models.deletion import ProtectedError
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer

from drf_easy_crud.const import DEFAULT_MAX_PAGE_SIZE, DEFAULT_PAGE_SIZE, PAGE_SIZE_QUERY_PARAM
from drf_easy_crud.filter_utils import FilterUtils

logger = get_logger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination class for list endpoints."""

    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = PAGE_SIZE_QUERY_PARAM
    max_page_size = DEFAULT_MAX_PAGE_SIZE


class CRUDUtils:
    """Enterprise-grade utility class providing comprehensive CRUD operations for Django REST Framework views."""

    @staticmethod
    def _check_object_permissions(
        request: Request,
        instance: models.Model,
        permission_classes: list[type[BasePermission]] | None,
    ) -> bool:
        """Run DRF object-level permission checks against a fetched instance.

        Calls ``has_object_permission(request, None, instance)`` on each class in
        *permission_classes*.  Returns True when all pass, False on the first failure.
        Note: ``view`` is passed as None — permission classes that access
        ``view.get_queryset()`` are not compatible with this helper.
        """

        if not permission_classes:
            return True
        return all(cls().has_object_permission(request, None, instance) for cls in permission_classes)

    @staticmethod
    def _get_instance_by_pk(
        queryset: models.QuerySet,
        pk: Any,
    ) -> models.Model | None:
        """Get a model instance by primary key within the provided queryset scope."""

        try:
            return queryset.get(pk=pk)
        except queryset.model.DoesNotExist:
            logger.warning("Instance not found: model=%s pk=%s", queryset.model.__name__, pk)
            return None

    @staticmethod
    def apply_pagination(
        queryset: models.QuerySet,
        request: Request,
        serializer_class: type[ModelSerializer],
        pagination_class: type[PageNumberPagination] | None = None,
    ) -> Response:
        """Apply pagination to a queryset and return a paginated response."""

        pagination_class = pagination_class or StandardResultsSetPagination

        paginator = pagination_class()
        if (page := paginator.paginate_queryset(queryset=queryset, request=request)) is not None:
            serializer = serializer_class(page, context={"request": request}, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = serializer_class(queryset, context={"request": request}, many=True)
        return Response(serializer.data)

    @staticmethod
    def _apply_filtering(
        queryset: models.QuerySet,
        request: Request,
    ) -> models.QuerySet:
        """Apply filtering to queryset using generic wildcard filtering."""

        if request.query_params:
            return FilterUtils.apply_wildcard_filtering(queryset=queryset, request=request)
        return queryset

    @staticmethod
    def _build_queryset(
        request: Request,
        queryset_hook: Callable[[Request], models.QuerySet],
    ) -> models.QuerySet:
        """Build the scoped queryset by invoking the caller-supplied hook.

        The hook receives the request so it can apply per-user, per-tenant, or any
        other runtime scoping.  Example::

            queryset_hook=lambda req: Article.objects.filter(owner=req.user)
        """

        return queryset_hook(request)

    @staticmethod
    def get_detail(
        request: Request,
        serializer_class: type[ModelSerializer],
        pk: Any,
        queryset_hook: Callable[[Request], models.QuerySet],
        permission_classes: list[type[BasePermission]] | None = None,
    ) -> Response:
        """Retrieve a single instance by pk, respecting the queryset scope and permission classes."""

        queryset = CRUDUtils._build_queryset(request=request, queryset_hook=queryset_hook)
        if not (instance := CRUDUtils._get_instance_by_pk(queryset=queryset, pk=pk)):
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not CRUDUtils._check_object_permissions(
            request=request, instance=instance, permission_classes=permission_classes
        ):
            logger.warning("Permission denied: model=%s pk=%s user=%s", queryset.model.__name__, pk, request.user)
            raise PermissionDenied()
        serializer = serializer_class(instance, context={"request": request})
        return Response(serializer.data)

    @staticmethod
    def get_list(
        request: Request,
        serializer_class: type[ModelSerializer],
        queryset_hook: Callable[[Request], models.QuerySet],
        ordering_field: str | None = "pk",
        pagination_class: type[PageNumberPagination] | None = None,
    ) -> Response:
        """Retrieve a paginated, filtered list of instances."""

        queryset = CRUDUtils._build_queryset(request=request, queryset_hook=queryset_hook)
        queryset = CRUDUtils._apply_filtering(queryset=queryset, request=request)
        queryset = queryset.order_by(ordering_field)
        return CRUDUtils.apply_pagination(
            queryset=queryset,
            request=request,
            serializer_class=serializer_class,
            pagination_class=pagination_class,
        )

    @staticmethod
    def get(  # pylint: disable=R0913
        request: Request,
        serializer_class: type[ModelSerializer],
        queryset_hook: Callable[[Request], models.QuerySet],
        ordering_field: str | None = "pk",
        pagination_class: type[PageNumberPagination] | None = None,
        permission_classes: list[type[BasePermission]] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Route to get_detail when pk is present, otherwise to get_list."""

        if (pk := kwargs.get("pk")) is not None:
            return CRUDUtils.get_detail(
                request=request,
                serializer_class=serializer_class,
                pk=pk,
                queryset_hook=queryset_hook,
                permission_classes=permission_classes,
            )
        return CRUDUtils.get_list(
            request=request,
            serializer_class=serializer_class,
            queryset_hook=queryset_hook,
            ordering_field=ordering_field,
            pagination_class=pagination_class,
        )

    @staticmethod
    def post(
        request: Request,
        serializer_class: type[ModelSerializer],
        **kwargs: Any,
    ) -> Response:
        """Create a new instance."""

        serializer = serializer_class(data=request.data, context={"request": request})
        if not serializer.is_valid():
            model_name = serializer_class.Meta.model.__name__
            logger.warning("Validation failed for %s: %s", model_name, serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            serializer.save(**kwargs)
            model_name = serializer_class.Meta.model.__name__
            instance_id = serializer.data.get("id")
            logger.info("Created %s with id=%s", model_name, instance_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except (IntegrityError, DjangoValidationError) as e:
            logger.error("Database error creating %s: %s", serializer_class.Meta.model.__name__, str(e))
            raise DRFValidationError({"detail": str(e)}) from e

    @staticmethod
    def _update_instance(  # pylint: disable=R0913
        request: Request,
        serializer_class: type[ModelSerializer],
        pk: Any,
        partial: bool,
        queryset_hook: Callable[[Request], models.QuerySet],
        permission_classes: list[type[BasePermission]] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Internal method to update an instance."""

        queryset = CRUDUtils._build_queryset(request=request, queryset_hook=queryset_hook)
        if not (instance := CRUDUtils._get_instance_by_pk(queryset=queryset, pk=pk)):
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not CRUDUtils._check_object_permissions(
            request=request, instance=instance, permission_classes=permission_classes
        ):
            logger.warning("Permission denied: model=%s pk=%s user=%s", queryset.model.__name__, pk, request.user)
            raise PermissionDenied()

        serializer = serializer_class(instance, data=request.data, context={"request": request}, partial=partial)
        if not serializer.is_valid():
            logger.warning("Validation failed for %s pk=%s: %s", queryset.model.__name__, pk, serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            serializer.save(**kwargs)
            update_type = "Partially updated" if partial else "Updated"
            logger.info("%s %s with pk=%s", update_type, queryset.model.__name__, pk)
            return Response(serializer.data)
        except (IntegrityError, DjangoValidationError) as e:
            logger.error("Database error updating %s pk=%s: %s", queryset.model.__name__, pk, str(e))
            raise DRFValidationError({"detail": str(e)}) from e

    @staticmethod
    def put(
        request: Request,
        serializer_class: type[ModelSerializer],
        queryset_hook: Callable[[Request], models.QuerySet],
        permission_classes: list[type[BasePermission]] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Update an existing instance with full replacement (PUT semantics)."""

        if (pk := kwargs.pop("pk", None)) is None:
            logger.warning("PUT request missing pk for %s", queryset_hook(request).model.__name__)
            return Response(status=status.HTTP_404_NOT_FOUND)
        return CRUDUtils._update_instance(
            request=request,
            serializer_class=serializer_class,
            pk=pk,
            partial=False,
            queryset_hook=queryset_hook,
            permission_classes=permission_classes,
            **kwargs,
        )

    @staticmethod
    def patch(
        request: Request,
        serializer_class: type[ModelSerializer],
        queryset_hook: Callable[[Request], models.QuerySet],
        permission_classes: list[type[BasePermission]] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Partially update an existing instance (PATCH semantics)."""

        if (pk := kwargs.pop("pk", None)) is None:
            logger.warning("PATCH request missing pk for %s", queryset_hook(request).model.__name__)
            return Response(status=status.HTTP_404_NOT_FOUND)
        return CRUDUtils._update_instance(
            request=request,
            serializer_class=serializer_class,
            pk=pk,
            partial=True,
            queryset_hook=queryset_hook,
            permission_classes=permission_classes,
            **kwargs,
        )

    @staticmethod
    def delete(
        request: Request,
        queryset_hook: Callable[[Request], models.QuerySet],
        permission_classes: list[type[BasePermission]] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Delete an existing instance."""

        queryset = CRUDUtils._build_queryset(request=request, queryset_hook=queryset_hook)

        if (pk := kwargs.get("pk")) is None:
            logger.warning("DELETE request missing pk for %s", queryset.model.__name__)
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not (instance := CRUDUtils._get_instance_by_pk(queryset=queryset, pk=pk)):
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not CRUDUtils._check_object_permissions(
            request=request, instance=instance, permission_classes=permission_classes
        ):
            logger.warning("Permission denied: model=%s pk=%s user=%s", queryset.model.__name__, pk, request.user)
            raise PermissionDenied()

        try:
            instance.delete()
            logger.info("Deleted %s with pk=%s", queryset.model.__name__, pk)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except (IntegrityError, ProtectedError) as e:
            logger.error("Error deleting %s pk=%s: %s", queryset.model.__name__, pk, str(e))
            raise DRFValidationError({"detail": str(e)}) from e
