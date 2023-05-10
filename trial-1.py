from flask import Flask, request, render_template
import docker
import docker.errors

app = Flask(__name__)
client = docker.from_env()

@app.route('/')
def home():
    return render_template('/index.html')

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
