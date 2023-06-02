from flask import Flask, render_template, request, flash, redirect, url_for, session
import docker
import docker.errors
import os
import secrets

app = Flask(__name__, static_url_path='/static')
client = docker.from_env()
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(16)

@app.route('/')
def home():
    return render_template('/index.html')


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
        # return 'Container created successfully!'

        # Redirect to start.html
        # return redirect(url_for('start_container', container = container))

        # Store the container ID in a session variable
        session['container_id'] = container.id

        # Redirect to start.html
        return redirect(url_for('start_container'))
    
        # # Start the container
        # container.start();

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


# LIST CONTAINERS
@app.route('/list-containers', methods=['GET', 'POST'])
def list_containers():
    containers = []
    for container in client.containers.list(all=True):
        container_info = {
            'container_id': container.id,
            'container_name': container.name,
            'image': container.image.tags[0] if container.image.tags else '',
            'status': container.status,
        }
        containers.append(container_info)
    return render_template('containers.html', containers=containers)

@app.route('/start_container', methods=['GET', 'POST'])
def start_container():
    if request.method == 'POST':
        try:
            # Find the container based on the name
            # container = client.containers.get(request.form['container_name'])
            # container = client.containers.get(container.name)
            # container_name = request.args.get('container_name')
            # container = client.containers.get(request.form['container_name'])

            # container_name = request.form.get('container_name')
            # if container_name is None:
            #     return 'Error: Container name is missing'
            # container = client.containers.get(container_name)

            # Find the container based on the name
            # container = client.containers.get(container_name)
            # Start the container
            # container.start()
            # container.run()

            # Retrieve the container ID from the session variable
            # container_id = session.get('container_id')
            container_id = request.form.get('container_id')
            if container_id is None:
                return 'Error: Container ID is missing'
            session['container_id'] = container_id


            
            # Find the container based on the ID
            container = client.containers.get(container_id)

            # Start the container
            container.start()

            # return 'Container started successfully!'
            # Display a flash message with the success notification
            flash('Container started successfully!')
            return render_template('start.html')

        except docker.errors.NotFound as e:
            return 'Error: Container not found'
        except docker.errors.APIError as e:
            return 'Error communicating with Docker API: ' + str(e)
    else:
        # Handle GET request for displaying the start.html page
        return render_template('start.html')

@app.route('/stop_container', methods=['POST'])
def stop_container():
    try:
        # Retrieve the container ID from the session variable
        container_id = session.get('container_id')

        # Find the container based on the ID
        container = client.containers.get(container_id)

        # Stop the container
        container.stop()

        # return 'Container stopped successfully!'
        # Display a flash message with the success notification
        flash('Container stopped successfully!')
        return render_template('start.html')

    except docker.errors.NotFound as e:
        return 'Error: Container not found'
    except docker.errors.APIError as e:
        return 'Error communicating with Docker API: ' + str(e)


# comment code below to make it no error
    # except docker.errors.ContainerError as e:
    #     return 'Error creating container: ' + str(e)
    # except docker.errors.ImageNotFound as e:
    #     return 'Error finding image: ' + str(e)
    # except docker.errors.APIError as e:
    #     return 'Error communicating with Docker API: ' + str(e)

if __name__ == '__main__':
    app.run(debug=True, host = '0.0.0.0', port = 81)
