from flask import Flask, render_template, request, flash, redirect, url_for
import docker
import docker.errors
import os
import secrets

app = Flask(__name__)
client = docker.from_env()
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(16)

@app.route('/')
def home():
    return render_template('/login.html')

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
    
@app.route('/index')
def index():
    return render_template('/index.html')

# @app.route('/build-image', methods=['POST'])
# def build_image():
    # try:
        # Path to directory containing Dockerfile
        # path = "/path/to/dockerfile/directory"
        # Build the image
        # output = client.images.build(path=path, tag="my-image", quiet=False)
        # Print output from build process
        # for line in output[1]:
            # print(line)
        # Return a message indicating success
        # return "Image built successfully"
    # except docker.errors.BuildError as e:
        # Handle build errors
        # return "Error building image: " + str(e)
    # except docker.errors.APIError as e:
        # Handle API errors
        # return "Error communicating with Docker API: " + str(e)

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

        # Run the container
        container = client.containers.run(
            request.form['image_name'],
            name=request.form['container_name'],
            ports={int(container_port): int(host_port)} if host_port else int(container_port),
            detach=True
        )
        return 'Container created successfully!'
    except docker.errors.ContainerError as e:
        return 'Error creating container: ' + str(e)
    except docker.errors.ImageNotFound as e:
        return 'Error finding image: ' + str(e)
    except docker.errors.APIError as e:
        return 'Error communicating with Docker API: ' + str(e)

if __name__ == '__main__':
    app.run(debug=True, host = '0.0.0.0', port = 81)
