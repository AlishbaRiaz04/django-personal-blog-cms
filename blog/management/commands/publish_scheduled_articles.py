from django.core.management.base import BaseCommand
from blog.services import publish_due_articles

class Command(BaseCommand):
    help="Publish articles whose scheduled time has arrived"

    def handle(self, *args, **options):
        published_count=publish_due_articles()

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully published {published_count} article(s)."
            )
        )