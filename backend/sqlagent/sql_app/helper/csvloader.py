import os
import pandas as pd
from sqlalchemy import create_engine


def csv_to_postgres(csv_file_path: str, table_name: str, session_id: str):
    df = pd.read_csv(csv_file_path)
    df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]

    schema_name = f"session_{session_id.replace('-', '_')}"
    engine = create_engine(os.getenv('DATABASE_URL'))

    df.to_sql(
        table_name,
        engine,
        schema=schema_name,
        if_exists='replace',
        index=False
    )

    engine.dispose()
    return df.columns.tolist()