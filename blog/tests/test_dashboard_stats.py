from django.contrib.auth.models import User
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from blog.models import Article, AuthorProfile, PageView


class DashboardStatsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="writer", password="x-pass-12345"
        )
        self.profile = AuthorProfile.objects.create(user=self.user)
        self.client.force_login(self.user)
        self.url = reverse("author_dashboard")

    def make_article(self, title="Article", author=None, **extra):
        fields = {
            "title": title,
            "content": "<p>Body</p>",
            "author": author or self.profile,
            "status": Article.Status.PUBLISHED,
            "published_at": timezone.now(),
        }
        fields.update(extra)
        return Article.objects.create(**fields)

    def add_views(self, article, *visitor_ids):
        for visitor_id in visitor_ids:
            PageView.objects.create(
                visitor_id=visitor_id,
                page_type=PageView.PageType.ARTICLE,
                article=article,
            )

    def dashboard_article(self, article):
        response = self.client.get(self.url)
        for item in response.context["articles"]:
            if item.pk == article.pk:
                return item
        self.fail("Article not on the dashboard")


class PerArticleStatsTests(DashboardStatsTestCase):
    def test_article_shows_its_total_views(self):
        article = self.make_article()
        self.add_views(article, "a", "a", "b")

        item = self.dashboard_article(article)

        self.assertEqual(item.view_count, 3)

    def test_unique_visitors_are_counted_once_each(self):
        article = self.make_article()
        self.add_views(article, "a", "a", "a", "b")

        item = self.dashboard_article(article)

        self.assertEqual(item.view_count, 4)
        self.assertEqual(item.unique_visitors, 2)

    def test_article_without_views_shows_zero(self):
        article = self.make_article()

        response = self.client.get(self.url)

        self.assertContains(response, "0 views")
        self.assertContains(response, "0 unique visitors")
        self.assertEqual(self.dashboard_article(article).view_count, 0)

    def test_one_view_uses_singular_wording(self):
        article = self.make_article()
        self.add_views(article, "a")

        response = self.client.get(self.url)

        self.assertContains(response, "1 view")
        self.assertNotContains(response, "1 views")
        self.assertContains(response, "1 unique visitor")
        self.assertNotContains(response, "1 unique visitors")

    def test_views_are_not_mixed_up_between_articles(self):
        first = self.make_article("First")
        second = self.make_article("Second")
        self.add_views(first, "a", "b", "c")
        self.add_views(second, "a")

        self.assertEqual(self.dashboard_article(first).view_count, 3)
        self.assertEqual(self.dashboard_article(second).view_count, 1)


class TotalsTests(DashboardStatsTestCase):
    def test_totals_add_up_across_all_articles(self):
        first = self.make_article("First")
        second = self.make_article("Second")
        self.add_views(first, "a", "b")
        self.add_views(second, "a", "c", "c")

        response = self.client.get(self.url)

        self.assertEqual(response.context["total_views"], 5)
        # visitors a, b and c; "a" visited both articles but counts once
        self.assertEqual(response.context["total_unique_visitors"], 3)

    def test_totals_ignore_other_authors_articles(self):
        other_user = User.objects.create_user(
            username="other", password="x-pass-12345"
        )
        other_profile = AuthorProfile.objects.create(user=other_user)
        mine = self.make_article("Mine")
        theirs = self.make_article("Theirs", author=other_profile)
        self.add_views(mine, "a")
        self.add_views(theirs, "a", "b", "c", "d")

        response = self.client.get(self.url)

        self.assertEqual(response.context["total_views"], 1)
        self.assertEqual(response.context["total_unique_visitors"], 1)

    def test_other_authors_articles_are_not_listed(self):
        other_user = User.objects.create_user(
            username="other", password="x-pass-12345"
        )
        other_profile = AuthorProfile.objects.create(user=other_user)
        self.make_article("Theirs", author=other_profile)

        response = self.client.get(self.url)

        self.assertEqual(len(response.context["articles"]), 0)

    def test_status_filter_does_not_change_the_totals(self):
        published = self.make_article("Live")
        self.make_article(
            "Draft", status=Article.Status.DRAFT, published_at=None
        )
        self.add_views(published, "a", "b")

        response = self.client.get(self.url, {"status": "draft"})

        self.assertEqual(len(response.context["articles"]), 1)
        self.assertEqual(response.context["total_views"], 2)

    def test_homepage_visits_are_not_counted_as_article_views(self):
        self.make_article()
        PageView.objects.create(
            visitor_id="a", page_type=PageView.PageType.HOMEPAGE
        )

        response = self.client.get(self.url)

        self.assertEqual(response.context["total_views"], 0)

    def test_no_articles_shows_zero_totals(self):
        response = self.client.get(self.url)

        self.assertEqual(response.context["total_views"], 0)
        self.assertEqual(response.context["total_unique_visitors"], 0)
        self.assertContains(response, "Total article views")


class EndToEndTests(DashboardStatsTestCase):
    def test_real_visits_are_counted_by_the_middleware(self):
        article = self.make_article("Real visits")
        article_url = reverse("article_detail", kwargs={"slug": article.slug})

        visitor_one = Client()
        visitor_two = Client()
        visitor_one.get(article_url)
        visitor_one.get(article_url)   # same person reads it twice
        visitor_two.get(article_url)   # a different person reads it once

        item = self.dashboard_article(article)

        self.assertEqual(item.view_count, 3)
        self.assertEqual(item.unique_visitors, 2)


class QueryCountTests(DashboardStatsTestCase):
    def count_queries(self):
        with CaptureQueriesContext(connection) as context:
            self.client.get(self.url)
        return len(context)

    def test_number_of_queries_does_not_grow_with_the_article_count(self):
        first = self.make_article("One")
        self.add_views(first, "a")
        queries_with_one_article = self.count_queries()

        for number in range(2, 7):
            article = self.make_article(f"Article {number}")
            self.add_views(article, "a", "b")

        self.assertEqual(self.count_queries(), queries_with_one_article)