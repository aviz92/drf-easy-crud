# pylint: disable=W0212
from typing import Any

import pytest
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import JSONParser
from rest_framework.permissions import BasePermission
from rest_framework.request import Request as DRFRequest
from rest_framework.test import APIRequestFactory

from drf_easy_crud.crud_utils import CRUDUtils
from tests.conftest import ArticleFactory, ArticleSerializer
from tests.test_app.models import Article


class DenyAll(BasePermission):
    """Permission class that always denies object access — used in tests."""

    def has_object_permission(self, request: DRFRequest, view: Any, obj: Any) -> bool:
        return False


class AllowAll(BasePermission):
    """Permission class that always allows object access — used in tests."""

    def has_object_permission(self, request: DRFRequest, view: Any, obj: Any) -> bool:
        return True


rf = APIRequestFactory()
_json_parsers = [JSONParser()]


def get(path: str, params: dict | None = None) -> DRFRequest:
    return DRFRequest(rf.get(path, params or {}))


def post(path: str, data: dict) -> DRFRequest:
    return DRFRequest(rf.post(path, data, format="json"), parsers=_json_parsers)


def put(path: str, data: dict) -> DRFRequest:
    return DRFRequest(rf.put(path, data, format="json"), parsers=_json_parsers)


def patch(path: str, data: dict) -> DRFRequest:
    return DRFRequest(rf.patch(path, data, format="json"), parsers=_json_parsers)


def delete(path: str) -> DRFRequest:
    return DRFRequest(rf.delete(path))


class TestGetInstanceByPk:
    @pytest.mark.django_db
    def test_returns_instance_when_found(self, article_factory: ArticleFactory) -> None:
        article = article_factory(title="Found")
        result = CRUDUtils._get_instance_by_pk(queryset=Article.objects.all(), pk=article.pk)
        assert result is not None
        assert result.pk == article.pk

    @pytest.mark.django_db
    def test_returns_none_when_not_found(self) -> None:
        result = CRUDUtils._get_instance_by_pk(queryset=Article.objects.all(), pk=99999)
        assert result is None

    @pytest.mark.django_db
    def test_respects_queryset_scope(self, article_factory: ArticleFactory) -> None:
        article = article_factory(title="Published", is_published=True)
        article_factory(title="Draft", is_published=False)
        scoped_qs = Article.objects.filter(is_published=True)
        assert CRUDUtils._get_instance_by_pk(queryset=scoped_qs, pk=article.pk) is not None
        draft = Article.objects.filter(is_published=False).first()
        assert CRUDUtils._get_instance_by_pk(queryset=scoped_qs, pk=draft.pk) is None


class TestGetDetail:
    @pytest.mark.django_db
    def test_returns_200_when_found(self, article_factory: ArticleFactory) -> None:
        article = article_factory(title="Detail Test")
        response = CRUDUtils.get_detail(
            request=get(f"/articles/{article.pk}/"),
            serializer_class=ArticleSerializer,
            pk=article.pk,
            queryset=Article.objects.all(),
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Detail Test"

    @pytest.mark.django_db
    def test_returns_404_when_not_found(self) -> None:
        response = CRUDUtils.get_detail(
            request=get("/articles/99999/"),
            serializer_class=ArticleSerializer,
            pk=99999,
            queryset=Article.objects.all(),
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_respects_queryset_scope(self, article_factory: ArticleFactory) -> None:
        article = article_factory(title="Draft", is_published=False)
        response = CRUDUtils.get_detail(
            request=get(f"/articles/{article.pk}/"),
            serializer_class=ArticleSerializer,
            pk=article.pk,
            queryset=Article.objects.filter(is_published=True),
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetList:
    @pytest.mark.django_db
    def test_returns_200_with_results(self, article_factory: ArticleFactory) -> None:
        article_factory(title="Article A")
        article_factory(title="Article B")
        response = CRUDUtils.get_list(
            request=get("/articles/"),
            serializer_class=ArticleSerializer,
            queryset=Article.objects.all(),
        )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_returns_empty_list(self) -> None:
        response = CRUDUtils.get_list(
            request=get("/articles/"),
            serializer_class=ArticleSerializer,
            queryset=Article.objects.all(),
        )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_queryset_restricts_results(self, article_factory: ArticleFactory) -> None:
        article_factory(is_published=True)
        article_factory(is_published=False)
        response = CRUDUtils.get_list(
            request=get("/articles/"),
            serializer_class=ArticleSerializer,
            queryset=Article.objects.filter(is_published=True),
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1


class TestGet:
    @pytest.mark.django_db
    def test_routes_to_detail_when_pk_given(self, article_factory: ArticleFactory) -> None:
        article = article_factory(title="Route Test")
        response = CRUDUtils.get(
            request=get(f"/articles/{article.pk}/"),
            serializer_class=ArticleSerializer,
            queryset=Article.objects.all(),
            pk=article.pk,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Route Test"

    @pytest.mark.django_db
    def test_routes_to_list_without_pk(self, article_factory: ArticleFactory) -> None:
        article_factory()
        response = CRUDUtils.get(
            request=get("/articles/"),
            serializer_class=ArticleSerializer,
            queryset=Article.objects.all(),
        )
        assert response.status_code == status.HTTP_200_OK
        assert "count" in response.data

    @pytest.mark.django_db
    def test_pk_zero_routes_to_detail(self) -> None:
        response = CRUDUtils.get(
            request=get("/articles/0/"),
            serializer_class=ArticleSerializer,
            queryset=Article.objects.all(),
            pk=0,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestPost:
    @pytest.mark.django_db
    def test_creates_instance_and_returns_201(self) -> None:
        response = CRUDUtils.post(
            request=post("/articles/", {"title": "New Article", "views": 0}),
            serializer_class=ArticleSerializer,
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert Article.objects.filter(title="New Article").exists()

    @pytest.mark.django_db
    def test_returns_400_on_validation_failure(self) -> None:
        response = CRUDUtils.post(
            request=post("/articles/", {}),  # title is required
            serializer_class=ArticleSerializer,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestPut:
    @pytest.mark.django_db
    def test_full_update_returns_200(self, article_factory: ArticleFactory) -> None:
        article = article_factory(title="Old Title")
        response = CRUDUtils.put(
            request=put(f"/articles/{article.pk}/", {"title": "New Title", "views": 5}),
            serializer_class=ArticleSerializer,
            queryset=Article.objects.all(),
            pk=article.pk,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "New Title"
        article.refresh_from_db()
        assert article.title == "New Title"

    @pytest.mark.django_db
    def test_returns_404_when_pk_missing(self) -> None:
        response = CRUDUtils.put(
            request=put("/articles/", {"title": "Title"}),
            serializer_class=ArticleSerializer,
            queryset=Article.objects.all(),
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_returns_404_for_nonexistent_instance(self) -> None:
        response = CRUDUtils.put(
            request=put("/articles/99999/", {"title": "Title"}),
            serializer_class=ArticleSerializer,
            queryset=Article.objects.all(),
            pk=99999,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_respects_queryset_scope(self, article_factory: ArticleFactory) -> None:
        article = article_factory(title="Draft", is_published=False)
        response = CRUDUtils.put(
            request=put(f"/articles/{article.pk}/", {"title": "Updated"}),
            serializer_class=ArticleSerializer,
            queryset=Article.objects.filter(is_published=True),
            pk=article.pk,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestPatch:
    @pytest.mark.django_db
    def test_partial_update_returns_200(self, article_factory: ArticleFactory) -> None:
        article = article_factory(title="Original")
        response = CRUDUtils.patch(
            request=patch(f"/articles/{article.pk}/", {"title": "Patched"}),
            serializer_class=ArticleSerializer,
            queryset=Article.objects.all(),
            pk=article.pk,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Patched"

    @pytest.mark.django_db
    def test_returns_404_when_pk_missing(self) -> None:
        response = CRUDUtils.patch(
            request=patch("/articles/", {"title": "Title"}),
            serializer_class=ArticleSerializer,
            queryset=Article.objects.all(),
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDelete:
    @pytest.mark.django_db
    def test_deletes_instance_and_returns_204(self, article_factory: ArticleFactory) -> None:
        article = article_factory()
        response = CRUDUtils.delete(
            request=delete(f"/articles/{article.pk}/"),
            queryset=Article.objects.all(),
            pk=article.pk,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Article.objects.filter(pk=article.pk).exists()

    @pytest.mark.django_db
    def test_returns_404_for_nonexistent_pk(self) -> None:
        response = CRUDUtils.delete(
            request=delete("/articles/99999/"),
            queryset=Article.objects.all(),
            pk=99999,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_returns_404_when_pk_missing(self) -> None:
        response = CRUDUtils.delete(
            request=delete("/articles/"),
            queryset=Article.objects.all(),
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_respects_queryset_scope(self, article_factory: ArticleFactory) -> None:
        article = article_factory(is_published=False)
        response = CRUDUtils.delete(
            request=delete(f"/articles/{article.pk}/"),
            queryset=Article.objects.filter(is_published=True),
            pk=article.pk,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Article.objects.filter(pk=article.pk).exists()  # not deleted


class TestModelClassShorthand:
    """Verify that passing a Model class is equivalent to Model.objects.all()."""

    @pytest.mark.django_db
    def test_get_detail_accepts_model_class(self, article_factory: ArticleFactory) -> None:
        article = article_factory(title="Shorthand")
        response = CRUDUtils.get_detail(
            request=get(f"/articles/{article.pk}/"),
            serializer_class=ArticleSerializer,
            pk=article.pk,
            queryset=Article,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Shorthand"

    @pytest.mark.django_db
    def test_get_list_accepts_model_class(self, article_factory: ArticleFactory) -> None:
        article_factory()
        response = CRUDUtils.get_list(
            request=get("/articles/"),
            serializer_class=ArticleSerializer,
            queryset=Article,
        )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_delete_accepts_model_class(self, article_factory: ArticleFactory) -> None:
        article = article_factory()
        response = CRUDUtils.delete(
            request=delete(f"/articles/{article.pk}/"),
            queryset=Article,
            pk=article.pk,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestObjectPermissions:
    """Verify that permission_classes are enforced on detail, update, and delete."""

    @pytest.mark.django_db
    def test_get_detail_raises_403_when_denied(self, article_factory: ArticleFactory) -> None:
        article = article_factory()
        with pytest.raises(PermissionDenied):
            CRUDUtils.get_detail(
                request=get(f"/articles/{article.pk}/"),
                serializer_class=ArticleSerializer,
                pk=article.pk,
                queryset=Article.objects.all(),
                permission_classes=[DenyAll],
            )

    @pytest.mark.django_db
    def test_get_detail_succeeds_when_allowed(self, article_factory: ArticleFactory) -> None:
        article = article_factory()
        response = CRUDUtils.get_detail(
            request=get(f"/articles/{article.pk}/"),
            serializer_class=ArticleSerializer,
            pk=article.pk,
            queryset=Article.objects.all(),
            permission_classes=[AllowAll],
        )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_put_raises_403_when_denied(self, article_factory: ArticleFactory) -> None:
        article = article_factory()
        with pytest.raises(PermissionDenied):
            CRUDUtils.put(
                request=put(f"/articles/{article.pk}/", {"title": "Updated"}),
                serializer_class=ArticleSerializer,
                queryset=Article.objects.all(),
                permission_classes=[DenyAll],
                pk=article.pk,
            )

    @pytest.mark.django_db
    def test_patch_raises_403_when_denied(self, article_factory: ArticleFactory) -> None:
        article = article_factory()
        with pytest.raises(PermissionDenied):
            CRUDUtils.patch(
                request=patch(f"/articles/{article.pk}/", {"title": "Patched"}),
                serializer_class=ArticleSerializer,
                queryset=Article.objects.all(),
                permission_classes=[DenyAll],
                pk=article.pk,
            )

    @pytest.mark.django_db
    def test_delete_raises_403_when_denied(self, article_factory: ArticleFactory) -> None:
        article = article_factory()
        with pytest.raises(PermissionDenied):
            CRUDUtils.delete(
                request=delete(f"/articles/{article.pk}/"),
                queryset=Article.objects.all(),
                permission_classes=[DenyAll],
                pk=article.pk,
            )
        assert Article.objects.filter(pk=article.pk).exists()  # not deleted

    @pytest.mark.django_db
    def test_multiple_classes_all_must_pass(self, article_factory: ArticleFactory) -> None:
        article = article_factory()
        with pytest.raises(PermissionDenied):
            CRUDUtils.get_detail(
                request=get(f"/articles/{article.pk}/"),
                serializer_class=ArticleSerializer,
                pk=article.pk,
                queryset=Article.objects.all(),
                permission_classes=[AllowAll, DenyAll],
            )
