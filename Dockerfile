FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json ./
COPY scripts/install_dependencies.py ./scripts/
COPY src ./src
COPY assets ./assets
COPY refinery_functional_models ./refinery_functional_models
COPY .streamlit ./.streamlit

ENV PYTHONPATH=/app/src
ENV PYTHONIOENCODING=utf-8
ENV PYTHONUTF8=1
ENV ARTIFACT_DATA_DIR=/data
ENV ARTIFACT_OUTPUT_DIR=/output
ENV MPLBACKEND=Agg
ENV ENABLE_RRT_ANIMATION=false

RUN pip install --no-cache-dir --upgrade pip \
    && python scripts/install_dependencies.py \
    && pip install --no-cache-dir streamlit==1.41.1 requests==2.32.3

RUN mkdir -p /data/full /data/uploads /output/jobs

EXPOSE 8501

CMD ["streamlit", "run", "src/artifact_ui/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.maxUploadSize=300", \
     "--server.maxMessageSize=300", \
     "--browser.gatherUsageStats=false"]
