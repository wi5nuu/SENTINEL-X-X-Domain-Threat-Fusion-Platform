#!/bin/bash
# Verification Script for Enhanced Features
# SENTINEL Platform - Enhanced Features Verification

echo "=========================================="
echo "SENTINEL Enhanced Features Verification"
echo "=========================================="
echo ""

# Check if enhanced profile containers are running
echo "[1/5] Checking Enhanced Containers Status..."
FLIGHTAWARE_STATUS=$(docker-compose ps sentinel-flightaware 2>/dev/null | grep -c "Up")
WEATHER_STATUS=$(docker-compose ps sentinel-weather 2>/dev/null | grep -c "Up")
CORRELATION_STATUS=$(docker-compose ps sentinel-correlation-engine 2>/dev/null | grep -c "Up")

if [ "$FLIGHTAWARE_STATUS" -eq 1 ]; then
    echo "  ✅ FlightAware Ingestor: RUNNING"
else
    echo "  ⚠️  FlightAware Ingestor: NOT RUNNING (optional - requires API key)"
fi

if [ "$WEATHER_STATUS" -eq 1 ]; then
    echo "  ✅ Weather Ingestor: RUNNING"
else
    echo "  ⚠️  Weather Ingestor: NOT RUNNING (optional - requires API key)"
fi

if [ "$CORRELATION_STATUS" -eq 1 ]; then
    echo "  ✅ Correlation Engine: RUNNING"
else
    echo "  ❌ Correlation Engine: NOT RUNNING (required)"
fi

echo ""

# Check Kafka topics
echo "[2/5] Checking Enhanced Kafka Topics..."
KAFKA_CONTAINER=$(docker-compose ps -q kafka)

if [ -n "$KAFKA_CONTAINER" ]; then
    TOPICS=$(docker exec "$KAFKA_CONTAINER" kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null)
    
    for TOPIC in "enhanced-air-tracks" "weather-data" "weather-alerts" "airport-conditions" "correlated-alerts"; do
        if echo "$TOPICS" | grep -q "^$TOPIC$"; then
            echo "  ✅ Topic: $TOPIC"
        else
            echo "  ❌ Topic: $TOPIC (missing)"
        fi
    done
else
    echo "  ❌ Kafka container not running"
fi

echo ""

# Check environment configuration
echo "[3/5] Checking Enhanced Configuration..."
if [ -f ".env" ]; then
    if grep -q "AEROAPI_KEY=" .env && [ -n "$(grep "AEROAPI_KEY=" .env | cut -d'=' -f2)" ]; then
        echo "  ✅ FlightAware API Key: CONFIGURED"
    else
        echo "  ⚠️  FlightAware API Key: NOT CONFIGURED (optional)"
    fi
    
    if grep -q "OPENWEATHER_API_KEY=" .env && [ -n "$(grep "OPENWEATHER_API_KEY=" .env | cut -d'=' -f2)" ]; then
        echo "  ✅ OpenWeather API Key: CONFIGURED"
    else
        echo "  ⚠️  OpenWeather API Key: NOT CONFIGURED (optional)"
    fi
    
    if grep -q "ENABLE_CORRELATION_ENGINE=true" .env; then
        echo "  ✅ Correlation Engine: ENABLED"
    else
        echo "  ⚠️  Correlation Engine: NOT ENABLED"
    fi
    
    if grep -q "ENABLE_DATA_QUALITY_VALIDATION=true" .env; then
        echo "  ✅ Data Quality Validation: ENABLED"
    else
        echo "  ⚠️  Data Quality Validation: NOT ENABLED"
    fi
else
    echo "  ❌ .env file not found"
fi

echo ""

# Check logs for enhanced data
echo "[4/5] Checking Enhanced Data Flow..."

if [ "$FLIGHTAWARE_STATUS" -eq 1 ]; then
    FA_LOGS=$(docker-compose logs --tail=50 sentinel-flightaware 2>/dev/null | grep -c "enhanced flights")
    if [ "$FA_LOGS" -gt 0 ]; then
        echo "  ✅ FlightAware: Processing enhanced flights"
    else
        echo "  ⚠️  FlightAware: No enhanced flights detected yet"
    fi
fi

if [ "$WEATHER_STATUS" -eq 1 ]; then
    WEATHER_LOGS=$(docker-compose logs --tail=50 sentinel-weather 2>/dev/null | grep -c "weather data")
    if [ "$WEATHER_LOGS" -gt 0 ]; then
        echo "  ✅ Weather: Processing weather data"
    else
        echo "  ⚠️  Weather: No weather data detected yet"
    fi
fi

if [ "$CORRELATION_STATUS" -eq 1 ]; then
    CORR_LOGS=$(docker-compose logs --tail=50 sentinel-correlation-engine 2>/dev/null | grep -c "correlated")
    if [ "$CORR_LOGS" -gt 0 ]; then
        echo "  ✅ Correlation: Generating correlated alerts"
    else
        echo "  ⚠️  Correlation: No correlated alerts yet"
    fi
fi

echo ""

# Data Quality Metrics
echo "[5/5] Checking Data Quality Metrics..."

if [ "$CORRELATION_STATUS" -eq 1 ]; then
    QUALITY_LOGS=$(docker-compose logs --tail=100 sentinel-correlation-engine 2>/dev/null | grep "quality_score" | tail -5)
    if [ -n "$QUALITY_LOGS" ]; then
        echo "  ✅ Quality scoring active"
        echo "$QUALITY_LOGS" | while read line; do
            echo "     $line"
        done
    else
        echo "  ⚠️  No quality score data yet"
    fi
else
    echo "  ❌ Correlation engine not running"
fi

echo ""
echo "=========================================="
echo "Verification Complete"
echo "=========================================="
echo ""
echo "To enable enhanced features:"
echo "  1. Add API keys to .env file"
echo "  2. Run: docker-compose --profile enhanced up -d"
echo ""
echo "For more information, see ENHANCED_FEATURES.md"
