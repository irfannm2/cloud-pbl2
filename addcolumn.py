import sqlite3

conn = sqlite3.connect('container_times.db')
cursor = conn.cursor()

table_name = 'containerLogs'
query = f"ALTER TABLE  {table_name} DROP COLUMN sequence_digit INTEGER;"

cursor.execute(query)
conn.commit()

cursor.close()
conn.close()

