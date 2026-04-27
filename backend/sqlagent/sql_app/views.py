import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .services import extract_full_schema, process_chat_message
from .helper.csvloader import csv_to_postgres
from .helper.dbconnection import create_session_schema
from .helper.vectorstore import create_collection_if_not_exists, store_table_embeddings

from .models import CSVUpload, CSVSession


create_collection_if_not_exists()
class CSVUploadView(APIView):
    def post(self, request):
        files = request.FILES.getlist('files')
        session_id = request.data.get('session_id')
        print(f"[upload] Received upload request for session_id={session_id}")
        print(f"[upload] Incoming files={[file.name for file in files]}")

        if not files or not session_id:
            print("[upload] Missing files or session_id")
            return Response(
                {'error': 'files and session_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        for file in files:
            if not file.name.endswith('.csv'):
                print(f"[upload] Rejected non-CSV file={file.name}")
                return Response(
                    {'error': f'{file.name} is not a CSV file'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # create PostgreSQL schema for this session
        create_session_schema(session_id)
        print(f"[upload] Ensured PostgreSQL schema exists for session_id={session_id}")

        session, _ = CSVSession.objects.get_or_create(
            session_id=session_id,
            defaults={'sqlite_path': ''}
        )
        print(f"[upload] Using CSVSession id={session.id} for session_id={session_id}")

        uploaded_tables = []
        table_summaries = []

        for file in files:
            table_name = os.path.splitext(file.name)[0].lower().replace(' ', '_')
            print(f"[upload] Processing file={file.name} as table={table_name}")

            upload = CSVUpload.objects.create(
                session=session,
                original_filename=file.name,
                csv_file=file,
                table_name=table_name,
            )
            print(f"[upload] Saved CSVUpload id={upload.id} path={upload.csv_file.path}")

            columns = csv_to_postgres(upload.csv_file.path, table_name, session_id)
            print(f"[upload] Loaded table={table_name} columns={columns}")
            uploaded_tables.append(table_name)
            table_summaries.append({
                'table_name': table_name,
                'columns': columns,
            })

        store_table_embeddings(session_id, table_summaries)
        print(f"[upload] Indexed embeddings for tables={uploaded_tables}")

        schema = extract_full_schema(session_id)
        print(f"[upload] Generated full schema preview for session_id={session_id}")

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
        print(f"[chat] Received chat request for session_id={session_id}")
        print(f"[chat] Question={question}")

        if not session_id or not question:
            print("[chat] Missing session_id or question")
            return Response(
                {'error': 'session_id and question are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = process_chat_message(session_id, question)
        print(f"[chat] Returning success={result.get('success', False)} for session_id={session_id}")

        if result.get('success'):
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
