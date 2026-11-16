
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from blog.models import Article


class ArticleSitemapTest(TestCase):

    def setUp(self):
        Article.objects.create(
            title="Published Article",
            slug="published-article",
            content="This article is public.",
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
        )

        Article.objects.create(
            title="Draft Article",
            slug="draft-article",
            content="This article is private.",
            status=Article.Status.DRAFT,
        )

        Article.objects.create(
            title="Scheduled Article",
            slug="scheduled-article",
            content="This article is not public yet.",
            status=Article.Status.SCHEDULED,
            scheduled_at=timezone.now() + timedelta(days=1),
        )

    def test_sitemap_contains_only_published_articles(self):
        response = self.client.get("/sitemap.xml")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "published-article")
        self.assertNotContains(response, "draft-article")
        self.assertNotContains(response, "scheduled-article")

    def test_sitemap_contains_article_last_modified_date(self):
        response = self.client.get("/sitemap.xml")

        article = Article.objects.get(slug="published-article")

        self.assertContains(
            response,
            article.updated_at.strftime("%Y-%m-%d"),
        )
