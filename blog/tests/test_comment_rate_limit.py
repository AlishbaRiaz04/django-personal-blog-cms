from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from blog.models import Article, AuthorProfile, Comment

User = get_user_model()


@override_settings(COMMENT_RATE_LIMIT=3, COMMENT_RATE_WINDOW_SECONDS=600)
class CommentRateLimitTests(TestCase):

    def setUp(self):
        author = User.objects.create_user(username="author", password="pass12345")
        profile = AuthorProfile.objects.create(user=author)
        self.article = Article.objects.create(
            title="Rate limit article",
            content="Body",
            author=profile,
            status=Article.Status.PUBLISHED,
        )
        self.url = reverse("article_detail", kwargs={"slug": self.article.slug})

        self.reader = User.objects.create_user(username="reader", password="pass12345")
        self.other_reader = User.objects.create_user(username="other", password="pass12345")
        self.client.login(username="reader", password="pass12345")

    def post_comment(self, text="Hello"):
        return self.client.post(self.url, {"content": text})

    def test_comments_under_the_limit_are_accepted(self):
        for i in range(3):
            response = self.post_comment(f"Comment {i}")
            self.assertEqual(response.status_code, 302)

        self.assertEqual(Comment.objects.filter(user=self.reader).count(), 3)

    def test_comment_over_the_limit_is_rejected_with_429(self):
        for i in range(3):
            self.post_comment(f"Comment {i}")

        response = self.post_comment("One too many")

        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "commenting too quickly", status_code=429)
        self.assertFalse(Comment.objects.filter(content="One too many").exists())

    def test_old_comments_do_not_count_towards_the_limit(self):
        for i in range(3):
            comment = Comment.objects.create(
                article=self.article, user=self.reader, content=f"Old {i}"
            )
            Comment.objects.filter(pk=comment.pk).update(
                created_at=timezone.now() - timedelta(seconds=601)
            )

        response = self.post_comment("Fresh comment")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Comment.objects.filter(content="Fresh comment").exists())

    def test_limit_is_per_user(self):
        for i in range(3):
            self.post_comment(f"Comment {i}")

        self.client.logout()
        self.client.login(username="other", password="pass12345")

        response = self.post_comment("Different user")

        self.assertEqual(response.status_code, 302)
