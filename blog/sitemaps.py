from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Article

class ArticleSitemap(Sitemap):
    changefreq="weekly"
    priority=0.8

    def items(self):
        return Article.objects.filter(
            status=Article.Status.PUBLISHED,
            published_at__isnull=False,
        )

    def location(self, obj):
        return reverse(
            "article_detail",
            kwargs={"slug": obj.slug},
        )

    def lastmod(self, obj):
        return obj.updated_at
