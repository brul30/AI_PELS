from django.contrib import admin
from .models import Word

# Register your models here.

class WordAdmin(admin.ModelAdmin):
    list_display = ('word', 'phonetic', 'laymans')  # Fields to display in list view
    search_fields = ('word',)  # Fields that can be searched

# Register your models here.
admin.site.register(Word, WordAdmin)