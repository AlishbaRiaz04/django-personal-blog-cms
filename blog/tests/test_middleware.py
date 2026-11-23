from django.contrib.sessions.models import Session
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


class PageViewBotAndSessionTest(TestCase):
    GOOGLEBOT = (
        "Mozilla/5.0 (compatible; Googlebot/2.1; "
        "+http://www.google.com/bot.html)"
    )
    BROWSER = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )

    def test_bot_requests_are_not_recorded(self):
        response = self.client.get(
            reverse("home"), HTTP_USER_AGENT=self.GOOGLEBOT
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(PageView.objects.count(), 0)

    def test_command_line_clients_are_not_recorded(self):
        self.client.get(reverse("home"), HTTP_USER_AGENT="curl/8.5.0")
        self.client.get(
            reverse("home"), HTTP_USER_AGENT="python-requests/2.32"
        )

        self.assertEqual(PageView.objects.count(), 0)

    def test_normal_browser_is_recorded(self):
        self.client.get(reverse("home"), HTTP_USER_AGENT=self.BROWSER)

        self.assertEqual(PageView.objects.count(), 1)

    def test_tracking_does_not_create_session_rows(self):
        self.client.get(reverse("home"), HTTP_USER_AGENT=self.BROWSER)
        self.client.get(reverse("home"), HTTP_USER_AGENT=self.BROWSER)

        self.assertEqual(Session.objects.count(), 0)

    def test_visitor_cookie_is_set_httponly_on_first_visit(self):
        response = self.client.get(
            reverse("home"), HTTP_USER_AGENT=self.BROWSER
        )

        cookie = response.cookies["visitor_id"]

        self.assertTrue(cookie.value)
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")

    def test_returning_visitor_keeps_one_visitor_id(self):
        first = self.client.get(reverse("home"), HTTP_USER_AGENT=self.BROWSER)
        second = self.client.get(reverse("home"), HTTP_USER_AGENT=self.BROWSER)

        self.assertNotIn("visitor_id", second.cookies)
        self.assertEqual(
            set(PageView.objects.values_list("visitor_id", flat=True)),
            {first.cookies["visitor_id"].value},
        )

    def test_oversized_visitor_cookie_is_replaced(self):
        self.client.cookies["visitor_id"] = "x" * 200

        self.client.get(reverse("home"), HTTP_USER_AGENT=self.BROWSER)

        self.assertLessEqual(len(PageView.objects.get().visitor_id), 64)
