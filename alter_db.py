import sqlite3
from pathlib import Path

db_path = Path("/home/gaboe/proyectos/promptGPT/prompt_gpt.db")
if not db_path.exists():
    print("DB no existe, se creará por SQLAlchemy luego")
else:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("ALTER TABLE chats ADD COLUMN usuario_id INTEGER NOT NULL DEFAULT 1;")
        conn.commit()
        print("Columna usuario_id añadida a la tabla chats.")
    except sqlite3.OperationalError as e:
        print(f"Error o ya existe: {e}")
    conn.close()
