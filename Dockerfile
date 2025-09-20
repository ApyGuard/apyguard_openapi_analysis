FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY analyzer.py .

# Make the script executable and available from any working directory
RUN chmod +x analyzer.py

ENTRYPOINT ["python", "/app/analyzer.py"]
