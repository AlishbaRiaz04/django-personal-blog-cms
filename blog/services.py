from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from django.db.models import Q
from django.urls import reverse

from .models import (
    Article,
    NotificationEvent,
    NotificationDelivery,
    Subscription,
)


def build_article_url(article):
    """Full web address of an article, e.g. https://myblog.com/article/my-post/

    Emails are read outside the website, so a relative link like
    /article/my-post/ would be useless. SITE_URL (in settings.py) is the
    part before the path.
    """
    path = reverse("article_detail", kwargs={"slug": article.slug})

    return settings.SITE_URL.rstrip("/") + path


@transaction.atomic
def create_article_notifications(article):
    if article.author is None:
        return 0

    event, _ = NotificationEvent.objects.get_or_create(
        article=article,
        defaults={
            "article_title":article.title,
        },
    )
    subscriptions=Subscription.objects.filter(
        author=article.author
    ).select_related("user")
    created_count=0

    for subscription in subscriptions:
        email=subscription.user.email.strip()

        if not email:
            continue

        _, created=NotificationDelivery.objects.get_or_create(
            event=event,
            recipient_email=email,
            defaults={
                "user":subscription.user,
            },
        )
        if created:
            created_count+=1

    return created_count

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
            create_article_notifications(article)

            published_count += 1

    return published_count

def send_notification_email(delivery):
    current_time=timezone.now()

    if delivery.status==NotificationDelivery.Status.SENT:
        return delivery.status
    if delivery.attempt_count>=3:
        return delivery.status

    if (
        delivery.status == NotificationDelivery.Status.FAILED
        and delivery.last_attempt_at is not None
        and delivery.last_attempt_at> current_time -timedelta(minutes=5)
    ):
        return delivery.status
    subject=f"New article: {delivery.event.article_title}"

    lines=[
        "A new article has been published!",
        "",
        f"Title: {delivery.event.article_title}",
    ]

    # The article may have been deleted since the notification was queued.
    article=delivery.event.article

    if article is not None:
        lines += [
            f"Read it here: {build_article_url(article)}",
            "",
            "You are receiving this because you subscribed to this author.",
            "To stop these emails, log in, open the article and click Unsubscribe.",
        ]

    message="\n".join(lines)
    try:
        sent_count=send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[delivery.recipient_email],
            fail_silently=False,
        )
        if sent_count !=1:
            raise RuntimeError("Email backend did not confirm delivery.")
        delivery.status=NotificationDelivery.Status.SENT
        delivery.sent_at=timezone.now()
        delivery.last_error=""

    except Exception as error:
        delivery.status=NotificationDelivery.Status.FAILED
        delivery.last_error=str(error)
        delivery.sent_at=None
    finally:
        delivery.attempt_count+=1
        delivery.last_attempt_at=timezone.now()
        delivery.save(update_fields=[
            "status",
            "sent_at",
            "last_error",
            "attempt_count",
            "last_attempt_at",
        ])

    return delivery.status

def process_pending_notifications():
    retry_time=timezone.now() - timedelta(minutes=5)

    deliveries=NotificationDelivery.objects.filter(
        attempt_count__lt=3
    ).filter(
        Q(status=NotificationDelivery.Status.PENDING)
        | Q(
            status=NotificationDelivery.Status.FAILED,
            last_attempt_at__lte=retry_time,
        )
        | Q(
            status=NotificationDelivery.Status.FAILED,
            last_attempt_at__isnull=True,
        )
    ).order_by("id")
    eligible_deliveries=list(deliveries)
    processed_count=0

    for delivery in eligible_deliveries:
        send_notification_email(delivery)
        processed_count+=1

    return processed_count
