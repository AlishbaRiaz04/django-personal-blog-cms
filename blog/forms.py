from django.forms import ModelForm
from django.utils.html import strip_tags
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Article

class ArticleForm(ModelForm):
    def __init__(self, *args, action=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.action=action

    class Meta:
        model = Article
        fields = ["title", "content", "categories", "tags", "scheduled_at"]
    def clean_content(self):
        content=self.cleaned_data["content"]
        cleaning=strip_tags(content).strip()
        if not cleaning:
            raise ValidationError("Content cannot be empty")

        return content

    def clean(self):
        cleaned_data = super().clean()

        scheduled_at = cleaned_data.get("scheduled_at")
        categories = cleaned_data.get("categories")

        if self.action in ["publish", "schedule"] and not categories:
            raise ValidationError("At least one category is required.")

        if self.action == "schedule":
            if not scheduled_at:
                raise ValidationError("A scheduled time is required.")

            if scheduled_at <= timezone.now():
                raise ValidationError("Scheduled time must be in the future.")

        return cleaned_data
