# m1frame Studio — container image
# Build:  docker build -t m1frame .
# Run:    docker run -p 8080:8080 -e ANTHROPIC_API_KEY=sk-... m1frame
#         (no key? it still serves the Studio in demo mode)
FROM python:3.11-slim

WORKDIR /app

# Install deps first for layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App
COPY . .

# Build the bundled demo so static/demo mode works out of the box
RUN python studio/build_demo.py || true

EXPOSE 8080
ENV PORT=8080 \
    HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1

# Healthcheck hits the API
HEALTHCHECK --interval=30s --timeout=4s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health').status==200 else 1)" || exit 1

CMD ["python", "api/server.py"]
