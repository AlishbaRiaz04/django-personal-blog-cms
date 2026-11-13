
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView
from django.utils import timezone
from django.views.generic import DetailView, UpdateView, ListView, DeleteView
from django.urls import reverse, reverse_lazy
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect

from .forms import ArticleForm, CommentForm
from .models import Article, AuthorProfile,  Comment


class ArticleListView(ListView):
    model=Article
    template_name = "blog/article_list.html"
    context_object_name = "articles"
    paginate_by = 10

    def get_queryset(self):
        return Article.objects.filter(
            status=Article.Status.PUBLISHED
        ).order_by("-created_at", "title")

class ArticleCreateView(LoginRequiredMixin, CreateView):
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

        # Assign the logged-in user as the author
        author, created = AuthorProfile.objects.get_or_create(
            user=self.request.user
        )
        article.author = author

        # Determine the article's state
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

        return super().form_valid(form)

    """def get_success_url(self):
        return reverse(
            "article_detial",
            kwargs={"slug": self.object.slug}
        )"""

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
        kwargs["action"] = "edit"
        return kwargs

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