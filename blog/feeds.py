from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils.feedgenerator import Atom1Feed

from .models import Article

class LatestArticlesFeed(Feed):
    title="Blog Updates"
    link = "/"
    description = "Latest published articles from blog."

    def items(self):
        return (
            Article.objects.filter(
                status=Article.Status.PUBLISHED,
                published_at__isnull=False
            ).select_related("author").order_by("-published_at", "title")[:20]

        )
    def item_title(self, item):
        return item.title
    def item_description(self, item):
        return item.content
    def item_link(self, item):
        return reverse(
            "article_detail",
            kwargs={"slug": item.slug}
        )

    def item_pubdate(self, item):
        return item.published_at

    def item_updateddate(self, item):
        return item.updated_at

    def item_author_name(self, item):
        if item.author:
            return str(item.author)
        return "Unknown Author"


class LatestArticlesAtomFeed(LatestArticlesFeed):
    feed_type = Atom1Feed
    subtitle=LatestArticlesFeed.description
