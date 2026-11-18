
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import redirect_to_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, UpdateView, ListView, DeleteView
from django.urls import reverse, reverse_lazy
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render, get_object_or_404

from .forms import ArticleForm, CommentForm, SignUpForm
from .models import Article, AuthorProfile,  Comment, Subscription, Category
from taggit.models import Tag
from .services import create_article_notifications

ARTICLE_MESSAGES = {
    "draft": "Saved as a draft.",
    "publish": "Article published.",
    "schedule": "Article scheduled.",
    "edit": "Changes saved.",
}


class SignUpView(CreateView):

    form_class=SignUpForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("home")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response=super().form_valid(form)
        login(self.request, self.object)
        return response




class ArticleListView(ListView):
    model = Article
    template_name = "blog/article_list.html"
    context_object_name = "articles"
    paginate_by = 10

    def get_queryset(self):
        queryset = Article.objects.filter(
            status=Article.Status.PUBLISHED,
            published_at__isnull=False,
        )

        category_id = self.request.GET.get("category")
        tag_slug = self.request.GET.get("tag")

        if category_id and category_id.isdigit():
            queryset = queryset.filter(categories__id=category_id)

        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)

        return queryset.distinct().order_by("-published_at", "title")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["categories"] = Category.objects.all()
        context["selected_category"] = self.request.GET.get("category", "")
        context["selected_tag"] = self.request.GET.get("tag", "")
        context["tags"] = Tag.objects.all()

        return context

class ArticleCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model= Article
    form_class=ArticleForm
    template_name = "blog/article_form.html"

    def get_form_kwargs(self):
        kwargs=super().get_form_kwargs()

        if self.request.method == "POST":
            kwargs["action"] =  self.request.POST.get("action")

        return kwargs


    def form_valid(self, form):
        article = form.save(commit=False)
        article.author = self.request.user.author_profile
        action = form.action

        if action == "draft":
            article.status = Article.Status.DRAFT
            article.scheduled_at = None

        elif action == "publish":
            article.status = Article.Status.PUBLISHED
            article.scheduled_at = None

            if not article.published_at:
                article.published_at = timezone.now()

        elif action == "schedule":
            article.status = Article.Status.SCHEDULED

        response=super().form_valid(form)

        if action =="publish":
            create_article_notifications(self.object)

        response=super().form_valid(form)

        if action =="publish":
            create_article_notifications(self.object)

        messages.success(self.request, ARTICLE_MESSAGES[action])

        return response

        return response

    def test_func(self):
        return AuthorProfile.objects.filter(
            user=self.request.user
        ).exists()

    def post(self, request, *args, **kwargs):
        action=request.POST.get("action")

        if action not in ["draft", "publish", "schedule"]:
            return HttpResponseBadRequest("Invalid article action.")

        return super().post(request, *args, **kwargs)

    success_url = reverse_lazy("home")

class ArticleDetailView(DetailView):
    model=Article
    template_name = "blog/article_detail.html"
    context_object_name = "article"

    def get_queryset(self):
        return Article.objects.filter(
            status=Article.Status.PUBLISHED
        )
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["comment_form"] = CommentForm()
        context["approved_comments"] = self.object.comments.filter(
            moderation_status=Comment.ModerationStatus.APPROVED
        ).order_by("created_at")

        context['is_subscribed']=False

        if self.request.user.is_authenticated and self.object.author:
            context["is_subscribed"] = Subscription.objects.filter(
                user=self.request.user,
                author=self.object.author
            ).exists()

        return context
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        self.object = self.get_object()
        form = CommentForm(request.POST)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.article = self.object
            comment.user = request.user
            comment.moderation_status = Comment.ModerationStatus.PENDING
            comment.save()

            return redirect(request.path)

        context = self.get_context_data()
        context["comment_form"] = form

        return self.render_to_response(context, status=400)

class ArticleUpdateView(LoginRequiredMixin, UpdateView):
    model = Article
    form_class = ArticleForm
    template_name = "blog/article_edit.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    success_url = reverse_lazy("home")

    def get_queryset(self):
        return Article.objects.filter(
            author__user=self.request.user
        )
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.method =="POST":
            kwargs["action"] = self.request.POST.get("action")
        else:
            kwargs["action"] = "edit"
        return kwargs

    def post(self, request, *args, **kwargs):
        action=request.POST.get("action")

        if action not in ["edit", "draft", "publish", "schedule"]:
            return HttpResponseBadRequest("Invalid article action.")
        return super().post(request, *args, **kwargs)
    def form_valid(self, form):
        was_published = (
            self.object.status == Article.Status.PUBLISHED
        )

        article=form.save(commit=False)
        action=form.action

        if action == "draft":
            article.status=Article.Status.DRAFT
            article.scheduled_at=None
            article.published_at=None

        elif action=="publish":
            article.status=Article.Status.PUBLISHED
            article.scheduled_at=None

            if not was_published or not article.published_at:
                article.published_at=timezone.now()
        elif action == "schedule":
            article.status = Article.Status.SCHEDULED
            article.published_at=None

        elif action == "edit":
            if article.status != Article.Status.SCHEDULED:
                article.scheduled_at=None

        response = super().form_valid(form)

        if action == "publish" and not was_published:
            create_article_notifications(self.object)

        messages.success(self.request, ARTICLE_MESSAGES[action])
        return response

class AuthorDashboardView(LoginRequiredMixin, ListView):
    model = Article
    template_name = "blog/author_dashboard.html"
    context_object_name = "articles"
    paginate_by = 10

    def get_queryset(self):
        queryset = Article.objects.filter(
            author__user=self.request.user
        ).order_by("-updated_at")

        status=self.request.GET.get("status")

        valid_statuses=[
            choice[0] for choice in Article.Status.choices
        ]
        if status in valid_statuses:
            queryset=queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context["selected_status"] = self.request.GET.get("status", "all")
        context["status_choices"] = Article.Status.choices

        return context

class ArticleDeleteView(LoginRequiredMixin, DeleteView):
    model = Article
    template_name = "blog/article_confirm_delete.html"
    success_url = reverse_lazy("author_dashboard")

    def get_queryset(self):
        return Article.objects.filter(
            author__user=self.request.user
        )

class CommentModerationView(LoginRequiredMixin, ListView):
    model = Comment
    template_name = "blog/comment_moderation.html"
    context_object_name = "comments"

    def get_queryset(self):
        queryset = Comment.objects.filter(
            moderation_status = Comment.ModerationStatus.PENDING
        ).select_related(
            "article",
            "article__author",
            "user",
        ).order_by("-created_at")

        if self.request.user.is_staff:
            return queryset

        return queryset.filter(
            article__author__user=self.request.user
        )
@login_required
@require_POST
def moderate_comment(request, comment_id, action):
    comment = get_object_or_404(Comment, id=comment_id)

    if not request.user.is_staff:
        if (
            comment.article.author is None
            or comment.article.author.user_id != request.user.id
        ):
            raise PermissionDenied

    if action == "approve":
        comment.moderation_status = Comment.ModerationStatus.APPROVED

    elif action == "reject":
        comment.moderation_status = Comment.ModerationStatus.REJECTED
    else:
        raise PermissionDenied

    comment.save(update_fields=["moderation_status", "updated_at"])
    return redirect("comment_moderation")

@login_required
@require_POST
def subscribe_to_author(request, slug):
    article=get_object_or_404(
        Article,
        slug=slug,
        status=Article.Status.PUBLISHED,
    )

    if article.author and article.author.user_id != request.user.id:
        Subscription.objects.get_or_create(
            user=request.user,
            author=article.author,
        )

    return redirect("article_detail", slug=article.slug)
@login_required
@require_POST
def unsubscribe_from_author(request, slug):
    article=get_object_or_404(
        Article,
        slug=slug,
        status=Article.Status.PUBLISHED,
    )

    if article.author and article.author.user_id != request.user.id:
        Subscription.objects.filter(
            user=request.user,
            author=article.author,
        ).delete()
    return redirect("article_detail", slug=article.slug)
