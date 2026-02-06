"""Enterprise-grade CRUD utility class for Django REST Framework.

Provides comprehensive CRUD operations with:
- Pagination support
- Generic wildcard filtering (no FilterSet needed)
- Ordering and sorting
- Queryset customization hooks
- Performance optimizations (select_related/prefetch_related)
- Bulk operations
- Comprehensive error handling
"""

from collections.abc import Callable
from typing import Any

from custom_python_logger import get_logger
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, models
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
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
    def _get_instance_by_pk(
        model_class: type[models.Model],
        pk: Any,
        select_related: list[str] | None = None,
        prefetch_related: list[str] | None = None,
    ) -> models.Model | None:
        """Get a model instance by primary key with optional performance optimizations."""

        try:
            queryset = model_class.objects.all()
            if select_related:
                queryset = queryset.select_related(*select_related)
            if prefetch_related:
                queryset = queryset.prefetch_related(*prefetch_related)
            return queryset.get(pk=pk)
        except model_class.DoesNotExist:
            logger.warning(f"{model_class.__name__} with pk={pk} not found")
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

        # No pagination, return all results
        serializer = serializer_class(queryset, context={"request": request}, many=True)
        return Response(serializer.data)

    @staticmethod
    def _apply_filtering(
        queryset: models.QuerySet,
        request: Request,
    ) -> models.QuerySet:
        """Apply filtering to queryset using django-filter or generic wildcard filtering."""

        if request.query_params:
            return FilterUtils.apply_wildcard_filtering(queryset=queryset, request=request)
        return queryset

    @staticmethod
    def _build_queryset(
        model_class: type[models.Model],
        queryset_hook: Callable | None = None,
    ) -> models.QuerySet:  # constant filter: queryset_hook=lambda: FirstApp.objects.filter(is_active=True)
        """Build the initial queryset for list retrieval, allowing for optional customization via a hook."""

        return queryset_hook() if queryset_hook else model_class.objects.all()

    @staticmethod
    def get(
        request: Request,
        model_class: type[models.Model],
        serializer_class: type[ModelSerializer],
        queryset_hook: Callable | None = None,
        ordering_field: str | None = "pk",
        pagination_class: type[PageNumberPagination] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Retrieve a single instance or paginated list of instances."""

        if pk := kwargs.get("pk"):
            if not (instance := CRUDUtils._get_instance_by_pk(model_class=model_class, pk=pk)):
                return Response(status=status.HTTP_404_NOT_FOUND)
            serializer = serializer_class(instance, context={"request": request})
            return Response(serializer.data)
        queryset = CRUDUtils._build_queryset(model_class=model_class, queryset_hook=queryset_hook)
        queryset = CRUDUtils._apply_filtering(queryset=queryset, request=request)
        queryset = queryset.order_by(ordering_field)
        return CRUDUtils.apply_pagination(
            queryset=queryset,
            request=request,
            serializer_class=serializer_class,
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
        if serializer.is_valid():
            try:
                serializer.save(**kwargs)
                model_name = serializer_class.Meta.model.__name__
                instance_id = serializer.data.get("id")
                logger.info(f"Created {model_name} with id={instance_id}")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except (IntegrityError, DjangoValidationError) as e:
                logger.error(f"Database error creating {serializer_class.Meta.model.__name__}: {str(e)}")
                return Response(
                    {"error": "Database constraint violation", "detail": str(e)}, status=status.HTTP_400_BAD_REQUEST
                )
        model_name = serializer_class.Meta.model.__name__
        logger.warning(f"Validation failed for {model_name}: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def _update_instance(
        request: Request,
        model_class: type[models.Model],
        serializer_class: type[ModelSerializer],
        pk: Any,
        partial: bool,
        select_related: list[str] | None = None,
        prefetch_related: list[str] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Internal method to update an instance."""

        instance = CRUDUtils._get_instance_by_pk(
            model_class=model_class,
            pk=pk,
            select_related=select_related,
            prefetch_related=prefetch_related,
        )
        if not instance:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = serializer_class(instance, data=request.data, context={"request": request}, partial=partial)
        if serializer.is_valid():
            try:
                serializer.save(**kwargs)
                update_type = "Partially updated" if partial else "Updated"
                logger.info(f"{update_type} {model_class.__name__} with pk={pk}")
                return Response(serializer.data)
            except (IntegrityError, DjangoValidationError) as e:
                logger.error(f"Database error updating {model_class.__name__} pk={pk}: {str(e)}")
                return Response(
                    {"error": "Database constraint violation", "detail": str(e)}, status=status.HTTP_400_BAD_REQUEST
                )
        logger.warning(f"Validation failed for {model_class.__name__} pk={pk}: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def put(
        request: Request,
        model_class: type[models.Model],
        serializer_class: type[ModelSerializer],
        select_related: list[str] | None = None,
        prefetch_related: list[str] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Update an existing instance with full replacement (PUT semantics)."""

        if not (pk := kwargs.pop("pk", None)):
            logger.warning(f"PUT request missing pk for {model_class.__name__}")
            return Response(status=status.HTTP_404_NOT_FOUND)
        return CRUDUtils._update_instance(
            request=request,
            model_class=model_class,
            serializer_class=serializer_class,
            pk=pk,
            partial=False,
            select_related=select_related,
            prefetch_related=prefetch_related,
            **kwargs,
        )

    @staticmethod
    def patch(
        request: Request,
        model_class: type[models.Model],
        serializer_class: type[ModelSerializer],
        select_related: list[str] | None = None,
        prefetch_related: list[str] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Partially update an existing instance (PATCH semantics)."""

        if not (pk := kwargs.pop("pk", None)):
            logger.warning(f"PATCH request missing pk for {model_class.__name__}")
            return Response(status=status.HTTP_404_NOT_FOUND)
        return CRUDUtils._update_instance(
            request=request,
            model_class=model_class,
            serializer_class=serializer_class,
            pk=pk,
            partial=True,
            select_related=select_related,
            prefetch_related=prefetch_related,
            **kwargs,
        )

    @staticmethod
    def delete(
        model_class: type[models.Model],
        **kwargs: Any,
    ) -> Response:
        """Delete an existing instance."""

        if not (pk := kwargs.get("pk")):
            logger.warning(f"DELETE request missing pk for {model_class.__name__}")
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not (instance := CRUDUtils._get_instance_by_pk(model_class, pk)):
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            instance.delete()
            logger.info(f"Deleted {model_class.__name__} with pk={pk}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Error deleting {model_class.__name__} pk={pk}: {str(e)}")
            return Response(
                {"error": "Failed to delete instance", "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
