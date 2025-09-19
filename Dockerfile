FROM python:3.11-slim

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY analyzer.py /app/analyzer.py
WORKDIR /app

ENTRYPOINT ["python", "analyzer.py"]
