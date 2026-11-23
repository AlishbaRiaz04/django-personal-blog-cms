from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from blog.models import Article


class ArticleFeedTest(TestCase):

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

    def test_rss_feed_contains_only_published_articles(self):
        response = self.client.get("/feeds/rss/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Published Article")
        self.assertNotContains(response, "Draft Article")
        self.assertNotContains(response, "Scheduled Article")
        self.assertContains(response, "/article/published-article/")

    def test_atom_feed_contains_only_published_articles(self):
        response = self.client.get("/feeds/atom/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Published Article")
        self.assertNotContains(response, "Draft Article")
        self.assertNotContains(response, "Scheduled Article")
        self.assertContains(response, "/article/published-article/")
