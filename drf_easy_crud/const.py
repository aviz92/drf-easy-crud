from django.db import models

LOGGER_NAME = "pytest_depends_on"

RESERVED_PARAMS = {"page", "page_size", "ordering", "format"}

RELATED_LOOKUP = "__"

OPERATOR_MAPPING = {
    ">=": "__gte",
    "<=": "__lte",
    ">": "__gt",
    "<": "__lt",
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

NUMBER_FIELDS = (
    *INTEGER_FIELDS,
    models.FloatField,
    models.DecimalField,
)
