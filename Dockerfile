FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY index.html script.js styles.css server.py ./

EXPOSE 8020

CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8020"]
