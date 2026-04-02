from django.db import models
import uuid


class CSVSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.CharField(max_length=255, unique=True)
    sqlite_path = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.session_id


class CSVUpload(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(CSVSession, on_delete=models.CASCADE, related_name='uploads')
    original_filename = models.CharField(max_length=255)
    csv_file = models.FileField(upload_to='csv_uploads/')
    table_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.original_filename} ({self.session.session_id})"


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    session = models.ForeignKey(CSVSession , on_delete=models.CASCADE , related_name="messages")
    role = models.CharField(max_length=20 , choices=ROLE_CHOICES)
    Content = models.TextField()
    sql_query = models.TextField(null=True , blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        db_table = 'sql_app_chatmessages'  

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"