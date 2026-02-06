# API User Guide

Complete guide for using the REST API endpoints. This guide shows you how to interact with the API, make requests, and understand responses.

## Table of Contents

- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
- [Search & Filtering](#search--filtering)
- [Pagination](#pagination)
- [Sorting](#sorting)
- [Request Examples](#request-examples)
- [Response Formats](#response-formats)
- [Error Handling](#error-handling)
- [Common Use Cases](#common-use-cases)

## Quick Start

**Base URL:** `http://127.0.0.1:8000`

**Authentication:** Token-based (see [Authentication](#authentication))

**Example Request:**
```bash
curl -H "Authorization: Token YOUR_TOKEN" \
     http://127.0.0.1:8000/first_app/
```

## Authentication

All API endpoints require authentication using a token.

### Getting Your Token

1. Log in to the admin panel or use the token endpoint
2. Your token will be provided (contact your administrator)

### Using Your Token

Include the token in the `Authorization` header:

```bash
Authorization: Token YOUR_TOKEN_HERE
```

**cURL Example:**
```bash
curl -H "Authorization: Token abc123..." \
     http://127.0.0.1:8000/first_app/
```

**Python Example:**
```python
import requests

headers = {
    'Authorization': 'Token YOUR_TOKEN_HERE'
}
response = requests.get('http://127.0.0.1:8000/first_app/', headers=headers)
```

**JavaScript Example:**
```javascript
fetch('http://127.0.0.1:8000/first_app/', {
    headers: {
        'Authorization': 'Token YOUR_TOKEN_HERE'
    }
})
```

## API Endpoints

### First App Endpoints

**List All Items:**
```
GET /first_app/
```

**Get Single Item:**
```
GET /first_app/{id}/
```

**Create New Item:**
```
POST /first_app/
```

**Update Item (Full):**
```
PUT /first_app/{id}/
```

**Update Item (Partial):**
```
PATCH /first_app/{id}/
```

**Delete Item:**
```
DELETE /first_app/{id}/
```

### Second App Endpoints

**List All Items:**
```
GET /second_app/
```

**Get Single Item:**
```
GET /second_app/{id}/
```

**Create New Item:**
```
POST /second_app/
```

**Update Item (Full):**
```
PUT /second_app/{id}/
```

**Update Item (Partial):**
```
PATCH /second_app/{id}/
```

**Delete Item:**
```
DELETE /second_app/{id}/
```

## Search & Filtering

The API supports powerful filtering capabilities for different field types:

### Text Field Wildcard Patterns

You can search text fields using wildcard patterns directly in query parameters:

| Pattern | Description | Example | Matches |
|---------|-------------|---------|---------|
| `field=value*` | Starts with | `?name=test*` | "test", "test123", "testing" |
| `field=*value` | Ends with | `?name=*test` | "mytest", "123test" |
| `field=*value*` | Contains | `?name=*test*` | "test", "mytest", "testing" |
| `field=va*ue` | Middle wildcard | `?name=t*t` | "test", "tart", "t123t" |
| `field=value` | Exact match (default) | `?name=test` | "test" (exact, case-insensitive) |

### Number Field Comparison Operators

For number fields (Integer, Float, Decimal), you can use comparison operators:

| Pattern | Description | Example | Matches |
|---------|-------------|---------|---------|
| `field=value` | Exact match | `?age=25` | Exactly 25 |
| `field=>=value` | Greater than or equal | `?age=>=25` | 25, 26, 27, ... |
| `field=<=value` | Less than or equal | `?age=<=100` | ..., 98, 99, 100 |
| `field=>value` | Greater than | `?age=>25` | 26, 27, 28, ... |
| `field=<value` | Less than | `?age=<25` | ..., 23, 24 |
| `field=min-max` | Range (inclusive) | `?age=10-20` | 10, 11, ..., 20 |

### ForeignKey Lookups

You can filter by related ForeignKey fields using double underscores (`__`):

| Pattern | Description | Example |
|---------|-------------|---------|
| `related__field=value*` | Text field in related model | `?first_app__name=test*` |
| `related__field=>=value` | Number field in related model | `?first_app__age=>=18` |
| `related__related__field=value` | Nested ForeignKey lookup | `?first_app__category__name=prod*` |

### Search Examples

**Search by name starting with "test":**
```
GET /first_app/?name=test*
```

**Search by name ending with "ing":**
```
GET /first_app/?name=*ing
```

**Search by name containing "test":**
```
GET /first_app/?name=*test*
```

**Search by exact name match:**
```
GET /first_app/?name=test
# Matches exactly "test" (case-insensitive)
```

**Search with middle wildcard:**
```
GET /first_app/?name=t*t
# Matches: "test", "tart", "t123t"
```

**Multiple filters:**
```
GET /first_app/?name=test*&description=*important*
```

**Search in Second App:**
```
GET /second_app/?name=prod*
```

**Number field filtering (exact match):**
```
GET /first_app/?age=25
```

**Number field filtering (comparison):**
```
GET /first_app/?age=>=18
GET /first_app/?age=<=65
GET /first_app/?age=18-30
```

**ForeignKey lookup (text field):**
```
GET /second_app/?first_app__name=test*
```

**ForeignKey lookup (number field):**
```
GET /second_app/?first_app__age=>=18
```

**Nested ForeignKey lookup:**
```
GET /third_app/?second_app__first_app__name=prod*
```

### Filtering Rules

- ✅ Works for any field on any model
- ✅ Case-insensitive search for text fields
- ✅ Multiple filters can be combined
- ✅ Empty results returned when no matches found
- ✅ **Non-existent fields return empty results** (not all items)
- ✅ Reserved parameters (`page`, `page_size`, `ordering`) are automatically ignored
- ✅ ForeignKey lookups supported with `__` syntax
- ✅ Number fields support comparison operators (`>=`, `<=`, `>`, `<`) and ranges (`10-20`)

## Pagination

Results are paginated by default (20 items per page).

### Pagination Parameters

- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20, max: 100)

### Examples

**Get first page:**
```
GET /first_app/
```

**Get second page:**
```
GET /first_app/?page=2
```

**Get 50 items per page:**
```
GET /first_app/?page_size=50
```

**Combine pagination with search:**
```
GET /first_app/?name=test*&page=2&page_size=50
```

### Paginated Response Format

```json
{
  "count": 150,
  "next": "http://127.0.0.1:8000/first_app/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "test item",
      "description": "...",
      "created_at": "2026-02-06T10:37:10.307956Z",
      "updated_at": "2026-02-06T10:37:10.307984Z"
    },
    ...
  ]
}
```

**Response Fields:**
- `count` - Total number of items
- `next` - URL to next page (null if last page)
- `previous` - URL to previous page (null if first page)
- `results` - Array of items for current page

## Sorting

Sort results using the `ordering` parameter.

### Sorting Syntax

- `ordering=field` - Ascending order
- `ordering=-field` - Descending order
- `ordering=field1,-field2` - Multiple fields

### Examples

**Sort by name (ascending):**
```
GET /first_app/?ordering=name
```

**Sort by created date (newest first):**
```
GET /first_app/?ordering=-created_at
```

**Sort by multiple fields:**
```
GET /first_app/?ordering=name,-created_at
```

**Combine sorting with search:**
```
GET /first_app/?name=test*&ordering=-created_at
```

## Request Examples

### GET - List All Items

```bash
curl -H "Authorization: Token YOUR_TOKEN" \
     http://127.0.0.1:8000/first_app/
```

**Response:** List of all items (paginated)

### GET - Get Single Item

```bash
curl -H "Authorization: Token YOUR_TOKEN" \
     http://127.0.0.1:8000/first_app/1/
```

**Response:** Single item object

### POST - Create New Item

```bash
curl -X POST \
     -H "Authorization: Token YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "New Item",
       "description": "Item description"
     }' \
     http://127.0.0.1:8000/first_app/
```

**Request Body (First App):**
```json
{
  "name": "New Item",
  "description": "Optional description"
}
```

**Request Body (Second App):**
```json
{
  "name": "New Item",
  "description": "Optional description",
  "first_app": 1
}
```

**Response:** Created item with 201 status

### PUT - Full Update

```bash
curl -X PUT \
     -H "Authorization: Token YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Updated Item",
       "description": "Updated description"
     }' \
     http://127.0.0.1:8000/first_app/1/
```

**Note:** PUT requires all fields. Missing fields will be set to null/default.

**Response:** Updated item with 200 status

### PATCH - Partial Update

```bash
curl -X PATCH \
     -H "Authorization: Token YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Updated Name Only"
     }' \
     http://127.0.0.1:8000/first_app/1/
```

**Note:** PATCH only updates provided fields.

**Response:** Updated item with 200 status

### DELETE - Delete Item

```bash
curl -X DELETE \
     -H "Authorization: Token YOUR_TOKEN" \
     http://127.0.0.1:8000/first_app/1/
```

**Response:** 204 No Content (success)

## Response Formats

### Success Responses

**200 OK** - Successful GET, PUT, PATCH
```json
{
  "id": 1,
  "name": "Item Name",
  "description": "Item description",
  "created_at": "2026-02-06T10:37:10.307956Z",
  "updated_at": "2026-02-06T10:37:10.307984Z"
}
```

**201 Created** - Successful POST
```json
{
  "id": 1,
  "name": "New Item",
  "description": "Item description",
  "created_at": "2026-02-06T10:37:10.307956Z",
  "updated_at": "2026-02-06T10:37:10.307984Z"
}
```

**204 No Content** - Successful DELETE (no body)

### Error Responses

**400 Bad Request** - Validation errors
```json
{
  "name": ["This field is required."],
  "description": ["This field may not be blank."]
}
```

**401 Unauthorized** - Missing or invalid token
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**404 Not Found** - Item doesn't exist
```json
{
  "detail": "Not found."
}
```

**500 Internal Server Error** - Server error
```json
{
  "error": "Internal server error",
  "detail": "Error message"
}
```

## Error Handling

### Common Errors

**Missing Authentication:**
```
401 Unauthorized
{
  "detail": "Authentication credentials were not provided."
}
```
**Solution:** Include `Authorization: Token YOUR_TOKEN` header

**Invalid Token:**
```
401 Unauthorized
{
  "detail": "Invalid token."
}
```
**Solution:** Check your token is correct

**Item Not Found:**
```
404 Not Found
{
  "detail": "Not found."
}
```
**Solution:** Check the item ID exists

**Validation Error:**
```
400 Bad Request
{
  "name": ["This field is required."]
}
```
**Solution:** Check required fields are provided

**No Search Results:**
```
200 OK
{
  "count": 0,
  "next": null,
  "previous": null,
  "results": []
}
```
**Note:** This is normal - no items matched your search criteria

## Common Use Cases

### Use Case 1: Search and Filter

**Find all items with name starting with "test":**
```
GET /first_app/?name=test*
```

**Find items created today:**
```
GET /first_app/?created_at=2026-02-06*
```

**Find items with specific description:**
```
GET /first_app/?description=*important*
```

**Find items with age >= 18:**
```
GET /first_app/?age=>=18
```

**Find items with age between 18 and 30:**
```
GET /first_app/?age=18-30
```

**Find Second App items by related First App name:**
```
GET /second_app/?first_app__name=test*
```

**Find Second App items where related First App age >= 18:**
```
GET /second_app/?first_app__age=>=18
```

### Use Case 2: Pagination

**Browse through all items:**
```
# Page 1
GET /first_app/

# Page 2
GET /first_app/?page=2

# Page 3 with 50 items
GET /first_app/?page=3&page_size=50
```

### Use Case 3: Sorting

**Get newest items first:**
```
GET /first_app/?ordering=-created_at
```

**Get items sorted by name:**
```
GET /first_app/?ordering=name
```

**Combine search, sorting, and pagination:**
```
GET /first_app/?name=test*&ordering=-created_at&page=1&page_size=20
```

### Use Case 4: Create and Update

**Create a new item:**
```bash
POST /first_app/
{
  "name": "My New Item",
  "description": "Description here"
}
```

**Update only the name:**
```bash
PATCH /first_app/1/
{
  "name": "Updated Name"
}
```

**Update all fields:**
```bash
PUT /first_app/1/
{
  "name": "Updated Name",
  "description": "Updated Description"
}
```

### Use Case 5: Working with Relationships

**Create Second App item linked to First App:**
```bash
POST /second_app/
{
  "name": "Second Item",
  "first_app": 1
}
```

**Search Second App items by related First App name:**
```
GET /second_app/?first_app__name=test*
```

**Filter Second App items by related First App number field:**
```
GET /second_app/?first_app__age=>=18
```

**Combine multiple filters including ForeignKey:**
```
GET /second_app/?name=prod*&first_app__name=test*&first_app__age=>=18
```

## Tips & Best Practices

1. **Always include Authorization header** - All endpoints require authentication
2. **Use PATCH for partial updates** - Only send fields you want to change
3. **Use wildcard patterns** - `name=test*` is more efficient than fetching all and filtering
4. **Handle pagination** - Check `next` and `previous` fields to navigate pages
5. **Check response status codes** - 200/201/204 = success, 4xx/5xx = error
6. **Empty results are normal** - `{"count": 0, "results": []}` means no matches found
7. **Use sorting** - Combine with search for better results: `?name=test*&ordering=-created_at`
8. **Use number comparisons** - `age=>=18` is more efficient than fetching all and filtering client-side
9. **Use ForeignKey lookups** - Filter by related models: `first_app__name=test*`
10. **Invalid fields return empty** - Non-existent fields or invalid values return empty results, not errors

## Need Help?

- **API Base URL:** `http://127.0.0.1:8000`
- **Authentication:** Token-based (contact administrator for token)
- **Content-Type:** `application/json` for POST/PUT/PATCH requests
- **Response Format:** JSON

For technical implementation details, see the developer documentation.
