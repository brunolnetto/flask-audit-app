# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Make the postgres check script executable
RUN chmod +x ./scripts/wait-for-postgres.sh

# Make the startup script executable
RUN chmod +x ./scripts/start.sh

# Install psql
RUN apt-get update && \
    apt-get install -y postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5000 available to the world outside this container
EXPOSE 5000



# Run app.py when the container launches
CMD ["flask", "run", "--host=0.0.0.0"]
