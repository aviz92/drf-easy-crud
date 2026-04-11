import pytest
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request as DRFRequest
from rest_framework.test import APIRequestFactory

from drf_easy_crud.filter_utils import FilterUtils
from tests.test_app.models import Article, Tag


rf = APIRequestFactory()


def make_get(path: str, params: dict | None = None) -> DRFRequest:
    return DRFRequest(rf.get(path, params or {}))


class TestWildcardToRegex:
    def test_escapes_dots(self) -> None:
        assert FilterUtils._wildcard_to_regex("test.value") == r"test\.value"

    def test_converts_star_to_dot_star(self) -> None:
        assert FilterUtils._wildcard_to_regex("*hello*") == ".*hello.*"

    def test_star_only(self) -> None:
        assert FilterUtils._wildcard_to_regex("*") == ".*"


class TestHasMiddleWildcard:
    def test_middle_wildcard_returns_true(self) -> None:
        assert FilterUtils._has_middle_wildcard("he*llo") is True

    def test_leading_star_returns_false(self) -> None:
        assert FilterUtils._has_middle_wildcard("*hello") is False

    def test_trailing_star_returns_false(self) -> None:
        assert FilterUtils._has_middle_wildcard("hello*") is False

    def test_short_string_returns_false(self) -> None:
        assert FilterUtils._has_middle_wildcard("*") is False

    def test_no_star_returns_false(self) -> None:
        assert FilterUtils._has_middle_wildcard("hello") is False


class TestApplyTextWildcardFilter:
    @pytest.mark.django_db
    def test_exact_match(self, article_factory) -> None:
        article_factory(title="Django REST")
        article_factory(title="Django ORM")
        qs = Article.objects.all()
        result = FilterUtils._apply_text_wildcard_filter(qs, "title", "Django REST")
        assert result.count() == 1
        assert result.first().title == "Django REST"

    @pytest.mark.django_db
    def test_contains_wildcard(self, article_factory) -> None:
        article_factory(title="Django REST")
        article_factory(title="Flask API")
        qs = Article.objects.all()
        result = FilterUtils._apply_text_wildcard_filter(qs, "title", "*Django*")
        assert result.count() == 1
        assert result.first().title == "Django REST"

    @pytest.mark.django_db
    def test_starts_with_wildcard(self, article_factory) -> None:
        article_factory(title="Django REST")
        article_factory(title="Django ORM")
        article_factory(title="Flask API")
        qs = Article.objects.all()
        result = FilterUtils._apply_text_wildcard_filter(qs, "title", "Django*")
        assert result.count() == 2

    @pytest.mark.django_db
    def test_ends_with_wildcard(self, article_factory) -> None:
        article_factory(title="Django REST")
        article_factory(title="Flask REST")
        article_factory(title="Flask API")
        qs = Article.objects.all()
        result = FilterUtils._apply_text_wildcard_filter(qs, "title", "*REST")
        assert result.count() == 2

    @pytest.mark.django_db
    def test_middle_wildcard_uses_regex(self, article_factory) -> None:
        article_factory(title="hello world")
        article_factory(title="hxllo world")
        article_factory(title="no match")
        qs = Article.objects.all()
        result = FilterUtils._apply_text_wildcard_filter(qs, "title", "h*llo world")
        assert result.count() == 2

    @pytest.mark.django_db
    def test_exact_match_case_insensitive(self, article_factory) -> None:
        article_factory(title="Django REST")
        qs = Article.objects.all()
        result = FilterUtils._apply_text_wildcard_filter(qs, "title", "django rest")
        assert result.count() == 1


class TestApplyNumberFilter:
    @pytest.fixture(autouse=True)
    def setup(self, article_factory) -> None:
        article_factory(views=5)
        article_factory(views=15)
        article_factory(views=25)

    @pytest.mark.django_db
    def test_exact_match(self) -> None:
        qs = Article.objects.all()
        field = Article._meta.get_field("views")
        result = FilterUtils._apply_number_filter(qs, "views", "15", field)
        assert result.count() == 1
        assert result.first().views == 15

    @pytest.mark.django_db
    def test_gte_operator(self) -> None:
        qs = Article.objects.all()
        field = Article._meta.get_field("views")
        result = FilterUtils._apply_number_filter(qs, "views", ">=15", field)
        assert result.count() == 2

    @pytest.mark.django_db
    def test_lte_operator(self) -> None:
        qs = Article.objects.all()
        field = Article._meta.get_field("views")
        result = FilterUtils._apply_number_filter(qs, "views", "<=15", field)
        assert result.count() == 2

    @pytest.mark.django_db
    def test_gt_operator(self) -> None:
        qs = Article.objects.all()
        field = Article._meta.get_field("views")
        result = FilterUtils._apply_number_filter(qs, "views", ">15", field)
        assert result.count() == 1
        assert result.first().views == 25

    @pytest.mark.django_db
    def test_lt_operator(self) -> None:
        qs = Article.objects.all()
        field = Article._meta.get_field("views")
        result = FilterUtils._apply_number_filter(qs, "views", "<15", field)
        assert result.count() == 1
        assert result.first().views == 5

    @pytest.mark.django_db
    def test_invalid_value_returns_none_queryset(self) -> None:
        qs = Article.objects.all()
        field = Article._meta.get_field("views")
        result = FilterUtils._apply_number_filter(qs, "views", "not-a-number", field)
        assert result.count() == 0


class TestGetLookupTargetField:
    @pytest.mark.django_db
    def test_direct_field(self) -> None:
        field = FilterUtils._get_lookup_target_field(Article, "title")
        assert field is not None
        assert field.name == "title"

    @pytest.mark.django_db
    def test_fk_traversal(self) -> None:
        field = FilterUtils._get_lookup_target_field(Article, "tag__name")
        assert field is not None
        assert field.name == "name"

    @pytest.mark.django_db
    def test_nonexistent_field_returns_none(self) -> None:
        result = FilterUtils._get_lookup_target_field(Article, "nonexistent__field")
        assert result is None

    @pytest.mark.django_db
    def test_nonexistent_final_field_returns_none(self) -> None:
        result = FilterUtils._get_lookup_target_field(Article, "tag__nonexistent")
        assert result is None


class TestApplyWildcardFiltering:
    @pytest.mark.django_db
    def test_filters_by_title(self, article_factory) -> None:
        article_factory(title="Python Guide")
        article_factory(title="Django Guide")
        request = make_get("/", {"title": "*Guide*"})
        result = FilterUtils.apply_wildcard_filtering(queryset=Article.objects.all(), request=request)
        assert result.count() == 2

    @pytest.mark.django_db
    def test_reserved_params_are_skipped(self, article_factory) -> None:
        article_factory(title="Article One")
        request = make_get("/", {"page": "1", "page_size": "10"})
        result = FilterUtils.apply_wildcard_filtering(queryset=Article.objects.all(), request=request)
        assert result.count() == 1

    @pytest.mark.django_db
    def test_invalid_field_raises_validation_error(self, article_factory) -> None:
        article_factory()
        request = make_get("/", {"nonexistent": "value"})
        with pytest.raises(ValidationError):
            FilterUtils.apply_wildcard_filtering(queryset=Article.objects.all(), request=request)

    @pytest.mark.django_db
    def test_filterable_fields_allowlist_blocks_unlisted_params(self, article_factory) -> None:
        article_factory(title="Only One", views=100)
        request = make_get("/", {"views": "100"})
        # views is not in allowlist — should be silently skipped
        result = FilterUtils.apply_wildcard_filtering(
            queryset=Article.objects.all(),
            request=request,
            filterable_fields=["title"],
        )
        assert result.count() == 1  # no filtering applied, all returned

    @pytest.mark.django_db
    def test_filterable_fields_allowlist_permits_listed_params(self, article_factory) -> None:
        article_factory(title="Match", views=100)
        article_factory(title="No Match", views=5)
        request = make_get("/", {"title": "Match"})
        result = FilterUtils.apply_wildcard_filtering(
            queryset=Article.objects.all(),
            request=request,
            filterable_fields=["title"],
        )
        assert result.count() == 1
        assert result.first().title == "Match"

    @pytest.mark.django_db
    def test_fk_filter(self, article_factory, tag_factory) -> None:
        tag = tag_factory(name="python")
        article_factory(title="Python Post", tag=tag)
        article_factory(title="Other Post")
        request = make_get("/", {"tag__name": "python"})
        result = FilterUtils.apply_wildcard_filtering(queryset=Article.objects.all(), request=request)
        assert result.count() == 1
        assert result.first().title == "Python Post"
