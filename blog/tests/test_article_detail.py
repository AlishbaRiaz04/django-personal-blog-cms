from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from blog.models import Article


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