import json
from flask import Flask, jsonify, request
from flask_cors import CORS
import socket
from threading import Thread
import logging
from network import Message, INTERFACE, BROADCAST_PORT, OpCode
import argparse
from application_state import ApplicationState, Question, Vote

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
    app_state = app.config["application_state"]

    return json.dumps(app_state.questions, default = lambda x: {"uuid": x.uuid, "text": x.text, "votes": len(x.votes)})

# Vote Up
@app.route('/api/vote_up', methods=['POST'])
def change_order():
    try:
        # Get the id from the request
        print(request.data)
        question_uuid = request.json['uuid']

        # Find the message with the given id
        # message = next((item for item in data if item['id'] == message_id), None)
        
        # # Update the order if the message is found
        # if message:
        #     message['order'] += 1  # Increment the order by 1
        #     return jsonify({'success': True, 'message': 'Order updated successfully'})
        # else:
        #     return jsonify({'success': False, 'message': 'Message not found'})
        cp = app.config["cp"]

        vote = Vote(socket=f"{cp.ip}:{cp.port}", question_uuid=question_uuid)
        # print(f"Target Question ID {question_id}")
        # for question in application_state.questions:
        #     print(f"Current question_id {question.uuid}")
        #     if question.uuid == question_id:
        #         print(f"Request sid: {request.sid}")
        #         question.toggle_vote(Vote(question_uuid=question_id, socket=request.sid)) 
        #         return jsonify({'success': True, 'message': 'Voted successfully'})
        #     else:
        #         return jsonify({'success': False, 'message': 'Question not found'})
        Message(opcode=OpCode.VOTE_REQUEST, port=cp.port, data=json.dumps(vote.__dict__)).send(cp.leader_ip, cp.leader_port)

        # Return a simple "OK" message
        return jsonify({'success': True, 'message': 'Vote posted successfully'}), 202


    except Exception as e:
        print(e)
        return jsonify({'success': False, 'message': str(e)}), 400

# Add New Question
@app.route('/api/add_question', methods=['POST'])
def add_question():
    try:
        # Get the data from the request
        data_json = request.get_json()

        # Create a new question
        new_question = {
            'text': data_json['text'],
        }

        # Append the new question to the data array
        data.append(new_question)
        cp = app.config["cp"]

        # TODO: Send message to server
        print(f"{cp.leader_ip}:{cp.leader_port}")
        Message(opcode=OpCode.QUESTION_REQUEST, port=cp.port, data=json.dumps(new_question)).send(cp.leader_ip, cp.leader_port)

        # Return a simple "OK" message
        return jsonify({'success': True, 'message': 'Question posted successfully'}), 202
    except Exception as e:
        print(e)
        return jsonify({'success': False, 'message': str(e)}), 500

class ControlPlane:
    def __init__(self, leader_ip, leader_port, ip, port):
        self.leader_ip = leader_ip
        self.leader_port = leader_port
        self.ip = ip  
        self.port = port 

def http_target(host, port, application_state: ApplicationState, cp: ControlPlane):
    print(f"Server running on http://{host}:{port}/")
    app.config["cp"] = cp
    app.config['application_state'] = application_state
    app.run(host=host, port=port, debug=True, use_reloader=False)

def broadcast_target(callback, application_state: ApplicationState, cp: ControlPlane):
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

                callback(msg, ip, application_state, cp)
    except KeyboardInterrupt:
        listen_socket.close()
        exit(0)

def unicast_target(callback, lport: int, application_state: ApplicationState, cp: ControlPlane):
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_socket.bind((INTERFACE.ip.compressed, lport))

    try:
        while True:
            data, (ip, port) = listen_socket.recvfrom(1024)
            if data:
                msg = Message.unmarshal(data)
                logging.debug(f"Unicast message received: {msg.opcode}")
                callback(msg, ip, application_state, cp)
    except KeyboardInterrupt:
        listen_socket.close()
        exit(0)

# Set current application state to the application state received by the server
def hello_reply_handler(message, ip, application_state, cp: ControlPlane):
    print(f"Received this message data in hello reply {message.data}")
    app_state = json.loads(message.data, object_hook=lambda d: ApplicationState(**d))
    application_state.questions = app_state.questions

    cp.leader_ip = ip      
    cp.leader_port = message.port

    print("Received hello reply")

def question_handler(message, ip, application_state, cp: ControlPlane):
    msg = json.loads(message.data)
    application_state.add_question(Question(msg["text"], msg["uuid"]))
    print(f"Added question {msg['text']} to application state")

def vote_handler(message, ip, application_state, cp: ControlPlane):
    msg = json.loads(message.data)
    question = application_state.get_question_from_uuid(msg["question_uuid"])
    question.toggle_vote(Vote(msg["socket"], msg["question_uuid"]))
    print(f"Added vote from {msg["socket"]} to application state")
    
def election_result_handler(message, ip, application_state, cp):
    cp.leader_ip = ip
    cp.leader_port = message.port
    print(f"Switching leader to {cp.leader_ip}:{cp.leader_port}") 

def message_handler(message: Message, ip: str, application_state: ApplicationState, cp: ControlPlane):
    if message.opcode is OpCode.HELLO_REPLY:
        # TODO: the leader is implicitely the node we received the message from
        hello_reply_handler(message, ip, application_state, cp)
    elif message.opcode is OpCode.QUESTION:
        question_handler(message, ip, application_state, cp)
    elif message.opcode is OpCode.VOTE:
        vote_handler(message, ip, application_state, cp)
    elif message.opcode is OpCode.ELECTION_RESULT:
        election_result_handler(message, ip, application_state, cp)
    else:
        return  
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="Client")

    parser.add_argument("--port", default="3678", type=int)
    parser.add_argument("--loglevel", default="INFO", type=str)

    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)

    host = '127.0.0.1'
    http_port = find_available_port(start_port=5000)

    threads = []

    application_state = ApplicationState()
    cp = ControlPlane(None, None, INTERFACE.ip.compressed, args.port)

    http_thread = Thread(target=http_target, args=(host, http_port, application_state, cp))
    threads.append(http_thread)
    http_thread.start()

    broadcast_thread = Thread(target=broadcast_target, args=(message_handler, application_state, cp))
    threads.append(broadcast_thread)
    broadcast_thread.start()

    unicast_thread = Thread(target=unicast_target, args=(message_handler, args.port, application_state, cp))
    threads.append(unicast_thread)
    unicast_thread.start()

    Message(OpCode.HELLO_SERVER, port=args.port).broadcast(2)

    for thread in threads:
        thread.join()