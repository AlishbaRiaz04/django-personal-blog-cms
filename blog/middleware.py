
import re
import uuid
import logging

from django.db import DatabaseError

from .models import Article, PageView

logger=logging.getLogger(__name__)

VISITOR_COOKIE_NAME = "visitor_id"
VISITOR_COOKIE_MAX_AGE = 60 * 60 * 24 * 365

BOT_USER_AGENT_PATTERN = re.compile(
    r"bot|crawl|spider|slurp|archiver|fetcher|preview|monitor|"
    r"headlesschrome|curl/|wget/|python-requests|python-urllib|"
    r"go-http-client|java/|libwww|httpclient|okhttp|"
    r"facebookexternalhit|lighthouse",
    re.IGNORECASE,
)


def is_bot(request):
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    return bool(BOT_USER_AGENT_PATTERN.search(user_agent))

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

        if is_bot(request):
            return

        visitor_id = request.COOKIES.get(VISITOR_COOKIE_NAME)

        if not visitor_id or len(visitor_id) > 64:
            visitor_id = str(uuid.uuid4())

        PageView.objects.create(
            visitor_id=visitor_id,
            page_type=page_type,
            article=article,
        )

        if request.COOKIES.get(VISITOR_COOKIE_NAME) != visitor_id:
            response.set_cookie(
                VISITOR_COOKIE_NAME,
                visitor_id,
                max_age=VISITOR_COOKIE_MAX_AGE,
                httponly=True,
                samesite="Lax",
                secure=request.is_secure(),
            )
