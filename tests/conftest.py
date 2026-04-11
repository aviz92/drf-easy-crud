from collections.abc import Callable
from typing import Any

import pytest
from rest_framework.serializers import ModelSerializer

from tests.test_app.models import Article, Tag

ArticleFactory = Callable[..., Article]
TagFactory = Callable[..., Tag]


class TagSerializer(ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


class ArticleSerializer(ModelSerializer):
    class Meta:
        model = Article
        fields = ["id", "title", "content", "views", "rating", "is_published", "tag"]


@pytest.fixture
def article_factory(db: None) -> ArticleFactory:
    def _factory(**kwargs: Any) -> Article:
        defaults: dict[str, Any] = {
            "title": "Test Article",
            "content": "",
            "views": 0,
            "rating": 0.0,
            "is_published": False,
        }
        defaults.update(kwargs)
        return Article.objects.create(**defaults)

    return _factory


@pytest.fixture
def tag_factory(db: None) -> TagFactory:
    def _factory(**kwargs: Any) -> Tag:
        defaults: dict[str, Any] = {"name": "test-tag"}
        defaults.update(kwargs)
        return Tag.objects.create(**defaults)

    return _factory
