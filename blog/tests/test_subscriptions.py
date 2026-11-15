
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from blog.models import Article, AuthorProfile, Subscription


User = get_user_model()


class SubscriptionTests(TestCase):

    def setUp(self):
        self.subscriber = User.objects.create_user(
            username="subscriber",
            password="testpass123",
        )

        self.other_user = User.objects.create_user(
            username="other",
            password="testpass123",
        )

        self.author_user = User.objects.create_user(
            username="author",
            password="testpass123",
        )

        self.author = AuthorProfile.objects.create(
            user=self.author_user,
        )

        self.article = Article.objects.create(
            title="Subscription Test Article",
            content="Article content",
            author=self.author,
            status=Article.Status.PUBLISHED,
        )

        self.subscribe_url = reverse(
            "subscribe_to_author",
            kwargs={"slug": self.article.slug},
        )

        self.unsubscribe_url = reverse(
            "unsubscribe_from_author",
            kwargs={"slug": self.article.slug},
        )

    def test_user_can_subscribe_to_author(self):
        self.client.force_login(self.subscriber)

        response = self.client.post(self.subscribe_url)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Subscription.objects.filter(
                user=self.subscriber,
                author=self.author,
            ).exists()
        )

    def test_duplicate_subscription_is_prevented(self):
        self.client.force_login(self.subscriber)

        self.client.post(self.subscribe_url)
        self.client.post(self.subscribe_url)

        self.assertEqual(
            Subscription.objects.filter(
                user=self.subscriber,
                author=self.author,
            ).count(),
            1,
        )

    def test_user_can_unsubscribe(self):
        Subscription.objects.create(
            user=self.subscriber,
            author=self.author,
        )

        self.client.force_login(self.subscriber)

        response = self.client.post(self.unsubscribe_url)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Subscription.objects.filter(
                user=self.subscriber,
                author=self.author,
            ).exists()
        )

    def test_user_cannot_delete_another_users_subscription(self):
        Subscription.objects.create(
            user=self.other_user,
            author=self.author,
        )

        self.client.force_login(self.subscriber)
        self.client.post(self.unsubscribe_url)

        self.assertTrue(
            Subscription.objects.filter(
                user=self.other_user,
                author=self.author,
            ).exists()
        )

    def test_anonymous_user_cannot_subscribe(self):
        response = self.client.post(self.subscribe_url)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Subscription.objects.exists())

    def test_get_request_cannot_subscribe(self):
        self.client.force_login(self.subscriber)

        response = self.client.get(self.subscribe_url)

        self.assertEqual(response.status_code, 405)
        self.assertFalse(Subscription.objects.exists())

    def test_author_cannot_subscribe_to_own_blog(self):
        self.client.force_login(self.author_user)

        self.client.post(self.subscribe_url)

        self.assertFalse(
            Subscription.objects.filter(
                user=self.author_user,
                author=self.author,
            ).exists()
        )
