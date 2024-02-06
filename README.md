# question-hub

## Usage 

When using the server outside of the `docker-compose` setup, the network has to be configured to `network_mode: host` in order for the broadcast to work.
This also does not work at the moment. Only starting the client with `python3 main.py` works. The container can't receive broadcast messages from the server