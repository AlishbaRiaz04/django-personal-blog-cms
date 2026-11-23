from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from blog.models import (
    Article,
    AuthorProfile,
    NotificationDelivery,
    Subscription,
)
from blog.services import (
    build_article_url,
    create_article_notifications,
    process_pending_notifications,
)


class NotificationEmailTestCase(TestCase):
    def setUp(self):
        author_user = User.objects.create_user(
            username="writer", password="x-pass-12345"
        )
        self.profile = AuthorProfile.objects.create(user=author_user)
        self.reader = User.objects.create_user(
            username="reader",
            email="reader@example.com",
            password="x-pass-12345",
        )
        Subscription.objects.create(user=self.reader, author=self.profile)

        self.article = Article.objects.create(
            title="Hello Subscribers",
            content="<p>Body</p>",
            author=self.profile,
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        self.article_path = reverse(
            "article_detail", kwargs={"slug": self.article.slug}
        )

    def send_queued_email(self):
        create_article_notifications(self.article)
        process_pending_notifications()
        return mail.outbox[0]


@override_settings(SITE_URL="https://myblog.example")
class NotificationEmailContentTests(NotificationEmailTestCase):
    def test_email_contains_a_full_link_to_the_article(self):
        email = self.send_queued_email()

        self.assertIn(
            f"https://myblog.example{self.article_path}", email.body
        )

    def test_email_contains_the_article_title(self):
        email = self.send_queued_email()

        self.assertIn("Title: Hello Subscribers", email.body)
        self.assertEqual(email.subject, "New article: Hello Subscribers")

    def test_email_explains_how_to_unsubscribe(self):
        email = self.send_queued_email()

        self.assertIn("Unsubscribe", email.body)

    def test_email_is_sent_to_the_subscriber_only(self):
        email = self.send_queued_email()

        self.assertEqual(email.to, ["reader@example.com"])

    def test_delivery_is_marked_as_sent(self):
        self.send_queued_email()

        delivery = NotificationDelivery.objects.get()
        self.assertEqual(delivery.status, NotificationDelivery.Status.SENT)

    def test_email_still_sends_if_the_article_was_deleted(self):
        create_article_notifications(self.article)
        self.article.delete()

        process_pending_notifications()

        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("Read it here", mail.outbox[0].body)
        delivery = NotificationDelivery.objects.get()
        self.assertEqual(delivery.status, NotificationDelivery.Status.SENT)


class BuildArticleUrlTests(NotificationEmailTestCase):
    @override_settings(SITE_URL="https://myblog.example/")
    def test_trailing_slash_in_site_url_is_not_doubled(self):
        self.assertEqual(
            build_article_url(self.article),
            f"https://myblog.example{self.article_path}",
        )

    @override_settings(SITE_URL="http://127.0.0.1:8000")
    def test_local_development_address_works(self):
        self.assertEqual(
            build_article_url(self.article),
            f"http://127.0.0.1:8000{self.article_path}",
        )
