from Backend.src.cloud.lambda_consumer.handler import lambda_handler

sample_event = {
    "Records": [
        {
            "body": """
            {
                "type": "ALERT",
                "data": {
                    "area_id": "AREA_1",
                    "pole_id": "P1",
                    "timestamp": "2026-03-21T22:35:00+00:00",
                    "severity": "CRITICAL",
                    "alert_type": "DOUBLE_POLE_FAILURE_RISK",
                    "details": {
                        "tilt_deg": 17.5,
                        "voltage_v": 180.0
                    }
                }
            }
            """
        },
        {
            "body": """
            {
                "type": "AREA_SUMMARY",
                "data": {
                    "area_id": "AREA_1",
                    "timestamp": "2026-03-21T22:35:00+00:00",
                    "score": 72.5,
                    "classification": "SHEDDING_RISK",
                    "active_poles": 4,
                    "alert_count": 2,
                    "metrics": {
                        "avg_voltage_v": 198.4
                    }
                }
            }
            """
        }
    ]
}

print(lambda_handler(sample_event, None))