from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from blog.models import (
    Article,
    AuthorProfile,
    Category,
    NotificationEvent,
    Subscription,
)


class EditWorkflowTestCase(TestCase):
    """Shared setup: one approved author, one category, a few helpers."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="writer", password="x-pass-12345"
        )
        self.profile = AuthorProfile.objects.create(user=self.user)
        self.category = Category.objects.create(name="Development")
        self.client.force_login(self.user)

    def make_article(self, status=Article.Status.DRAFT, **extra):
        fields = {
            "title": "My Article",
            "content": "<p>Body</p>",
            "author": self.profile,
            "status": status,
        }
        fields.update(extra)
        article = Article.objects.create(**fields)
        article.categories.add(self.category)
        return article

    def edit_url(self, article):
        return reverse("article_update", kwargs={"slug": article.slug})

    def submit(self, article, action, follow=False, **extra):
        data = {
            "title": article.title,
            "content": "<p>Body</p>",
            "categories": [self.category.pk],
            "action": action,
        }
        data.update(extra)
        return self.client.post(self.edit_url(article), data, follow=follow)

    def future(self, days=2):
        moment = timezone.now() + timedelta(days=days)
        return moment.strftime("%Y-%m-%dT%H:%M")


class PublishFromEditPageTests(EditWorkflowTestCase):
    def test_draft_can_be_published(self):
        article = self.make_article()

        response = self.submit(article, "publish")

        self.assertEqual(response.status_code, 302)
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.PUBLISHED)
        self.assertIsNotNone(article.published_at)
        self.assertIsNone(article.scheduled_at)

    def test_published_article_is_visible_to_visitors(self):
        article = self.make_article()
        self.submit(article, "publish")

        self.client.logout()
        response = self.client.get(
            reverse("article_detail", kwargs={"slug": article.slug})
        )

        self.assertEqual(response.status_code, 200)

    def test_article_without_a_category_cannot_be_published(self):
        article = self.make_article()

        response = self.submit(article, "publish", categories=[])

        self.assertEqual(response.status_code, 200)
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.DRAFT)

    def test_publishing_notifies_subscribers(self):
        reader = User.objects.create_user(
            username="reader",
            email="reader@example.com",
            password="x-pass-12345",
        )

        Subscription.objects.create(
            user=reader,
            author=self.profile,
        )

        article = self.make_article()

        self.submit(article, "publish")

        self.assertEqual(NotificationEvent.objects.count(), 1)

class ScheduleFromEditPageTests(EditWorkflowTestCase):
    def test_draft_can_be_scheduled(self):
        article = self.make_article()

        self.submit(article, "schedule", scheduled_at=self.future())

        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.SCHEDULED)
        self.assertIsNotNone(article.scheduled_at)
        self.assertIsNone(article.published_at)

    def test_scheduling_without_a_time_is_rejected(self):
        article = self.make_article()

        response = self.submit(article, "schedule")

        self.assertEqual(response.status_code, 200)
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.DRAFT)

    def test_scheduling_in_the_past_is_rejected(self):
        article = self.make_article()
        past = (timezone.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")

        response = self.submit(article, "schedule", scheduled_at=past)

        self.assertEqual(response.status_code, 200)
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.DRAFT)

    def test_scheduled_article_can_be_published_now(self):
        article = self.make_article(
            Article.Status.SCHEDULED,
            scheduled_at=timezone.now() + timedelta(days=1),
        )

        self.submit(article, "publish")

        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.PUBLISHED)
        self.assertIsNone(article.scheduled_at)
        self.assertIsNotNone(article.published_at)

    def test_scheduled_article_can_be_moved_back_to_draft(self):
        article = self.make_article(
            Article.Status.SCHEDULED,
            scheduled_at=timezone.now() + timedelta(days=1),
        )

        self.submit(article, "draft")

        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.DRAFT)
        self.assertIsNone(article.scheduled_at)

    def test_saving_changes_keeps_the_article_scheduled(self):
        article = self.make_article(
            Article.Status.SCHEDULED,
            scheduled_at=timezone.now() + timedelta(days=1),
        )

        self.submit(article, "edit", scheduled_at=self.future(days=5))

        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.SCHEDULED)
        self.assertGreater(
            article.scheduled_at, timezone.now() + timedelta(days=4)
        )

    def test_scheduling_does_not_notify_subscribers_yet(self):
        reader = User.objects.create_user(
            username="reader", email="reader@example.com", password="x-pass-12345"
        )
        Subscription.objects.create(user=reader, author=self.profile)
        article = self.make_article()

        self.submit(article, "schedule", scheduled_at=self.future())

        self.assertEqual(NotificationEvent.objects.count(), 0)

    def test_schedule_article_cannnot_be_rescheduled_to_past(self):
        original_time=timezone.now() + timedelta(days=2)

        article=self.make_article(
            Article.Status.SCHEDULED,
            scheduled_at=original_time,
        )
        past_time=(
            timezone.now() - timedelta(days=1)
        ).strftime("%Y-%m-%dT%H:%M")
        response=self.submit(
            article,
            "edit",
            scheduled_at=past_time,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Scheduled time must be in the future.",
        )

        article.refresh_from_db()

        self.assertEqual(article.status, Article.Status.SCHEDULED)
        self.assertEqual(article.scheduled_at, original_time)



class UnpublishTests(EditWorkflowTestCase):
    def setUp(self):
        super().setUp()
        self.article = self.make_article(
            Article.Status.PUBLISHED, published_at=timezone.now()
        )

    def test_published_article_can_be_unpublished(self):
        self.submit(self.article, "draft")

        self.article.refresh_from_db()
        self.assertEqual(self.article.status, Article.Status.DRAFT)
        self.assertIsNone(self.article.published_at)

    def test_unpublished_article_disappears_for_visitors(self):
        self.submit(self.article, "draft")

        self.client.logout()
        response = self.client.get(
            reverse("article_detail", kwargs={"slug": self.article.slug})
        )

        self.assertEqual(response.status_code, 404)

    def test_saving_changes_keeps_the_article_published(self):
        self.submit(self.article, "edit", title="Renamed")

        self.article.refresh_from_db()
        self.assertEqual(self.article.status, Article.Status.PUBLISHED)
        self.assertEqual(self.article.title, "Renamed")


class StrayScheduleTimeTests(EditWorkflowTestCase):
    """A schedule time only means something on a scheduled article."""

    def test_draft_does_not_keep_a_typed_schedule_time(self):
        article = self.make_article()

        self.submit(article, "edit", scheduled_at=self.future())

        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.DRAFT)
        self.assertIsNone(article.scheduled_at)

    def test_published_page_has_no_schedule_field(self):
        article = self.make_article(Article.Status.PUBLISHED)

        response = self.client.get(self.edit_url(article))

        self.assertNotIn("scheduled_at", response.context["form"].fields)


class EditPageButtonTests(EditWorkflowTestCase):
    def test_draft_page_offers_save_publish_and_schedule(self):
        article = self.make_article()

        response = self.client.get(self.edit_url(article))

        for value in ["draft", "publish", "schedule"]:
            self.assertContains(response, f'value="{value}"')

    def test_scheduled_page_offers_publish_now_and_move_to_draft(self):
        article = self.make_article(
            Article.Status.SCHEDULED,
            scheduled_at=timezone.now() + timedelta(days=1),
        )

        response = self.client.get(self.edit_url(article))

        self.assertContains(response, "Publish Now")
        self.assertContains(response, "Move to Draft")

    def test_published_page_offers_unpublish_but_not_schedule(self):
        article = self.make_article(Article.Status.PUBLISHED)

        response = self.client.get(self.edit_url(article))

        self.assertContains(response, "Unpublish")
        self.assertNotContains(response, 'value="schedule"')
        self.assertNotContains(response, "Publish Now")


class FeedbackMessageTests(EditWorkflowTestCase):
    def test_each_action_shows_a_message(self):
        expected = {
            "draft": "Saved as a draft.",
            "publish": "Article published.",
            "schedule": "Article scheduled.",
        }

        for action, text in expected.items():
            with self.subTest(action=action):
                article = self.make_article(title=f"Article {action}")
                extra = {"scheduled_at": self.future()} if action == "schedule" else {}

                response = self.submit(article, action, follow=True, **extra)

                self.assertContains(response, text)

    def test_saving_changes_shows_a_message(self):
        article = self.make_article(Article.Status.PUBLISHED)

        response = self.submit(article, "edit", follow=True)

        self.assertContains(response, "Changes saved.")


class EditSafetyTests(EditWorkflowTestCase):
    def test_unknown_action_is_rejected(self):
        article = self.make_article()

        response = self.submit(article, "delete-everything")

        self.assertEqual(response.status_code, 400)

    def test_author_cannot_edit_or_publish_someone_elses_article(self):
        other_user = User.objects.create_user(
            username="other", password="x-pass-12345"
        )
        other_profile = AuthorProfile.objects.create(user=other_user)
        article = self.make_article(author=other_profile)

        response = self.submit(article, "publish")

        self.assertEqual(response.status_code, 404)
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.DRAFT)

    def test_script_added_while_editing_is_removed(self):
        article = self.make_article()

        self.submit(
            article, "publish",
            content="<p>Hi</p><script>alert(1)</script>",
        )

        article.refresh_from_db()
        self.assertEqual(article.content, "<p>Hi</p>")
