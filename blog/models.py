from tkinter.constants import CASCADE

from django.db import models
from django.db.models import SET_NULL
from django.db.models.fields import TextField, CharField
from django.utils.text import slugify
from django.conf import settings
from taggit.managers import TaggableManager




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
