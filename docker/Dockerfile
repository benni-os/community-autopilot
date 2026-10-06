FROM python:3.12-slim

WORKDIR /app

# Copy dependency specifications and sources
COPY pyproject.toml .
COPY src/ src/

# Install application and production dependencies
RUN pip install --no-cache-dir .

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

ENTRYPOINT ["autopilot"]
CMD ["run"]
