from flask import Flask, jsonify, request
from flask_cors import CORS
import socket


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

# GET API
@app.route('/api/get', methods=['GET'])
def get_data():
    return jsonify(data)

# POST API
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

if __name__ == '__main__':
    host = '127.0.0.1'
    port = find_available_port(start_port=5000)
    print(f"Server running on http://{host}:{port}/")
    app.run(host= host, port=port, debug=True)
    