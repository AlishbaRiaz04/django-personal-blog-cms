from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from blog.forms import ArticleForm
from blog.models import Article, AuthorProfile, Category
from blog.sanitizers import sanitize_html


class SanitizeHtmlTests(SimpleTestCase):
    """Tests for the sanitize_html() function on its own."""

    def test_script_tag_and_its_code_are_removed(self):
        result = sanitize_html("<p>Hi</p><script>alert(1)</script>")

        self.assertEqual(result, "<p>Hi</p>")
        self.assertNotIn("alert", result)

    def test_event_handler_attribute_is_removed(self):
        result = sanitize_html('<img src="https://example.com/a.png" onerror="alert(1)">')

        self.assertNotIn("onerror", result)
        self.assertIn("https://example.com/a.png", result)

    def test_javascript_link_is_removed(self):
        result = sanitize_html('<a href="javascript:alert(1)">click</a>')

        self.assertNotIn("javascript", result)
        self.assertIn("click", result)

    def test_data_url_is_removed(self):
        result = sanitize_html('<a href="data:text/html,<script>alert(1)</script>">x</a>')

        self.assertNotIn("data:", result)

    def test_iframe_is_removed(self):
        result = sanitize_html('<iframe src="https://evil.example.com"></iframe>')

        self.assertNotIn("iframe", result)

    def test_style_attribute_is_removed(self):
        result = sanitize_html('<p style="position:fixed;top:0">text</p>')

        self.assertEqual(result, "<p>text</p>")

    def test_onclick_is_removed_but_link_is_kept(self):
        result = sanitize_html('<a href="https://example.com" onclick="evil()">ok</a>')

        self.assertNotIn("onclick", result)
        self.assertIn('href="https://example.com"', result)

    def test_external_links_get_noopener_noreferrer(self):
        result = sanitize_html('<a href="https://example.com">ok</a>')

        self.assertIn('rel="noopener noreferrer"', result)

    def test_normal_formatting_is_kept(self):
        html = (
            "<h2>Title</h2>"
            "<p>Some <strong>bold</strong>, <em>italic</em> and <u>underlined</u> text.</p>"
            "<ul><li>one</li><li>two</li></ul>"
            "<blockquote>quote</blockquote>"
        )

        self.assertEqual(sanitize_html(html), html)

    def test_plain_text_is_unchanged(self):
        self.assertEqual(sanitize_html("Just some text"), "Just some text")

    def test_empty_values_become_empty_string(self):
        self.assertEqual(sanitize_html(""), "")
        self.assertEqual(sanitize_html(None), "")

    def test_cleaning_twice_gives_the_same_result(self):
        once = sanitize_html('<p>Hi <a href="https://example.com">there</a></p><script>x</script>')

        self.assertEqual(sanitize_html(once), once)


class ArticleModelSanitizingTests(TestCase):
    def test_saving_an_article_cleans_its_content(self):
        article = Article.objects.create(
            title="Model test",
            content="<p>Safe</p><script>alert(1)</script>",
        )

        article.refresh_from_db()
        self.assertEqual(article.content, "<p>Safe</p>")


class ArticleFormSanitizingTests(TestCase):
    def build_form(self, content):
        category = Category.objects.create(name="Dev")
        return ArticleForm(
            data={
                "title": "T",
                "content": content,
                "categories": [category.pk],
            },
            action="publish",
        )

    def test_form_returns_cleaned_content(self):
        form = self.build_form("<p>Hi</p><script>alert(1)</script>")

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["content"], "<p>Hi</p>")

    def test_content_made_only_of_a_script_is_rejected_as_empty(self):
        form = self.build_form("<script>alert(1)</script>")

        self.assertFalse(form.is_valid())
        self.assertIn("content", form.errors)


class StoredXssEndToEndTests(TestCase):
    """Walk the whole path: author submits an attack, visitor views the page."""

    def setUp(self):
        user = User.objects.create_user(username="writer", password="x-pass-12345")
        AuthorProfile.objects.create(user=user)
        self.category = Category.objects.create(name="Dev")
        self.client.force_login(user)

    def test_script_in_a_published_article_never_reaches_visitors(self):
        self.client.post(
            reverse("article_create"),
            {
                "title": "Attack",
                "content": "<p>Hello</p><script>alert('xss')</script>"
                           '<img src="https://example.com/x.png" onerror="alert(2)">',
                "categories": [self.category.pk],
                "action": "publish",
            },
        )
        article = Article.objects.get(title="Attack")

        self.client.logout()
        page = self.client.get(
            reverse("article_detail", kwargs={"slug": article.slug})
        ).content.decode()

        self.assertIn("<p>Hello</p>", page)
        self.assertNotIn("<script>alert", page)
        self.assertNotIn("onerror", page)
