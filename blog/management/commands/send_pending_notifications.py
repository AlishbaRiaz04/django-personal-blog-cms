from django.core.management.base import BaseCommand
from blog.services import process_pending_notifications

class Command(BaseCommand):
    help="Send pending article notification emails"

    def handle(self, *args, **options):
        processed_count=process_pending_notifications()

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {processed_count} notification(s)."
            )
        )