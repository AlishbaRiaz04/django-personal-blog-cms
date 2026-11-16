from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from blog.models import Article, PageView

class PageViewMiddlewareTest(TestCase):
    def setUp(self):
        self.article = Article.objects.create(
            title="Middleware Test Article",
            content="Testing visitor tracking.",
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
        )

    def test_homepage_visit_is_recorded(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(PageView.objects.count(), 1)

        page_view = PageView.objects.first()

        self.assertEqual(
            page_view.page_type,
            PageView.PageType.HOMEPAGE,
        )
        self.assertIsNone(page_view.article)

    def test_article_visit_is_recorded(self):
        response = self.client.get(
            reverse(
                "article_detail",
                kwargs={"slug": self.article.slug},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(PageView.objects.count(), 1)

        page_view = PageView.objects.first()

        self.assertEqual(
            page_view.page_type,
            PageView.PageType.ARTICLE,
        )
        self.assertEqual(page_view.article, self.article)

    def test_rss_feed_is_not_recorded(self):
        response = self.client.get(reverse("rss_feed"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/rss+xml", response["Content-Type"])
        self.assertEqual(PageView.objects.count(), 0)

    def test_failed_article_response_is_not_recorded(self):
        response = self.client.get(
            reverse(
                "article_detail",
                kwargs={"slug": "article-that-does-not-exist"},
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(PageView.objects.count(), 0)

    def test_visitor_id_is_reused_across_requests(self):
        self.client.get(reverse("home"))

        self.client.get(
            reverse(
                "article_detail",
                kwargs={"slug": self.article.slug},
            )
        )

        page_views = PageView.objects.all()

        self.assertEqual(page_views.count(), 2)

        visitor_ids = set(
            page_views.values_list("visitor_id", flat=True)
        )

        self.assertEqual(len(visitor_ids), 1)
        self.assertTrue(visitor_ids.pop())
