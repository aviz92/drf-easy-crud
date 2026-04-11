from django.db import models


class Tag(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        app_label = "test_app"


class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField(default="")
    views = models.IntegerField(default=0)
    rating = models.FloatField(default=0.0)
    is_published = models.BooleanField(default=False)
    tag = models.ForeignKey(Tag, on_delete=models.SET_NULL, null=True, blank=True, related_name="articles")

    class Meta:
        app_label = "test_app"
