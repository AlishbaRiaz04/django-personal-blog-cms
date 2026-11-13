
from django.db import transaction
from django.utils import timezone

from .models import (
    Article,
    NotificationEvent,
    NotificationDelivery,
    Subscription,
)


def publish_due_articles():
    current_time = timezone.now()

    due_article_ids = Article.objects.filter(
        status=Article.Status.SCHEDULED,
        scheduled_at__lte=current_time,
    ).values_list("id", flat=True)

    published_count = 0

    for article_id in due_article_ids:
        with transaction.atomic():
            try:
                article = Article.objects.select_for_update().get(
                    id=article_id
                )
            except Article.DoesNotExist:
                continue

            # Recheck because another process may have handled it.
            if (
                article.status != Article.Status.SCHEDULED
                or article.scheduled_at is None
                or article.scheduled_at > current_time
            ):
                continue

            article.status = Article.Status.PUBLISHED

            # Preserve the original publication time if this is a
            # previously published article being republished.
            if not article.published_at:
                article.published_at = current_time

            article.scheduled_at = None

            article.save(update_fields=[
                "status",
                "published_at",
                "scheduled_at",
                "updated_at",
            ])

            event, created = NotificationEvent.objects.get_or_create(
                article=article,
                defaults={
                    "article_title": article.title,
                },
            )

            # Prepare notification deliveries for this author's subscribers.
            if article.author:
                subscriptions = Subscription.objects.filter(
                    author=article.author
                ).select_related("user")

                for subscription in subscriptions:
                    email = subscription.user.email.strip()

                    if not email:
                        continue

                    NotificationDelivery.objects.get_or_create(
                        event=event,
                        recipient_email=email,
                        defaults={
                            "user": subscription.user,
                        },
                    )

            published_count += 1

    return published_count
