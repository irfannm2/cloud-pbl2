import sqlite3

conn = sqlite3.connect('container_times.db')
cursor = conn.cursor()

table_name = 'billings'
query = f"DROP TABLE IF EXISTS {table_name};"

cursor.execute(query)
conn.commit()

cursor.close()
conn.close()
