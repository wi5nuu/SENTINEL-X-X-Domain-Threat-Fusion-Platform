#!/bin/sh
set -e

echo "Waiting for Kafka to be ready..."
sleep 10

TOPICS="air-tracks maritime-positions seismic-events rf-signals cyber-events alerts response-commands dead-letter-queue enhanced-air-tracks weather-data weather-alerts airport-conditions correlated-alerts"

for TOPIC in $TOPICS; do
  kafka-topics --bootstrap-server kafka:9092 \
    --create \
    --if-not-exists \
    --topic "$TOPIC" \
    --partitions 3 \
    --replication-factor 1 \
    --config cleanup.policy=delete \
    --config retention.ms=604800000 \
    --config max.message.bytes=1048576
  echo "Created topic: $TOPIC"
done

echo "Kafka topics initialized successfully."
