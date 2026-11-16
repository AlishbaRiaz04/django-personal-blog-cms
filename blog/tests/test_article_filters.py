from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from blog.models import Article, Category


class ArticleFilterTests(TestCase):

    def setUp(self):
        self.category = Category.objects.create(name="Development")
        self.other_category = Category.objects.create(name="Tutorials")

        self.url = reverse("home")

    def create_article(self, title, status=Article.Status.PUBLISHED,
                       category=None, tags=None):
        article = Article.objects.create(
            title=title,
            content="Test article content",
            status=status,
            published_at=(
                timezone.now()
                if status == Article.Status.PUBLISHED
                else None
            ),
        )

        if category:
            article.categories.add(category)

        if tags:
            article.tags.add(*tags)

        return article

    def test_category_filter(self):
        matching = self.create_article(
            "Django Article",
            category=self.category,
        )

        self.create_article(
            "Other Article",
            category=self.other_category,
        )

        response = self.client.get(
            self.url,
            {"category": self.category.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, matching.title)
        self.assertNotContains(response, "Other Article")

    def test_tag_filter(self):
        matching = self.create_article(
            "Python Article",
            tags=["python"],
        )

        self.create_article(
            "Django Article",
            tags=["django"],
        )

        response = self.client.get(
            self.url,
            {"tag": "python"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, matching.title)
        self.assertNotContains(response, "Django Article")

    def test_combined_category_and_tag_filter(self):
        matching = self.create_article(
            "Matching Article",
            category=self.category,
            tags=["django"],
        )

        self.create_article(
            "Wrong Category",
            category=self.other_category,
            tags=["django"],
        )

        self.create_article(
            "Wrong Tag",
            category=self.category,
            tags=["python"],
        )

        response = self.client.get(
            self.url,
            {
                "category": self.category.id,
                "tag": "django",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, matching.title)
        self.assertNotContains(response, "Wrong Category")
        self.assertNotContains(response, "Wrong Tag")

    def test_filters_exclude_unpublished_articles(self):
        published = self.create_article(
            "Published Article",
            category=self.category,
            tags=["django"],
        )

        self.create_article(
            "Draft Article",
            status=Article.Status.DRAFT,
            category=self.category,
            tags=["django"],
        )

        self.create_article(
            "Scheduled Article",
            status=Article.Status.SCHEDULED,
            category=self.category,
            tags=["django"],
        )

        response = self.client.get(
            self.url,
            {
                "category": self.category.id,
                "tag": "django",
            },
        )

        self.assertContains(response, published.title)
        self.assertNotContains(response, "Draft Article")
        self.assertNotContains(response, "Scheduled Article")

    def test_pagination_preserves_active_filters(self):
        for number in range(11):
            self.create_article(
                f"Article {number}",
                category=self.category,
                tags=["django"],
            )

        response = self.client.get(
            self.url,
            {
                "category": self.category.id,
                "tag": "django",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_paginated"])

        next_page_url = (
            f"?page=2&category={self.category.id}&tag=django"
        )

        self.assertContains(response, next_page_url, html=False)

        second_page = self.client.get(
            self.url,
            {
                "page": 2,
                "category": self.category.id,
                "tag": "django",
            },
        )

        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(len(second_page.context["articles"]), 1)