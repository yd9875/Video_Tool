FROM python:3.12-slim

ARG APP_RELEASE_VERSION=local
ENV APP_RELEASE_VERSION=${APP_RELEASE_VERSION}

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-nanum \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY index.html script.js styles.css server.py ./

EXPOSE 8020

CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8020"]
