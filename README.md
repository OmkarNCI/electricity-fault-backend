# Fog & Edge-Based Electricity Fault Detection System

## What is this?

This is a practical demonstration of how edge and fog computing can work together to monitor power grids efficiently. Instead of sending every sensor reading to the cloud (which would be wasteful), the system processes data locally first, detects problems right away, and only sends the important stuff to AWS.

The whole thing is simulated with Python, so you can run it without any actual hardware. The idea is to show how smart data filtering at the edge/fog layer can drastically reduce cloud costs and latency.

## How it works

- **Edge layer**: Simulated sensors on poles generate voltage, current, temperature, and tilt readings every second
- **Fog layer**: Processes these readings in real-time, detects faults (undervoltage, overload, overheating, etc.), and only sends alerts and summaries to the cloud
- **Cloud layer**: AWS SQS, Lambda, and DynamoDB handle storage and final processing

## Tech Stack

- **Python** - Everything is written in Python for simplicity and readability
- **MQTT (Mosquitto)** - Lightweight pub/sub messaging between edge and fog
- **AWS SQS** - Message queue for reliably sending alerts to the cloud
- **AWS Lambda** - Serverless processing of messages from SQS
- **AWS DynamoDB** - NoSQL database for storing alerts and area summaries
- **YAML** - Configuration files for thresholds and AWS settings
- **FastAPI** - REST API and WebSocket server for the dashboard

## Getting Started

### Prerequisites
- Python 3.10+
- Mosquitto MQTT broker installed locally
- AWS credentials configured (for SQS and DynamoDB access)
- A WebSocket-capable terminal (for real-time updates)

### Setup

Make sure you're in the `Backend/` directory for all commands.

**Step 1: Start the MQTT Broker**

Open a terminal and run:
```bash
mosquitto
```
This starts the message broker that edge and fog layers communicate through.

**Step 2: Start the Fog Processor**

Open a new terminal from the project root:
```bash
python -m src.fog.mqtt_subscriber
```
This listens for sensor data from the edge layer and runs the fault detection logic. You should see connection confirmations and incoming sensor readings.

**Step 3: Start the Sensor Simulator**

Open another terminal:
```bash
python -m src.edge.simulator
```
This generates simulated sensor data and publishes it to MQTT. You'll see logs of voltage, current, temperature, and tilt readings.

**Step 4: Start the Backend API**

Open yet another terminal:
```bash
uvicorn src.dashboard.api:app --reload
```
This runs the FastAPI backend server. The API is now available at `http://localhost:8000` and will serve the dashboard frontend.

**Step 5: Verify Cloud Integration**

After everything is running for a minute or two:
- Check AWS SQS console - you should see messages appearing in the queue
- AWS Lambda functions should be processing those messages
- DynamoDB tables (`Alerts` and `AreaSummaries`) should have records

If you see messages flowing through the entire pipeline, you're good to go!

### Tips
- Keep all terminals visible side-by-side so you can watch everything happening in real-time
- If MQTT connection fails, make sure Mosquitto is actually running
- AWS credentials need to be set up before running. Use `aws configure` if you haven't already
- The simulator runs for 5 minutes by default. Edit `config/settings.yaml` to change this

## Architecture Overview

The system works in layers:

1. **Edge Layer** - Poles with sensors push readings via MQTT every second
2. **Fog Layer** - Local processing detects anomalies and filters data before cloud transmission. Reduces bandwidth by ~80%
3. **Cloud Layer** - SQS queues, Lambda processes, and DynamoDB persists the important alerts and summaries
4. **Dashboard** - WebSocket live updates + REST API for historical data

This approach means:
- No wasted bandwidth sending every sensor reading to the cloud
- Fault detection happens instantly at the fog layer (sub-second latency)
- The cloud only handles the alerts and summaries that matter
- Much cheaper than traditional centralized monitoring