from django.urls import path
from . import views
from .views import CommentModerationView

urlpatterns=[
    path('', views.ArticleListView.as_view(), name='home'),

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
]