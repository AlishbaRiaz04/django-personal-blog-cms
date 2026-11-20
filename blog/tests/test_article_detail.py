from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from blog.models import Article, AuthorProfile


class ArticleDetailPageTests(TestCase):
    def setUp(self):
        self.article = Article.objects.create(
            title="Layout Test Article",
            content="<p>Body text</p>",
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        self.response = self.client.get(
            reverse("article_detail", kwargs={"slug": self.article.slug})
        )

    def create_author(self, username, is_staff=False):
        User=get_user_model()

        user=User.objects.create_user(
            username=username,
            password="testpass123",
            is_staff=is_staff,
        )
        profile=AuthorProfile.objects.create(user=user)

        return user, profile

    def test_author_can_view_their_own_draft(self):
        author, profile = self.create_author("alice")

        article = Article.objects.create(
            title="Alice Draft",
            content="<p>Unpublished content</p>",
            status=Article.Status.DRAFT,
            author=profile,
        )

        self.client.force_login(author)

        response = self.client.get(
            reverse("article_detail", kwargs={"slug": article.slug})
        )

        self.assertEqual(response.status_code, 200)

    def test_author_cannot_view_another_authors_draft(self):
        alice, alice_profile =self.create_author("alice")
        bob, bob_profile=self.create_author("bob")

        article=Article.objects.create(
            title="Bob Draft",
            content="<p>Private content</p>",
            status=Article.Status.DRAFT,
            author=bob_profile,
        )
        self.client.force_login(alice)
        response=self.client.get(
            reverse("article_detail", kwargs={"slug": article.slug})
        )
        self.assertEqual(response.status_code, 404)

    def test_author_can_view_their_own_scheduled_article(self):
        author, profile = self.create_author("alice")

        article = Article.objects.create(
            title="Alice Scheduled Article",
            content="<p>Scheduled content</p>",
            status=Article.Status.SCHEDULED,
            scheduled_at=timezone.now() + timedelta(days=1),
            author=profile,
        )

        self.client.force_login(author)

        response = self.client.get(
            reverse("article_detail", kwargs={"slug": article.slug})
        )

        self.assertEqual(response.status_code, 200)

    def test_staff_can_view_another_authors_draft(self):
        bob, bob_profile = self.create_author("bob")
        staff, staff_profile = self.create_author(
            "admin",
            is_staff=True,
        )

        article = Article.objects.create(
            title="Bob Private Draft",
            content="<p>Private content</p>",
            status=Article.Status.DRAFT,
            author=bob_profile,
        )

        self.client.force_login(staff)

        response = self.client.get(
            reverse("article_detail", kwargs={"slug": article.slug})
        )
        self.assertEqual(response.status_code, 200)
    def test_page_extends_the_base_template(self):
        self.assertTemplateUsed(self.response, "blog/base.html")

    def test_page_loads_the_stylesheet_and_navigation(self):
        self.assertContains(self.response, "blog/css/style.css")
        self.assertContains(self.response, 'class="main-nav"')

    def test_page_title_contains_the_article_title(self):
        self.assertContains(
            self.response, "<title>Layout Test Article | My Blog</title>"
        )

    def test_article_body_is_shown(self):
        self.assertContains(self.response, "<p>Body text</p>")

    def test_anonymous_login_links_return_to_the_article(self):
        article_url = reverse("article_detail", kwargs={"slug": self.article.slug})

        self.assertContains(self.response, f"{reverse('login')}?next={article_url}")