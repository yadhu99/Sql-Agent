import os
import pandas as pd
from sqlalchemy import create_engine


def csv_to_postgres(csv_file_path: str, table_name: str, session_id: str):
    print(f"[csvloader] Reading CSV path={csv_file_path} for table={table_name}")
    df = pd.read_csv(csv_file_path)
    df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
    print(
        f"[csvloader] Normalized columns for table={table_name}: {df.columns.tolist()}"
    )
    print(f"[csvloader] Row count for table={table_name}: {len(df)}")

    schema_name = f"session_{session_id.replace('-', '_')}"
    engine = create_engine(os.getenv('DATABASE_URL'))
    print(f"[csvloader] Writing table={table_name} into schema={schema_name}")

    df.to_sql(
        table_name,
        engine,
        schema=schema_name,
        if_exists='replace',
        index=False
    )

    engine.dispose()
    print(f"[csvloader] Completed write for table={table_name}")
    return df.columns.tolist()
