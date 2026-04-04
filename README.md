Fog & Edge-Based Electricity Fault Detection System

Project Overview

This project is a simulation of an electricity monitoring system built using Edge, Fog, and Cloud computing concepts.

The system generates simulated electricity sensor data and processes it in different stages. The fog layer detects abnormal conditions such as overload, voltage drop, or pole tilt. Important alerts and area-level summaries are then sent to AWS services for storage and further processing.

The main goal of this project is to demonstrate how fog computing can process data locally and reduce unnecessary cloud traffic, while still sending critical information to the cloud.

This project is written completely in Python and uses simulated sensors instead of physical devices.

Technologies Used
Python — Main programming language
MQTT (Mosquitto) — Used for communication between edge and fog layers
AWS SQS — Used to queue messages from fog to cloud
AWS Lambda — Processes incoming SQS messages
AWS DynamoDB — Stores alerts and area summaries
YAML Configuration — Used for system settings
Python Dataclasses — Used to structure sensor data

How to Run This Project:

Step 1 — Start MQTT Broker:
Run Mosquitto broker:
mosquitto

Step 2 — Start Fog Subscriber   -> This will start listening for incoming sensor data.
Open terminal from project root:
python -m src.fog.mqtt_subscriber

Step 3 — Run Sensor Simulator -> This will start generating simulated sensor data.
Open another terminal from project root:
python -m src.edge.simulator

Step 4 - Run the fastapi backend app to run the dashboard
Open another terminal from project root:
uvicorn src.dashboard.api:app --reload

Step 5 — Verify AWS Processing
After running the system:
Messages should appear in AWS SQS
Lambda should process the messages
Data should be stored in DynamoDB

Purpose of This Project: 
This project demonstrates how:
1. Edge devices generate data
2. Fog layer processes data locally
3. Only important data is sent to the cloud
4. Cloud services store and manage the results

It helps show the practical working of Fog and Edge Computing systems in a real-world style electricity monitoring scenario.