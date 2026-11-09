from tkinter.constants import CASCADE

from django.db import models
from django.db.models import SET_NULL, PROTECT
from django.db.models.fields import TextField, CharField
from django.utils.text import slugify
from django.conf import settings
from taggit.managers import TaggableManager
from django.db.models import Q




class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT="draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        PUBLISHED= "published", "Published"

    title=models.CharField(max_length=200)
    content=models.TextField()
    status=models.CharField(
        max_length=20,
        choices = Status.choices,
        default=Status.DRAFT,
    )
    author=models.ForeignKey(
        "AuthorProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )
    categories = models.ManyToManyField(
        "Category",
        blank=True,
        related_name="articles",
    )

    created_at= models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at=models.DateTimeField(null=True, blank=True)
    scheduled_at=models.DateTimeField(null=True, blank=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    tags = TaggableManager(blank=True)

    def generate_unique_slug(self):

        base_slug = slugify(self.title) or "article"
        candidate=base_slug
        counter=2

        while Article.objects.filter(slug=candidate).exists():
            candidate = f"{base_slug}-{counter}"
            counter+=1
        return candidate

    def save(self, *args, **kwargs):
        if self._state.adding and not self.slug:
            self.slug = self.generate_unique_slug()

        super().save(*args, **kwargs)

class AuthorProfile(models.Model):
    user=models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="author_profile"
    )
    display_name=models.CharField(max_length=100, blank=True)
    biography=models.TextField(max_length=500, blank=True)

    def __str__(self):
        return self.display_name or self.user.username

class Category(models.Model):
    name=models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Comment(models.Model):
    class ModerationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    article=models.ForeignKey(
        "Article",
        on_delete=models.CASCADE,
        related_name="comments",

    )
    user=models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comments",
    )
    content=models.TextField()
    moderation_status=models.CharField(
        max_length=20,
        choices=ModerationStatus.choices,
        default=ModerationStatus.PENDING,
    )
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def __str__(self):
        username = self.user.username if self.user else "Anonymous"
        return f"Comment on '{self.article.title}' by {username}"

class Subscription(models.Model):
    user=models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    author=models.ForeignKey(
        "AuthorProfile",
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )
    class Meta:
        constraints=[
            models.UniqueConstraint(
                fields=["user", "author"],
                name="unique_user_author_subscription",
            )
        ]
    def __str__(self):
        return f"{self.user} subscribes to {self.author}"

class NotificationEvent(models.Model):
    article=models.OneToOneField(
        "Article",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_event",

    )
    article_title=models.CharField(max_length=200)
    created_at=models.DateTimeField(auto_now_add=True)

class NotificationDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING="pending", "Pending"
        SENT="sent", "Sent"
        FAILED="failed", "Failed"

    event=models.ForeignKey(
        "NotificationEvent",
        on_delete=models.PROTECT,
        related_name="deliveries",
    )
    user=models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_deliveries",
    )
    recipient_email=models.EmailField()
    status=models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    attempt_count=models.PositiveIntegerField(default=0)

    sent_at=models.DateTimeField(
        null=True,
        blank=True,
    )
    last_attempt_at=models.DateTimeField(
        null=True,
        blank=True,
    )
    class Meta:
        constraints=[
            models.UniqueConstraint(
                fields=["event", "recipient_email"],
                name="unique_event_recipient_delivery",
            )
        ]
    last_error=models.TextField(blank=True)
    def __str__(self):
        return f"Delivery to {self.recipient_email}"

class PageView(models.Model):
    class PageType(models.TextChoices):
        HOMEPAGE= "homepage", "Homepage"
        ARTICLE= "article", "Article"
        CATEGORY= "category", "Category"
        Author_PROFILE="author_profile", "Author_Profile"
    visitor_id=models.CharField(
        max_length=64,
    )
    article=models.ForeignKey(
        "Article",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="page_views",
    )
    page_type=models.CharField(
        max_length=20,
        choices=PageType.choices,
    )
    viewed_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                        Q(page_type="article", article__isnull=False)
                        | Q(
                    page_type__in=["homepage", "category", "author_profile"],
                    article__isnull=True,
                )
                ),
                name="valid_pageview_article_relationship",
            )
        ]