
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone

from blog.models import(
    Article,
    AuthorProfile,
    Category,
    Subscription,
    NotificationEvent,
    NotificationDelivery,
)

class ArticleCreationPermissionTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(
            username="testuser",
            password="testpassword123",
        )
        self.url=reverse("article_create")

    def test_regular_user_cannot_access_article_creation_page(self):
        self.client.login(
            username="testuser",
            password="testpassword123",
        )
        response=self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_regular_user_cannot_submit_article_creation_request(self):
        self.client.login(
            username="testuser",
            password="testpassword123",
        )

        response=self.client.post(
            self.url,
            {"action": "draft"}

        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Article.objects.count(), 0)

    def test_approved_author_can_access_article_creation_page(self):
        AuthorProfile.objects.create(user=self.user)

        self.client.login(
            username="testuser",
            password="testpassword123",
        )
        response=self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_approved_author_can_create_draft_without_category(self):
        AuthorProfile.objects.create(user=self.user)
        self.client.login(
            username="testuser",
            password="testpassword123",
        )

        response=self.client.post(
            self.url,
            {
                "title": "My Draft",
                "content": "Draft content",
                "action": "draft",
            },
        )
        self.assertEqual(response.status_code, 302)

        article=Article.objects.get(title="My Draft")
        self.assertEqual(article.status, Article.Status.DRAFT)
        self.assertIsNone(article.published_at)
        self.assertIsNone(article.scheduled_at)

    def test_approved_author_can_publish_article(self):
        AuthorProfile.objects.create(user=self.user)
        category = Category.objects.create(name="Development")

        self.client.login(
            username="testuser",
            password="testpassword123",
        )

        response = self.client.post(
            self.url,
                {
                "title": "My Published Article",
                "content": "Published content",
                "categories": [category.pk],
                "action": "publish",
            },
        )

        self.assertEqual(response.status_code, 302)

        article = Article.objects.get(title="My Published Article")
        self.assertEqual(article.status, Article.Status.PUBLISHED)
        self.assertIsNotNone(article.published_at)
        self.assertIsNone(article.scheduled_at)

    def test_approved_author_can_schedule_article(self):
        AuthorProfile.objects.create(user=self.user)
        category = Category.objects.create(name="Development")

        future_date = (
                timezone.now() + timedelta(days=2)
        ).strftime("%Y-%m-%dT%H:%M")

        self.client.login(
            username="testuser",
            password="testpassword123",
            )

        response = self.client.post(
            self.url,
            {
                "title": "My Scheduled Article",
                "content": "Scheduled content",
                "categories": [category.pk],
                "scheduled_at": future_date,
                "action": "schedule",
            },
        )

        self.assertEqual(response.status_code, 302)

        article = Article.objects.get(title="My Scheduled Article")
        self.assertEqual(article.status, Article.Status.SCHEDULED)
        self.assertIsNotNone(article.scheduled_at)
        self.assertIsNone(article.published_at)

    def test_publishing_article_creates_subscriber_notifications(self):
        author = AuthorProfile.objects.create(user=self.user)

        subscriber = User.objects.create_user(
            username="subscriber",
            email="subscriber@example.com",
            password="testpassword123",
        )

        Subscription.objects.create(
            user=subscriber,
            author=author,
        )

        category = Category.objects.create(name="Development")

        self.client.login(
            username="testuser",
            password="testpassword123",
        )

        response = self.client.post(
            self.url,
            {
                "title": "Notification Test",
                "content": "This article should notify subscribers.",
                "categories": [category.pk],
                "action": "publish",
            },
        )

        self.assertEqual(response.status_code, 302)

        article = Article.objects.get(title="Notification Test")

        self.assertTrue(
            NotificationEvent.objects.filter(article=article).exists()
        )

        self.assertTrue(
            NotificationDelivery.objects.filter(
                event__article=article,
                recipient_email="subscriber@example.com",
                status=NotificationDelivery.Status.PENDING,
            ).exists()
        )

    def test_editing_published_article_does_not_create_duplicate_notifications(self):
        author = AuthorProfile.objects.create(user=self.user)
        category = Category.objects.create(name="Development")

        subscriber = User.objects.create_user(
            username="subscriber",
            email="subscriber@example.com",
            password="testpassword123",
        )

        Subscription.objects.create(
            user=subscriber,
            author=author,
        )

        article = Article.objects.create(
            title="Original Title",
            content="Original content",
            author=author,
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        article.categories.add(category)

        event = NotificationEvent.objects.create(
            article=article,
            article_title=article.title,
        )

        NotificationDelivery.objects.create(
            event=event,
            user=subscriber,
            recipient_email=subscriber.email,
        )

        self.client.login(
            username="testuser",
            password="testpassword123",
        )

        url = reverse(
            "article_update",
            kwargs={"slug": article.slug},
        )

        response = self.client.post(
            url,
            {
                "title": "Updated Title",
                "content": "Updated content",
                "categories": [category.pk],
                "action": "edit",
            },
        )

        self.assertEqual(response.status_code, 302)

        article.refresh_from_db()

        self.assertEqual(article.title, "Updated Title")
        self.assertEqual(article.status, Article.Status.PUBLISHED)

        self.assertEqual(
            NotificationEvent.objects.filter(article=article).count(),
            1,
        )

        self.assertEqual(
            NotificationDelivery.objects.filter(event=event).count(),
            1,
        )

    def test_publishing_existing_draft_creates_subscriber_notifications(self):
        author = AuthorProfile.objects.create(user=self.user)
        category = Category.objects.create(name="Development")

        subscriber = User.objects.create_user(
            username="subscriber",
            email="subscriber@example.com",
            password="testpassword123",
        )

        Subscription.objects.create(
            user=subscriber,
            author=author,
        )

        article = Article.objects.create(
            title="My Draft",
            content="Draft content",
            author=author,
            status=Article.Status.DRAFT,
        )

        self.client.login(
            username="testuser",
            password="testpassword123",
        )

        url = reverse(
            "article_update",
            kwargs={"slug": article.slug},
        )

        response = self.client.post(
            url,
            {
                "title": article.title,
                "content": article.content,
                "categories": [category.pk],
                "action": "publish",
            },
        )

        self.assertEqual(response.status_code, 302)

        article.refresh_from_db()

        self.assertEqual(article.status, Article.Status.PUBLISHED)
        self.assertIsNotNone(article.published_at)

        event = NotificationEvent.objects.get(article=article)

        self.assertTrue(
            NotificationDelivery.objects.filter(
                event=event,
                recipient_email=subscriber.email,
                status=NotificationDelivery.Status.PENDING,
            ).exists()
        )


