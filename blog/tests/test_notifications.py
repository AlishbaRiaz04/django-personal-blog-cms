from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from blog.models import(
    Article,
    AuthorProfile,
    NotificationDelivery,
    NotificationEvent,
)

User=get_user_model()

class NotificationEmailTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="subscriber",
            email="subscriber@example.com",
            password="testpass123",
        )
        self.author_user=User.objects.create_user(
            username="author",
            email="author@example.com",
            password="testpass123",
        )
        self.author=AuthorProfile.objects.create(
            user=self.author_user,
        )

        self.article = Article.objects.create(
            title="Notification Test Article",
            content="Test article content",
            author=self.author,
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
        )

        self.event = NotificationEvent.objects.create(
            article=self.article,
            article_title=self.article.title,
        )

        self.delivery = NotificationDelivery.objects.create(
            event=self.event,
            user=self.user,
            recipient_email=self.user.email,
        )

    @patch("blog.services.send_mail", return_value=1)
    def test_successful_email_marks_delivery_as_sent(self, mock_send_mail):
        from blog.services import send_notification_email

        result = send_notification_email(self.delivery)

        self.delivery.refresh_from_db()

        self.assertEqual(result, NotificationDelivery.Status.SENT)
        self.assertEqual(
            self.delivery.status,
            NotificationDelivery.Status.SENT,
        )
        self.assertEqual(self.delivery.attempt_count, 1)
        self.assertIsNotNone(self.delivery.sent_at)
        self.assertEqual(self.delivery.last_error, "")
        mock_send_mail.assert_called_once()

    @patch(
        "blog.services.send_mail",
        side_effect=Exception("Email server unavailable"),
    )
    def test_failed_email_records_failure(self, mock_send_mail):
        from blog.services import send_notification_email

        result = send_notification_email(self.delivery)

        self.delivery.refresh_from_db()

        self.assertEqual(result, NotificationDelivery.Status.FAILED)
        self.assertEqual(
            self.delivery.status,
            NotificationDelivery.Status.FAILED,
        )
        self.assertEqual(self.delivery.attempt_count, 1)
        self.assertIsNone(self.delivery.sent_at)
        self.assertEqual(
            self.delivery.last_error,
            "Email server unavailable",
        )
        self.assertIsNotNone(self.delivery.last_attempt_at)
        mock_send_mail.assert_called_once()

    @patch("blog.services.send_mail", return_value=1)
    def test_failed_email_is_not_retried_before_five_minutes(
        self, mock_send_mail
    ):
        from blog.services import process_pending_notifications

        self.delivery.status = NotificationDelivery.Status.FAILED
        self.delivery.attempt_count = 1
        self.delivery.last_attempt_at = timezone.now() - timedelta(minutes=4)
        self.delivery.save()

        processed_count = process_pending_notifications()

        self.delivery.refresh_from_db()

        self.assertEqual(processed_count, 0)
        self.assertEqual(self.delivery.attempt_count, 1)
        self.assertEqual(self.delivery.status, NotificationDelivery.Status.FAILED)
        mock_send_mail.assert_not_called()

    @patch("blog.services.send_mail", return_value=1)
    def test_failed_email_is_retried_after_five_minutes(
        self, mock_send_mail
    ):
        from blog.services import process_pending_notifications

        self.delivery.status = NotificationDelivery.Status.FAILED
        self.delivery.attempt_count = 1
        self.delivery.last_attempt_at = timezone.now() - timedelta(minutes=6)
        self.delivery.save()

        processed_count = process_pending_notifications()

        self.delivery.refresh_from_db()

        self.assertEqual(processed_count, 1)
        self.assertEqual(self.delivery.attempt_count, 2)
        self.assertEqual(self.delivery.status, NotificationDelivery.Status.SENT)
        self.assertIsNotNone(self.delivery.sent_at)
        mock_send_mail.assert_called_once()

    @patch("blog.services.send_mail", return_value=1)
    def test_delivery_is_not_retried_after_three_attempts(
        self, mock_send_mail
    ):
        from blog.services import process_pending_notifications

        self.delivery.status = NotificationDelivery.Status.FAILED
        self.delivery.attempt_count = 3
        self.delivery.last_attempt_at = timezone.now() - timedelta(minutes=10)
        self.delivery.save()

        processed_count = process_pending_notifications()

        self.delivery.refresh_from_db()

        self.assertEqual(processed_count, 0)
        self.assertEqual(self.delivery.attempt_count, 3)
        self.assertEqual(self.delivery.status, NotificationDelivery.Status.FAILED)
        mock_send_mail.assert_not_called()

    @patch("blog.services.send_mail", return_value=0)
    def test_zero_sent_count_marks_delivery_as_failed(self, mock_send_mail):
        from blog.services import send_notification_email

        result = send_notification_email(self.delivery)

        self.delivery.refresh_from_db()

        self.assertEqual(result, NotificationDelivery.Status.FAILED)
        self.assertEqual(self.delivery.status, NotificationDelivery.Status.FAILED)
        self.assertEqual(self.delivery.attempt_count, 1)
        self.assertIsNone(self.delivery.sent_at)
        self.assertIn("did not confirm delivery", self.delivery.last_error)
        mock_send_mail.assert_called_once()

    @patch("blog.services.send_mail", return_value=1)
    def test_sent_delivery_cannot_be_sent_again(
        self, mock_send_mail
    ):
        from blog.services import send_notification_email

        self.delivery.status = NotificationDelivery.Status.SENT
        self.delivery.attempt_count = 1
        self.delivery.sent_at = timezone.now()
        self.delivery.save()

        result = send_notification_email(self.delivery)

        self.delivery.refresh_from_db()

        self.assertEqual(result, NotificationDelivery.Status.SENT)
        self.assertEqual(self.delivery.attempt_count, 1)
        self.assertIsNotNone(self.delivery.sent_at)
        mock_send_mail.assert_not_called()

    @patch("blog.services.send_mail", return_value=1)
    def test_direct_email_call_respects_retry_delay(self, mock_send_mail):
        from blog.services import send_notification_email
        self.delivery.status = NotificationDelivery.Status.FAILED
        self.delivery.attempt_count=1
        self.delivery.last_attempt_at=timezone.now() - timedelta(minutes=4)
        self.delivery.save()

        result=send_notification_email(self.delivery)

        self.delivery.refresh_from_db()
        self.assertEqual(result, NotificationDelivery.Status.FAILED)
        self.assertEqual(self.delivery.attempt_count, 1)
        mock_send_mail.assert_not_called()
