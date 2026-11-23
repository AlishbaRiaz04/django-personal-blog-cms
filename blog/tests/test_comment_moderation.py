from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from blog.models import Article, AuthorProfile, Comment


User = get_user_model()


class CommentModerationTests(TestCase):

    def setUp(self):
        # Create two authors
        self.author_one = User.objects.create_user(
            username="author_one",
            password="testpass123"
        )

        self.author_two = User.objects.create_user(
            username="author_two",
            password="testpass123"
        )

        self.profile_one = AuthorProfile.objects.create(
            user=self.author_one
        )

        self.profile_two = AuthorProfile.objects.create(
            user=self.author_two
        )

        # Create an article for each author
        self.article_one = Article.objects.create(
            title="Author One Article",
            content="Article content",
            author=self.profile_one,
            status=Article.Status.PUBLISHED
        )

        self.article_two = Article.objects.create(
            title="Author Two Article",
            content="Article content",
            author=self.profile_two,
            status=Article.Status.PUBLISHED
        )

        # Create pending comments
        self.comment_one = Comment.objects.create(
            article=self.article_one,
            user=self.author_two,
            content="Comment on author one article"
        )

        self.comment_two = Comment.objects.create(
            article=self.article_two,
            user=self.author_one,
            content="Comment on author two article"
        )

        self.moderation_url = reverse("comment_moderation")

    def action_url(self, comment, action):
        return reverse(
            "moderate_comment",
            kwargs={
                "comment_id": comment.id,
                "action": action
            }
        )

    def test_author_can_approve_comment_on_own_article(self):
        self.client.force_login(self.author_one)

        response = self.client.post(
            self.action_url(self.comment_one, "approve")
        )

        self.comment_one.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.comment_one.moderation_status,
            Comment.ModerationStatus.APPROVED
        )

    def test_author_can_reject_comment_on_own_article(self):
        self.client.force_login(self.author_one)

        response = self.client.post(
            self.action_url(self.comment_one, "reject")
        )

        self.comment_one.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.comment_one.moderation_status,
            Comment.ModerationStatus.REJECTED
        )

    def test_author_cannot_moderate_another_authors_comment(self):
        self.client.force_login(self.author_one)

        response = self.client.post(
            self.action_url(self.comment_two, "approve")
        )

        self.comment_two.refresh_from_db()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            self.comment_two.moderation_status,
            Comment.ModerationStatus.PENDING
        )

    def test_staff_can_moderate_any_comment(self):
        staff_user = User.objects.create_user(
            username="staff_user",
            password="testpass123",
            is_staff=True
        )

        self.client.force_login(staff_user)

        response = self.client.post(
            self.action_url(self.comment_two, "approve")
        )

        self.comment_two.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.comment_two.moderation_status,
            Comment.ModerationStatus.APPROVED
        )

    def test_anonymous_user_cannot_moderate_comment(self):
        response = self.client.post(
            self.action_url(self.comment_one, "approve")
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

        self.comment_one.refresh_from_db()

        self.assertEqual(
            self.comment_one.moderation_status,
            Comment.ModerationStatus.PENDING
        )

    def test_moderation_action_rejects_get_request(self):
        self.client.force_login(self.author_one)

        response = self.client.get(
            self.action_url(self.comment_one, "approve")
        )

        self.assertEqual(response.status_code, 405)

    def test_author_sees_only_own_pending_comments(self):
        self.client.force_login(self.author_one)

        response = self.client.get(self.moderation_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Comment on author one article"
        )
        self.assertNotContains(
            response,
            "Comment on author two article"
        )

    def test_submitted_comment_is_pending(self):
        self.client.force_login(self.author_two)

        response = self.client.post(
            reverse(
                "article_detail",
                kwargs={"slug": self.article_one.slug}
            ),
            {"content": "This is my new comment"}
        )

        comment = Comment.objects.get(
            article=self.article_one,
            content="This is my new comment"
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            comment.moderation_status,
            Comment.ModerationStatus.PENDING
        )

    def test_only_approved_comments_are_visible(self):
        Comment.objects.create(
            article=self.article_one,
            user=self.author_two,
            content="This comment should be visible",
            moderation_status=Comment.ModerationStatus.APPROVED
        )

        Comment.objects.create(
            article=self.article_one,
            user=self.author_two,
            content="This comment should stay hidden",
            moderation_status=Comment.ModerationStatus.REJECTED
        )

        response = self.client.get(
            reverse(
                "article_detail",
                kwargs={"slug": self.article_one.slug}
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "This comment should be visible"
        )

        self.assertNotContains(
            response,
            "Comment on author one article"
        )

        self.assertNotContains(
            response,
            "This comment should stay hidden"
        )

    def test_anonymous_user_cannot_submit_comment(self):
        initial_count = Comment.objects.filter(
            article=self.article_one
        ).count()

        response = self.client.post(
            reverse(
                "article_detail",
                kwargs={"slug": self.article_one.slug}
            ),
            {"content": "Anonymous comment"}
        )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            Comment.objects.filter(
                article=self.article_one
            ).count(),
            initial_count
        )
