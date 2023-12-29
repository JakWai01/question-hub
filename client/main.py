import http.server
import socketserver
import socket
import threading
import netifaces
from ipaddress import IPv4Interface

# HTTP server to handle web client requests
class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    pass

def http_server():
    PORT = 8000
    Handler = MyHttpRequestHandler

    with socketserver.TCPServer(("localhost", PORT), Handler) as httpd:
        print("HTTP server started on port", PORT)
        httpd.serve_forever()


#Client Node Initiator

if __name__ == "__main__":
    try:
        # Start the HTTP server in a separate thread
        http_thread = threading.Thread(target=http_server)
        http_thread.start()
        
    except Exception as e:
        print(f"Error: {e}")