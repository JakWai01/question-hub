.PHONY: server client run

server:
	python ./server/main.py

client:
	python ./client/main.py

build:
	docker-compose build --no-cache

run:
	docker-compose up
