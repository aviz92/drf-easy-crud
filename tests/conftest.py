import pytest
from rest_framework.serializers import ModelSerializer
from rest_framework.test import APIRequestFactory

from tests.test_app.models import Article, Tag


class TagSerializer(ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


class ArticleSerializer(ModelSerializer):
    class Meta:
        model = Article
        fields = ["id", "title", "content", "views", "rating", "is_published", "tag"]


@pytest.fixture
def rf() -> APIRequestFactory:
    return APIRequestFactory()


@pytest.fixture
def article_factory(db):
    def _factory(**kwargs) -> Article:
        defaults = {"title": "Test Article", "content": "", "views": 0, "rating": 0.0, "is_published": False}
        defaults.update(kwargs)
        return Article.objects.create(**defaults)

    return _factory


@pytest.fixture
def tag_factory(db):
    def _factory(**kwargs) -> Tag:
        defaults = {"name": "test-tag"}
        defaults.update(kwargs)
        return Tag.objects.create(**defaults)

    return _factory
