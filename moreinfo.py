import sqlite3

def display(database, table_name, container_id):
    # Connect to the SQLite database
    conn = sqlite3.connect(database)

    # Create a cursor to execute SQL queries
    cursor = conn.cursor()

    # Query to fetch rows for a specific container ID from a table
    query = f"SELECT * FROM {table_name} WHERE container_id = ?;"

    # Execute the query with the container ID parameter
    cursor.execute(query, (container_id,))

    # Fetch all rows
    rows = cursor.fetchall()

    # Check if any rows were found
    if rows:
        # Get the column headers
        headers = [description[0] for description in cursor.description]

        # Generate the HTML table
        html_table = "<table class='min-w-full divide-y divide-gray-200'>"
        html_table += "<thead><tr>"
        for header in headers:
            html_table += f"<th class='px-6 py-3 bg-gray-100 text-left text-xs leading-4 font-medium text-gray-500 uppercase tracking-wider'>{header}</th>"
        html_table += "</tr></thead><tbody class='bg-white divide-y divide-gray-200'>"

        # Generate the table rows
        for row in rows:
            html_table += "<tr>"
            for value in row:
                html_table += f"<td class='px-6 py-4 whitespace-no-wrap'>{value}</td>"
            html_table += "</tr>"
        html_table += "</tbody></table>"

        # Close the cursor and the connection
        cursor.close()
        conn.close()

        return html_table
    else:
        return "No rows found for the container ID in the table."