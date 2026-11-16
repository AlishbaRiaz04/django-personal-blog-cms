
import uuid
import logging

from django.db import DatabaseError

from .models import Article, PageView

logger=logging.getLogger(__name__)

class PageViewMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        try:
            self.record_page_view(request, response)
        except DatabaseError:
            logger.exception(
                "Failed to record page view."
            )

        return response

    def record_page_view(self, request, response):
        if request.method != "GET":
            return

        if response.status_code != 200:
            return

        if not response.get("Content-Type", "").startswith("text/html"):
            return

        match = request.resolver_match

        if match is None:
            return

        page_type = None
        article = None

        if match.url_name == "home":
            page_type = PageView.PageType.HOMEPAGE

        elif match.url_name == "article_detail":
            slug = match.kwargs.get("slug")

            article = Article.objects.filter(
                slug=slug,
                status=Article.Status.PUBLISHED,
                published_at__isnull=False,
            ).first()

            if article is None:
                return

            page_type = PageView.PageType.ARTICLE

        else:
            return

        visitor_id = request.session.get("visitor_id")

        if visitor_id is None:
            visitor_id = str(uuid.uuid4())
            request.session["visitor_id"] = visitor_id

        PageView.objects.create(
            visitor_id=visitor_id,
            page_type=page_type,
            article=article,
        )
