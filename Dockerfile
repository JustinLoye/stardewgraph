FROM python:3.10.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y unzip && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

COPY . .

# Unzip wiki sources
RUN mkdir -p /app/data && unzip /app/data/wiki/sources/sources.zip -d /app/data/wiki/sources/

# Install Python requirements
RUN pip install --no-cache-dir -r requirements_pipreqs.txt

CMD ["python", "-m", "stardewkg.neo4j.run_writers"]
