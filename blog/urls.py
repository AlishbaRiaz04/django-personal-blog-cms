from django.urls import path
from . import views
from .views import CommentModerationView
from .views import moderate_comment
from .feeds import LatestArticlesFeed, LatestArticlesAtomFeed

urlpatterns=[
    path('', views.ArticleListView.as_view(), name='home'),
    path(
        'account/signup/',
        views.SignUpView.as_view(),
        name="signup"
    ),
    path(
        'article/create/',
        views.ArticleCreateView.as_view(),
        name='article_create'
    ),
    path(
        'article/<slug:slug>/',
        views.ArticleDetailView.as_view(),
        name='article_detail'
    ),
    path(
        'article/<slug:slug>/edit/',
        views.ArticleUpdateView.as_view(),
        name='article_update'
    ),
    path(
        "dashboard/",
        views.AuthorDashboardView.as_view(),
        name="author_dashboard"
    ),
    path(
        "article/<slug:slug>/delete/",
        views.ArticleDeleteView.as_view(),
        name="article_delete"
    ),
    path(
        "comments/moderation/",
        CommentModerationView.as_view(),
        name="comment_moderation",
    ),
    path(
        "comments/<int:comment_id>/<str:action>/",
        moderate_comment,
        name="moderate_comment",
    ),
    path(
        "article/<slug:slug>/subscribe/",
        views.subscribe_to_author,
        name="subscribe_to_author",
    ),
    path(
        "article/<slug:slug>/unsubscribe/",
        views.unsubscribe_from_author,
        name="unsubscribe_from_author",
    ),
    path(
        "feeds/rss/",
        LatestArticlesFeed(),
        name="rss_feed",
    ),
    path(
        "feeds/atom/",
        LatestArticlesAtomFeed(),
        name="atom_feed",
    ),
]
