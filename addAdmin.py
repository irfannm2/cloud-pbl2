import sqlite3
from main import generate_user_id

# Connect to the database
conn = sqlite3.connect('container_times.db')

# Create a cursor object to execute SQL statements
cursor = conn.cursor()

# Assign values for insertion
user_id = generate_user_id()
username = 'logi'
password = 'L0g1t3ch'
is_admin = False

# Execute the INSERT statement to add a new user
addAdmin = "INSERT INTO users (user_id, username, password, is_admin) VALUES (?, ?, ?, ?)"
cursor.execute(addAdmin, (user_id, username, password, is_admin))

# Commit the changes to the database
conn.commit()

# Close the database connection
conn.close()
