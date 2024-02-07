# question-hub

## Usage 

Building the client:

```
podman build -f Containerfile -t client
```

Running the client: 

`--port` and `--frontend-port` are optional

```
podman run --network host --rm client:latest python3 main.py --port 3452 --frontend-port 8081
```

Running the server

`--port` is optional

```
python3 main.py --port 9091
```