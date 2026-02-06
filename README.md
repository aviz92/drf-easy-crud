# DRF Easy CRUD
Enterprise-grade utility library for simplifying CRUD operations in Django REST Framework. Provides powerful filtering, pagination, and standardized CRUD methods to accelerate API development.

---

## Installation
```bash
uv add drf-easy-crud
```

---

## Features
- **🔧 Simplified CRUD Operations**: Static utility methods for GET, POST, PUT, PATCH, and DELETE operations
- **🔍 Advanced Filtering**: Wildcard pattern matching for text fields, comparison operators for numeric fields
- **📄 Built-in Pagination**: Standard pagination with configurable page sizes
- **🔗 ForeignKey Support**: Filter across related models using Django's double-underscore lookup syntax
- **🛡️ Enterprise-Grade Error Handling**: Comprehensive error handling with detailed logging
- **📊 Type-Safe**: Full type hints for better IDE support and code reliability
- **⚡ Performance Optimized**: Efficient queryset handling with optional hooks for customization

---
## Quick Start
### Basic Usage
```python
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from drf_easy_crud import CRUDUtils
from myapp.models import MyModel
from myapp.serializers import MyModelSerializer


class MyModelViewSet(viewsets.ViewSet):
    """Example ViewSet using CRUDUtils."""

    def get(self, request: Request) -> Response:
        """List all instances with filtering and pagination."""
        return CRUDUtils.get(
            request=request,
            model_class=MyModel,
            serializer_class=MyModelSerializer,
        )

    def post(self, request: Request) -> Response:
        """Create a new instance."""
        return CRUDUtils.post(
            request=request,
            serializer_class=MyModelSerializer,
        )

    def put(self, request: Request, pk: int) -> Response:
        """Full update of an instance."""
        return CRUDUtils.put(
            request=request,
            model_class=MyModel,
            serializer_class=MyModelSerializer,
            pk=pk,
        )

    def patch(self, request: Request, pk: int) -> Response:
        """Partial update of an instance."""
        return CRUDUtils.patch(
            request=request,
            model_class=MyModel,
            serializer_class=MyModelSerializer,
            pk=pk,
        )

    def delete(self, request: Request, pk: int) -> Response:
        """Delete an instance."""
        return CRUDUtils.delete(
            model_class=MyModel,
            pk=pk,
        )
```

## Advanced Features
### Custom Queryset Hooks
Filter the base queryset before applying request filters:
```python
def list(self, request: Request) -> Response:
    """List only active instances."""
    return CRUDUtils.get(
        request=request,
        model_class=MyModel,
        serializer_class=MyModelSerializer,
        queryset_hook=lambda: MyModel.objects.filter(is_active=True),
    )
```

### Custom Pagination
Use your own pagination class:
```python
from drf_easy_crud import CRUDUtils, StandardResultsSetPagination
from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    page_size = 50
    max_page_size = 200


def list(self, request: Request) -> Response:
    return CRUDUtils.get(
        request=request,
        model_class=MyModel,
        serializer_class=MyModelSerializer,
        pagination_class=CustomPagination,
    )
```

### Custom Ordering
Specify default ordering for list endpoints:
```python
def list(self, request: Request) -> Response:
    return CRUDUtils.get(
        request=request,
        model_class=MyModel,
        serializer_class=MyModelSerializer,
        ordering_field="-created_at",  # Newest first
    )
```

---

## Filtering
The library provides powerful filtering capabilities through `FilterUtils`:

### Text Field Wildcard Patterns
| Pattern | Description | Example | Matches |
|---------|-------------|---------|---------|
| `field=value*` | Starts with | `?name=test*` | "test", "test123", "testing" |
| `field=*value` | Ends with | `?name=*test` | "mytest", "123test" |
| `field=*value*` | Contains | `?name=*test*` | "test", "mytest", "testing" |
| `field=va*ue` | Middle wildcard | `?name=t*t` | "test", "tart", "t123t" |
| `field=value` | Exact match | `?name=test` | "test" (case-insensitive) |

### Number Field Comparison Operators
| Pattern | Description | Example | Matches |
|---------|-------------|---------|---------|
| `field=value` | Exact match | `?age=25` | Exactly 25 |
| `field=>=value` | Greater than or equal | `?age=>=25` | 25, 26, 27, ... |
| `field=<=value` | Less than or equal | `?age=<=100` | ..., 98, 99, 100 |
| `field=>value` | Greater than | `?age=>25` | 26, 27, 28, ... |
| `field=<value` | Less than | `?age=<25` | ..., 23, 24 |

### ForeignKey Lookups
Filter by related model fields using double underscores:
```python
# Filter by related model's text field
GET /api/products/?category__name=electronics*

# Filter by related model's number field
GET /api/products/?category__priority=>=5

# Nested ForeignKey lookup
GET /api/orders/?customer__company__name=acme*
```

### Filtering Examples
```bash
# Search by name starting with "test"
GET /api/mymodel/?name=test*

# Search by name containing "important"
GET /api/mymodel/?name=*important*

# Filter by age >= 18
GET /api/mymodel/?age=>=18

# Filter by age between 18 and 30
GET /api/mymodel/?age=18-30

# Multiple filters combined
GET /api/mymodel/?name=test*&age=>=18&status=active

# ForeignKey lookup
GET /api/mymodel/?category__name=electronics*
```

---

## Pagination
Results are paginated by default (20 items per page, max 100).
### Pagination Parameters

- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20, max: 100)

### Paginated Response Format
```json
{
  "count": 150,
  "next": "http://example.com/api/mymodel/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Item 1",
      ...
    },
    ...
  ]
}
```

---

## 🤝 Contributing
If you have a helpful tool, pattern, or improvement to suggest:
Fork the repo <br>
Create a new branch <br>
Submit a pull request <br>
I welcome additions that promote clean, productive, and maintainable development. <br>

---

## 🙏 Thanks
Thanks for exploring this repository! <br>
Happy coding! <br>
