# syntax=docker/dockerfile:1
FROM python:3.10-alpine
WORKDIR /webserver
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
EXPOSE 5000
COPY . .
CMD ["python3.10", "app.py"]