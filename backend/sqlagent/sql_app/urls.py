from django.urls import path
from .views import CSVUploadView , ChatView

urlpatterns = [
    path('upload/csv/', CSVUploadView.as_view(), name='csv-upload'),
     path('chat/', ChatView.as_view(), name='chat'),
]