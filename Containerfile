FROM node:20-alpine AS frontend

WORKDIR /ui

COPY qhub-ui .

RUN npm ci && npm run build


FROM python:3.12-alpine AS middleware

WORKDIR /app/client 

COPY requirements.txt .

RUN apk add gcc python3-dev musl-dev linux-headers
RUN pip install -r requirements.txt
RUN pip install gunicorn

COPY --from=frontend /ui/dist ../qhub-ui/dist
COPY client .

CMD python3 main.py