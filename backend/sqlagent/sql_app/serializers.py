from rest_framework import serializers
from .models import CSVUpload

class CSVUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = CSVUpload
        fields = ['id', 'session_id', 'original_filename', 'table_name', 'uploaded_at']