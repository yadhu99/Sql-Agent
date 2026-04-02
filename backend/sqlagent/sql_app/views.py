import os
import uuid
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import process_chat_message,extract_full_schema
from .helper.csvloader import csv_to_postgres
from .helper.dbconnection import create_session_schema

from .models import CSVUpload, CSVSession



class CSVUploadView(APIView):
    def post(self, request):
        files = request.FILES.getlist('files')
        session_id = request.data.get('session_id')

        if not files or not session_id:
            return Response(
                {'error': 'files and session_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        for file in files:
            if not file.name.endswith('.csv'):
                return Response(
                    {'error': f'{file.name} is not a CSV file'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # create PostgreSQL schema for this session
        create_session_schema(session_id)

        session, _ = CSVSession.objects.get_or_create(
            session_id=session_id,
            defaults={'sqlite_path': ''}
        )

        uploaded_tables = []

        for file in files:
            table_name = os.path.splitext(file.name)[0].lower().replace(' ', '_')

            upload = CSVUpload.objects.create(
                session=session,
                original_filename=file.name,
                csv_file=file,
                table_name=table_name,
            )

            csv_to_postgres(upload.csv_file.path, table_name, session_id)
            uploaded_tables.append(table_name)

        schema = extract_full_schema(session_id)

        return Response({
            'session_id': session_id,
            'tables': uploaded_tables,
            'schema': schema,
            'message': f'{len(files)} CSV(s) uploaded and processed successfully'
        }, status=status.HTTP_201_CREATED)
    

class ChatView(APIView):
    def post(self, request):
        session_id = request.data.get('session_id')
        question = request.data.get('question')

        if not session_id or not question:
            return Response(
                {'error': 'session_id and question are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = process_chat_message(session_id, question)

        if result.get('success'):
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)