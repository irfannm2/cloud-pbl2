import sqlite3

# Connect to the database
conn = sqlite3.connect('container_times.db')

# Create a cursor object to execute SQL statements
cursor = conn.cursor()

# Execute the INSERT statement to add a new user
customQuery = "DROP TABLE users"
cursor.execute(customQuery)

# Commit the changes to the database
conn.commit()

# Close the database connection
conn.close()
