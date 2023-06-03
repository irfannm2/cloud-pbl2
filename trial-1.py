import sqlite3
from flask import Flask, render_template, request, flash, redirect, url_for, session
import docker
import docker.errors
import os
import secrets
import datetime


# Uncomment the line below to enable Docker Daemon TCP connection (without TLS)
# Don't forget to configure the Docker Desktop settings
# client = docker.DockerClient(base_url='tcp://localhost:2375')

# Connect to the database
conn = sqlite3.connect('container_times.db')

# Create a table to store container times
conn.execute('''CREATE TABLE IF NOT EXISTS container_times
                 (container_id TEXT,
                  start_time TEXT,
                  stop_time TEXT,
                  sequence_digit INTEGER,
                  PRIMARY KEY (container_id, sequence_digit))''')

# Close the database connection
conn.close()

app = Flask(__name__, static_url_path='/static')
client = docker.from_env()
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(16)

@app.route('/')
def home():
    return render_template('/index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('/dashboard.html')

@app.route('/login')
def login():
    return render_template('/login.html')

# How to get user run the app without having to open Docker Desktop/login first
@app.route('/docker-login', methods=['POST'])
def docker_login():
    try:
        # Authenticate with Docker using the provided credentials
        client.login(username=request.form['docker_username'], password=request.form['docker_password'])

        # If login is successful, show a flash message and redirect to index.html
        # It stores a message in the session,
        # which can then be displayed on the next web page that the user visits
        flash('Successfully logged in!')
        return redirect(url_for('index'))

    except docker.errors.APIError:
        flash('Invalid credentials. Please try again.')
        return redirect(url_for('home'))

# go to create container form page
@app.route('/create-cont')
def create_cont():
    return render_template('/create-cont.html')

@app.route('/dockbox')
def dockbox():
    return render_template('/dockbox.html')


@app.route('/create-container', methods=['POST'])
def create_container():
    # Split the ":" to extract host port and container port
    host_port = container_port = None
    port_input = request.form['container_port']
    if ':' in port_input:
        host_port, container_port = port_input.split(':')
    else:
        container_port = port_input

    try:
        # Pull the container image from registry Dockerhub
        # User input on Image Name SHOULD BE available at Dockerhub, otherwise error
        # NEXT: might want to add dropdown choices instead of text type
        client.images.pull(request.form['image_name'])

        # Create the container
        container = client.containers.create(
            request.form['image_name'],
            name=request.form['container_name'],
            ports={int(container_port): int(host_port)} if host_port else int(container_port),
            detach=True
        )

        session['container_id'] = container.id

        # REVISE! redirect to list containers
        return redirect(url_for('start_container'))

    except docker.errors.NotFound as e:
        return 'Error: Container not found'
    except docker.errors.APIError as e:
        return 'Error communicating with Docker API: ' + str(e)


# LIST IMAGES
@app.route('/list-images', methods=['GET', 'POST'])
def list_images():
    list_img = []
    for image in client.images.list():
        image_info = {
            'image_name': image.tags[0] if image.tags else '',
            'created': image.attrs['Created'],
            'size': image.attrs['Size'],
        }
        list_img.append(image_info)
    return render_template('images.html', list_img=list_img)


# START STOP TIMES
# Retrieve the start and stop times from the database for each container
def get_container_times(container_id):
    # Create a new database connection
    conn = sqlite3.connect('container_times.db')

    cursor = conn.execute("SELECT container_id, start_time, stop_time FROM container_times WHERE container_id = ?", (container_id,))
    container_times = cursor.fetchall()

    # Close the database connection
    conn.close()

    return container_times

# Calculate the duration (in seconds) for each container
def calculate_duration(start_time, stop_time):
    start = datetime.datetime.fromisoformat(str(start_time))
    stop = datetime.datetime.fromisoformat(str(stop_time))
    duration = stop - start
    return duration.total_seconds()

# Calculate the total time used and the total cost
def calculate_total_time_and_cost(container_id, billing_rate):
    # Retrieve container times from the database for the specific container ID
    container_times = get_container_times(container_id)

    total_time = 0
    for container_time in container_times:
        start_time = container_time[1]
        stop_time = container_time[2]
        duration = calculate_duration(start_time, stop_time)
        total_time += duration

    total_time_hours = total_time / 3600  # Convert seconds to hours
    total_cost = total_time_hours * billing_rate
    return total_time_hours, total_cost

# LIST CONTAINERS
@app.route('/list-containers', methods=['GET', 'POST'])
def list_containers():
    containers = []
    start_time = session.pop('start_time', None)  # Retrieve and remove start_time from the session

    # Set the billing rate per hour
    billing_rate = 1000
    
    for container in client.containers.list(all=True):
        # Calculate the total time used and the total cost
        total_time_hours, total_cost = calculate_total_time_and_cost(container.id, billing_rate)

        cpu_percent, memory_percent = get_container_stats(container)
        container_info = {
            'container_id': container.short_id,
            'container_name': container.name,
            'image': container.image.tags[0] if container.image.tags else '',
            'status': container.status,
            'cpu_percent': cpu_percent if container.status == 'running' else None,
            'memory_percent': memory_percent if container.status == 'running' else None,
            'start_time': start_time if container.id == session.get('container_id') else None,
            'total_time_hours': total_time_hours,
            'total_cost': total_cost
        }
        containers.append(container_info)
    return render_template('containers.html', containers=containers)

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
    cursor = conn.execute("SELECT MAX(sequence_digit) FROM container_times WHERE container_id=?", (container_id,))
    result = cursor.fetchone()
    
    # Determine the next sequence digit
    next_sequence_digit = 1 if result[0] is None else result[0] + 1
    
    # Close the database connection
    conn.close()
    
    return next_sequence_digit


@app.route('/start_container', methods=['POST'])
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

        # Generate a unique identifier combining container ID and sequence digit
        unique_identifier = f"{container_id}_{get_next_sequence_digit(container_id)}"

        # Insert the container information into the database
        conn.execute("INSERT INTO container_times (container_id, start_time, sequence_digit) VALUES (?, ?, ?)", (container_id, start_time, get_next_sequence_digit(container_id)))


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
def stop_container():
    try:
        container_id = request.form.get('container_id')
        if container_id is None:
            return 'Error: Container ID is missing'
        session['container_id'] = container_id
            
        # Find the container based on the ID
        container = client.containers.get(container_id)

        # Connect to the database
        conn = sqlite3.connect('container_times.db')

        # Start the container
        container.stop()

        # Retrieve the current time
        stop_time = datetime.datetime.now().isoformat()

        # Update the container record in the database with the stop time
        conn.execute("UPDATE container_times SET stop_time = ? WHERE container_id = ?", (stop_time, container_id))

        # Commit the changes and close the database connection
        conn.commit()
        conn.close()

        # Redirect back to the current page
        return redirect(request.referrer)

    except docker.errors.NotFound as e:
        return 'Error: Container not found'
    except docker.errors.APIError as e:
        return 'Error communicating with Docker API: ' + str(e)


if __name__ == '__main__':
    app.run(debug=True, host = '0.0.0.0', port = 81)
