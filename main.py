import sqlite3
from flask import Flask, render_template, request, flash, redirect, url_for, session
from functools import wraps
import uuid
import re
import docker
import docker.errors
import os
import secrets
import datetime
from displayDB import display_table_values
import random
import socket

# Connect to the database
conn = sqlite3.connect('container_times.db')

# Containers Table
conn.execute('''CREATE TABLE IF NOT EXISTS containers
                 (container_id TEXT,
                  container_name TEXT,
                  user_id TEXT,
                  image_name TEXT,
                  FOREIGN KEY (user_id) REFERENCES users(user_id))''')

# Users Table
conn.execute('''CREATE TABLE IF NOT EXISTS users
                (user_id TEXT,
                username TEXT,
                password TEXT,
                PRIMARY KEY (user_id))''')

# ContainerLogs Table
conn.execute('''CREATE TABLE IF NOT EXISTS containerLogs 
                (sequence_digit INTEGER,
                container_id TEXT,
                user_id TEXT,
                start_time TEXT,
                stop_time TEXT,
                total_time FLOAT,
                total_cost FLOAT,
                FOREIGN KEY (container_id) REFERENCES containers(container_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                PRIMARY KEY (container_id, sequence_digit))''')

# Close the database connection
conn.close()


# Define the Flask application obejct
app = Flask(__name__, static_url_path='/static')
client = docker.from_env()
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(16)

# SIGN UP
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Validate the form inputs
        # Check Username availability
        if not is_username_available(username):
            flash('Username is already taken.', 'danger')
            return redirect(url_for('signup'))
        
        # Password Complexity
        if not is_password_complex(password):
            flash('Password must contain at least 8 characters, including at least one uppercase letter, one lowercase letter, and one digit.', 'danger')
            return redirect(url_for('signup'))

        # Store the user details in the database (you may need to modify the database schema)
        # Connect to the database
        conn = sqlite3.connect('container_times.db')

        # Insert the user information into the database
        conn.execute('''INSERT INTO users
                (user_id, username, password) 
                VALUES (?, ?, ?)''', (generate_user_id(), username, password))

        # Commit the changes and close the database connection
        conn.commit()
        conn.close()

        # Redirect the user to a success page or perform additional actions as needed
        flash('Successfully registered!', 'success')
        return redirect(url_for('login'))

    # If it's a GET request, render the signup form
    return render_template('signup.html')

def generate_user_id():
    # Generate a UUID (Universally Unique Identifier) as the user ID
    user_id = str(uuid.uuid4())
    return user_id

def is_username_available(username):
    conn = sqlite3.connect('container_times.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
    count = cursor.fetchone()[0]
    conn.close()
    return count == 0

def is_password_complex(password):
    # Check password complexity using regular expressions
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    return True

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    username = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Validate the form inputs
        if not is_valid_credentials(username, password):
            flash('Invalid username or password. Please try again.', 'danger')
            return redirect(url_for('login'))

        user_id = get_user_id(username, password)
        # Store the user_id in the session
        session['user_id'] = user_id

        return redirect(url_for('landing'))
    
    # If it's a GET request, render the login form
    return render_template('login.html')

def is_valid_credentials(username, password):
    conn = sqlite3.connect('container_times.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = ? AND password = ?", (username, password))
    count = cursor.fetchone()[0]
    conn.close()
    return count == 1

def get_user_id(username, password):
    conn = sqlite3.connect('container_times.db')
    cursor = conn.cursor()

    # Query the users table to fetch the user_id based on the username and password
    query = "SELECT user_id FROM users WHERE username = ? AND password = ?"
    cursor.execute(query, (username, password))

    # Fetch the user_id from the result
    result = cursor.fetchone()

    # Close the cursor and the connection
    cursor.close()
    conn.close()

    if result:
        return result[0]  # Return the user_id
    else:
        return None  # User not found or invalid credentials

def get_username(user_id):
    conn = sqlite3.connect('container_times.db')
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]
    else:
        return None

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:
            # User is not logged in, redirect to login page
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped_view

# ALL THE PAGES THAT REQUIRED LOGIN
@app.route('/')
def landing():
    return render_template('/landing.html')

# go to create container form page
@app.route('/create-cont')
@login_required
def create_cont():
    if 'user_id' in session:
        user_id = session['user_id']
        username = get_username(user_id)
    else:
        return redirect(url_for('login'))
    return render_template('/create-cont.html', username=username)

@app.route('/dockbox')
@login_required
def dockbox():
    list_img = []
    if 'user_id' in session:
        user_id = session['user_id']
        username = get_username(user_id)
    else:
        return redirect(url_for('login'))
    
    for image in client.images.list():
        image_info = {
            'image_name': image.tags[0] if image.tags else '',
            'created': image.attrs['Created'],
            'size': image.attrs['Size'],
        }
        list_img.append(image_info)
                
        # Limit the containers to 3
        if len(list_img) >= 3:
            break
        

    containers = []
    start_time = session.pop('start_time', None)  # Retrieve and remove start_time from the session
    
    # Connect to the database
    conn = sqlite3.connect('container_times.db')
    cursor = conn.cursor()
    
    # Retrieve containers made by the logged-in user
    cursor.execute("SELECT * FROM containers WHERE user_id = ?", (user_id,))
    container_logs = cursor.fetchall()
    
    for container in client.containers.list(all=True):
        cpu_percent, memory_percent = get_container_stats(container)
        container_info = {
            'container_id': container.short_id,
            'container_name': container.name,
            'image': container.image.tags[0] if container.image.tags else '',
            'status': container.status,
            'cpu_percent': cpu_percent if container.status == 'running' else None,
            'memory_percent': memory_percent if container.status == 'running' else None,
            'start_time': start_time if container.id == session.get('container_id') else None
        }
        
        # Check if the container is made by the logged-in user
        for container_log in container_logs:
            if container_log[0] == container.id:  # Assuming the container_id is stored in the second column
                containers.append(container_info)
                break
                
        # Limit the containers to 3
        if len(containers) >= 3:
            break
    
    # Close the database connection
    conn.close()
    
    return render_template('dockbox.html', list_img=list_img, containers=containers, username=username)

def is_port_in_use(port):
    # Create a socket object
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Try to bind the socket to the given port
        sock.bind(('localhost', port))
        # Port is available
        return False
    except socket.error:
        # Port is already in use
        return True
    finally:
        # Close the socket
        sock.close()

@app.route('/create-container', methods=['POST'])
@login_required
def create_container():
    try:
        image_name = request.form['image_name']
        client.images.pull(image_name)

        # Generate random port number for the container
        container_port = random.randint(1024, 65535)
        host_port = None

        # Check if the random port is already in use
        while is_port_in_use(container_port):
            container_port = random.randint(1024, 65535)

        # Create the container
        container = client.containers.create(
            image_name,
            name=request.form['container_name'],
            ports={container_port: None},
            detach=True
        )

        # Store container information in the database
        conn = sqlite3.connect('container_times.db')
        conn.execute(
            '''INSERT INTO containers (container_id, container_name, user_id, image_name)
            VALUES (?, ?, ?, ?)''',
            (container.short_id, request.form['container_name'], session['user_id'], request.form['image_name'])
        )
        conn.commit()
        conn.close()
        session['container_id'] = container.short_id

        return redirect(url_for('list_containers'))

    except docker.errors.NotFound as e:
        return 'Error: Container not found'
    except docker.errors.APIError as e:
        return 'Error communicating with Docker API: ' + str(e)

@app.route('/delete_container', methods=['POST'])
def delete_container():
    try:
        container_id = request.form['container_id']
        container = client.containers.get(container_id)
        container.stop()  # Stop the container before deleting
        container.remove()  # Delete the container

        # Remove container information from the database
        conn = sqlite3.connect('container_times.db')
        conn.execute(
            "DELETE FROM containers WHERE container_id = ?",
            (container_id,)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('list_containers'))

    except docker.errors.NotFound:
        return 'Error: Container not found'
    except docker.errors.APIError as e:
        return 'Error communicating with Docker API: ' + str(e)


# LIST IMAGES
@app.route('/list-images', methods=['GET', 'POST'])
@login_required
def list_images():
    list_img = []
    if 'user_id' in session:
        user_id = session['user_id']
        username = get_username(user_id)
    else:
        return redirect(url_for('login'))
    for image in client.images.list():
        image_info = {
            'image_name': image.tags[0] if image.tags else '',
            'created': image.attrs['Created'],
            'size': image.attrs['Size'],
        }
        list_img.append(image_info)
    return render_template('images.html', list_img=list_img, username=username)

# DISPLAY ALL TABLES IN THE DATABASE
def get_table_names(database):
    with sqlite3.connect(database) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        return table_names

# GOTTA RESTRICT USER WITHOUT ADMIN LEVEL FROM ACCESSING THIS
@app.route('/database')
@login_required
def display_tables():
    database = 'container_times.db'
    tables = get_table_names(database)
    table_html = ""
    for table in tables:
        table_html += "<h2>{}</h2>".format(table)
        table_html += display_table_values(database, table)
    return render_template('database.html', table_html=table_html)

# LIST CONTAINERS
@app.route('/list-containers', methods=['GET', 'POST'])
@login_required
def list_containers():
    containers = []
    start_time = session.pop('start_time', None)  # Retrieve and remove start_time from the session
    if 'user_id' in session:
        user_id = session['user_id']
        username = get_username(user_id)
    else:
        return redirect(url_for('login'))
    # Connect to the database
    conn = sqlite3.connect('container_times.db')
    cursor = conn.cursor()
    
    # Retrieve containers made by the logged-in user
    cursor.execute("SELECT * FROM containers WHERE user_id = ?", (user_id,))
    container_logs = cursor.fetchall()
    
    for container in client.containers.list(all=True):
        cpu_percent, memory_percent = get_container_stats(container)
        container_info = {
            'container_id': container.short_id,
            'container_name': container.name,
            'image': container.image.tags[0] if container.image.tags else '',
            'status': container.status,
            'cpu_percent': cpu_percent if container.status == 'running' else None,
            'memory_percent': memory_percent if container.status == 'running' else None,
            'start_time': start_time if container.id == session.get('container_id') else None
        }
        
        # Check if the container is made by the logged-in user
        for container_log in container_logs:
            if container_log[0] == container.short_id:  # Assuming the container_id is stored in the second column
                containers.append(container_info)
                break
    
    # Close the database connection
    conn.close()
    
    return render_template('containers.html', containers=containers, username=username)


def get_container_stats(container):
    cpu_percent = None
    memory_percent = None

    if container.status == 'running':
        try:
            stats = container.stats(stream=False)
            cpu_stats = stats['cpu_stats']
            precpu_stats = stats['precpu_stats']

            cpu_delta = cpu_stats['cpu_usage']['total_usage'] - precpu_stats['cpu_usage']['total_usage']
            system_cpu_delta = cpu_stats['system_cpu_usage'] - precpu_stats['system_cpu_usage']
            number_cpus = len(cpu_stats['cpu_usage']['percpu_usage']) or cpu_stats['online_cpus']

            cpu_percent = round((cpu_delta / system_cpu_delta) * number_cpus * 100.0, 3)

            memory_stats = stats['memory_stats']
            used_memory = memory_stats['usage'] - memory_stats['stats']['cache']
            available_memory = memory_stats['limit']
            memory_percent = round((used_memory / available_memory) * 100.0, 3)
        except docker.errors.APIError as e:
            print('Error retrieving container stats:', str(e))

    return cpu_percent, memory_percent


def get_next_sequence_digit(container_id):
    # Connect to the database
    conn = sqlite3.connect('container_times.db')
    
    # Query the database to retrieve the highest sequence digit for the given container ID
    cursor = conn.execute("SELECT MAX(sequence_digit) FROM containerLogs WHERE container_id=?", (container_id,))
    result = cursor.fetchone()
    
    # Determine the next sequence digit
    next_sequence_digit = 1 if result[0] is None else result[0] + 1
    
    # Close the database connection
    conn.close()
    
    return next_sequence_digit

# CALCULATE START TIME STOP TIME
def calculate_time_difference(start_time, end_time):
    start = datetime.datetime.fromisoformat(start_time)
    end = datetime.datetime.fromisoformat(end_time)
    duration = end - start
    time_difference = float(duration.total_seconds())
    return time_difference


@app.route('/start_container', methods=['POST'])
@login_required
def start_container():
    try:
        container_id = request.form.get('container_id')
        if container_id is None:
            return 'Error: Container ID is missing'
        
        # Find the container based on the ID
        container = client.containers.get(container_id)

        # Connect to the database
        conn = sqlite3.connect('container_times.db')

        # Start the container
        container.start()

        # Record the start time
        start_time = datetime.datetime.now().isoformat()

        # Insert the container information into the database
        conn.execute('''INSERT INTO containerLogs
                        (sequence_digit, container_id, start_time, user_id)
                        VALUES (?, ?, ?, ?)''',
                        (get_next_sequence_digit(container_id), container_id, start_time, session['user_id']))

        # Commit the changes and close the database connection
        conn.commit()
        conn.close()

        # Redirect back to the current page
        return redirect(request.referrer)

    except docker.errors.NotFound as e:
        return 'Error: Container not found'
    except docker.errors.APIError as e:
        return 'Error communicating with Docker API: ' + str(e)
        

@app.route('/stop_container', methods=['POST'])
@login_required
def stop_container():
    try:
        container_id = request.form.get('container_id')
        if container_id is None:
            return 'Error: Container ID is missing'
            
        # Find the container based on the ID
        container = client.containers.get(container_id)

        # Connect to the database
        conn = sqlite3.connect('container_times.db')

        # Start the container
        container.stop()

        # Retrieve the current time
        stop_time = datetime.datetime.now().isoformat()

        # Retrieve the start time from the containerLogs table
        cursor = conn.cursor()
        cursor.execute("SELECT start_time, sequence_digit FROM containerLogs WHERE container_id = ? ORDER BY sequence_digit DESC LIMIT 1", (container_id,))
        result = cursor.fetchone()
        if result:
            start_time, sequence_digit = result

            # Calculate the time difference
            time_difference = calculate_time_difference(start_time, stop_time)
            print("Time Difference:", time_difference)

            # Calculate the total cost based on time difference and the billing rate (e.g., $1.00 per second)
            billing_rate = 0.05
            total_cost = round(time_difference * billing_rate, 2)

            # Update the container record in the database with the stop time and time difference
            cursor.execute("UPDATE containerLogs SET stop_time = ?, total_time = ?, total_cost = ? WHERE container_id = ? AND sequence_digit = ?", (stop_time, time_difference, total_cost, container_id, sequence_digit))
            conn.commit()
        else:
            print("Start time not found for the container ID:", container_id)

        # Close the database connection
        conn.close()

        # Redirect back to the current page
        return redirect(request.referrer)

    except docker.errors.NotFound as e:
        return 'Error: Container not found'
    except docker.errors.APIError as e:
        return 'Error communicating with Docker API: ' + str(e)
        


@app.route('/invoice')
def display_invoice():
    rows = []
    conn = sqlite3.connect('container_times.db')
    cursor = conn.cursor()

    # Query to fetch containerLogs values along with container_name and total_cost from containers table
    query = '''SELECT containerLogs.container_id, containers.container_name, containerLogs.total_time, containerLogs.total_cost
           FROM containerLogs
           INNER JOIN containers ON containerLogs.container_id = containers.container_id
           WHERE containerLogs.total_cost IS NOT NULL'''

    # Execute the query
    cursor.execute(query)

    # Fetch all rows
    rows = cursor.fetchall()

    # Close the cursor and the connection
    cursor.close()
    conn.close()

    return render_template('invoice.html', container_logs=rows)

if __name__ == '__main__':
    app.run(debug=True, host = '0.0.0.0', port = 81)
