from django import forms
from django.forms import ModelForm
from django.utils.html import strip_tags
from django.core.exceptions import ValidationError
from django.utils import timezone
from ckeditor.widgets import CKEditorWidget
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Article
from .models import Comment
from .sanitizers import sanitize_html


class ArticleForm(ModelForm):
    def __init__(self, *args, action=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.action=action

        if self.instance.pk and self.instance.status ==Article.Status.PUBLISHED:
            del self.fields["scheduled_at"]

    class Meta:
        model = Article
        fields = ["title", "content", "categories", "tags", "scheduled_at"]

        widgets={
            "content": CKEditorWidget(),
        }
    def clean_content(self):
        content=sanitize_html(self.cleaned_data["content"])
        cleaning=strip_tags(content).strip()
        if not cleaning:
            raise ValidationError("Content cannot be empty")

        return content

    def clean(self):
        cleaned_data = super().clean()

        scheduled_at = cleaned_data.get("scheduled_at")
        categories = cleaned_data.get("categories")

        if self.action not in ["draft", "publish", "schedule", "edit"]:
            raise ValidationError("Invalid article action.")

        if self.action in ["publish", "schedule"] and not categories:
            raise ValidationError("At least one category is required.")

        if self.action == "schedule":
            if not scheduled_at:
                raise ValidationError("A scheduled time is required.")

            if scheduled_at <= timezone.now():
                raise ValidationError("Scheduled time must be in the future.")
        if self.action == "edit":
            if (
                    self.instance.status in [
                Article.Status.PUBLISHED,
                Article.Status.SCHEDULED
            ]
                    and not categories
            ):
                raise ValidationError("At least one category is required.")

            if self.instance.status == Article.Status.SCHEDULED:
                if not scheduled_at:
                    raise ValidationError("A scheduled time is required.")

                if scheduled_at <= timezone.now():
                    raise ValidationError("Scheduled time must be in the future.")
        return cleaned_data

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Write your comment..."
            })
        }

    def clean_content(self):
        content=self.cleaned_data["content"]

        if not content.strip():
            raise ValidationError("Comment cannot be empty")

        return content

class SignUpForm(UserCreationForm):
    email=forms.EmailField(required=True)
    class Meta(UserCreationForm.Meta):
        model=User
        fields=("username", "email")

    def clean_email(self):
        email=self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email
