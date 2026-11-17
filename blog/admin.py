from django.contrib import admin

from .models import Article, AuthorProfile, Category, Comment

admin.site.register(Article)
admin.site.register(AuthorProfile)
admin.site.register(Category)
admin.site.register(Comment)

