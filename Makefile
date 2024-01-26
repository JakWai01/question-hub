.PHONY: server client

server:
	python ./server/main.py

client:
<<<<<<< HEAD
	python ./client/main.py

build:
	docker-compose build --no-cache

run:
	docker-compose up --scale server=2 --scale client=1
=======
	python ./client/main.py
>>>>>>> main
