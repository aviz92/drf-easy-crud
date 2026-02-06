from django.db import models

RESERVED_PARAMS = {"page", "page_size", "ordering", "format"}

RELATED_LOOKUP = "__"

OPERATOR_MAPPING = {  # pylint: disable=R6101
    ">=": ("__gte", 2),
    "<=": ("__lte", 2),
    ">": ("__gt", 1),
    "<": ("__lt", 1),
}

DEFAULT_PAGE_SIZE = 20
DEFAULT_MAX_PAGE_SIZE = 100
PAGE_SIZE_QUERY_PARAM = "page_size"

INTEGER_FIELDS = (
    models.IntegerField,
    models.BigIntegerField,
    models.SmallIntegerField,
    models.PositiveIntegerField,
    models.PositiveSmallIntegerField,
)
