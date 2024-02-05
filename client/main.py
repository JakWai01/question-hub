from flask import Flask, jsonify, request
from flask_cors import CORS
import socket
from threading import Thread
import logging
from network import Message, INTERFACE, BROADCAST_PORT

app = Flask(__name__)


CORS(app)

# Sample data for demonstration
data = [
    { 'id': 1, 'title': 'Python3 Issues', 'message': 'I cant run python3 commands on shell', 'order': 0 },
    { 'id': 2, 'title': 'Python2 Issues', 'message': 'I cant run python3 commands on shell', 'order': 0 },
    { 'id': 3, 'title': 'Python1 Issues', 'message': 'I cant run python3 commands on shell', 'order': 0 },
    { 'id': 4, 'title': 'Python0 Issues', 'message': 'I cant run python3 commands on shell', 'order': 0 },
  ]


def get_available_ip():
    try:
        # Create a socket to get the local machine's IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))  # Use a well-known IP address for internet connectivity check
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except socket.error:
        return '0.0.0.0'  # Default to localhost if unable to get the IP
    

def find_available_port(start_port, max_attempts=10):
    for _ in range(max_attempts):
        try:
            # Create a socket to check if the port is available
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', start_port))
            return start_port
        except socket.error:
            start_port += 1

    raise Exception(f"Could not find an available port in the range {start_port} to {start_port + max_attempts}")    

# GET All Questions
@app.route('/api/get', methods=['GET'])
def get_data():
    return jsonify(data)

# Vote Up
@app.route('/api/vote_up', methods=['POST'])
def change_order():
    try:
        # Get the id from the request
        message_id = int(request.json['id'])

        # Find the message with the given id
        message = next((item for item in data if item['id'] == message_id), None)

        # Update the order if the message is found
        if message:
            message['order'] += 1  # Increment the order by 1
            return jsonify({'success': True, 'message': 'Order updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Message not found'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# Add New Question
@app.route('/api/add_question', methods=['POST'])
def add_question():
    try:
        # Get the data from the request
        data_json = request.get_json()

        # Create a new question
        new_question = {
            'id': data[-1]['id'] + 1,
            'title': data_json['title'],
            'message': data_json['message'],
            'order': 0,
        }

        # Append the new question to the data array
        data.append(new_question)

        # Return a simple "OK" message
        return jsonify({'success': True, 'message': 'Question added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

def http_target(host, port):
    print(f"Server running on http://{host}:{port}/")
    app.run(host=host, port=port, debug=True, use_reloader=False)

def broadcast_target(callback):
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(("", BROADCAST_PORT))

    try:
        while True:
            data, (ip, port) = listen_socket.recvfrom(1024)
            if data:
                msg = Message.unmarshal(data)

                logging.debug(f"Broadcast message received: {msg.opcode}")

                callback(msg, ip)
    except KeyboardInterrupt:
        listen_socket.close()
        exit(0)

def unicast_target(callback, lport: int):
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_socket.bind((INTERFACE.ip.compressed, lport))

    try:
        while True:
            data, (ip, port) = listen_socket.recvfrom(1024)
            if data:
                msg = Message.unmarshal(data)
                logging.debug(f"Unicast message received: {msg.opcode}")
                callback(msg, ip)
    except KeyboardInterrupt:
        listen_socket.close()
        exit(0)


if __name__ == '__main__':
    host = '127.0.0.1'
    port = find_available_port(start_port=5000)

    threads = []

    http_thread = Thread(target=http_target, args=(host, port))
    threads.append(http_thread)
    http_thread.start()

    broadcast_thread = Thread(target=broadcast_target)
    threads.append(broadcast_thread)
    broadcast_thread.start()

    unicast_thread = Thread(target=unicast_target)
    threads.append(unicast_thread)
    unicast_thread.start()

    # TODO: Send Hello message from client

    for thread in threads:
        thread.join()