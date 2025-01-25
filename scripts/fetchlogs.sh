#!/bin/bash

# Help text
show_help() {
    echo "Usage: fetchlogs [SECONDS]"
    echo "Fetch CloudWatch logs from development environment"
    echo ""
    echo "Options:"
    echo "  -h --help       Show this help message"
    echo ""
    echo "Arguments:"
    echo "  SECONDS          Number of seconds of historical logs to fetch"
    echo "                   If not provided streams logs in real-time"
    echo ""
    echo "Examples:"
    echo "  fetchlogs        # Stream logs in real-time"
    echo "  fetchlogs 3600   # Fetch last hour (3600 seconds) of logs"
}

# Default values
SECONDS_TO_FETCH=""
LOG_GROUP="/ecs/vimbiso-development"
AWS_REGION="af-south-1"

# Check required environment variables
check_aws_env() {
    local missing=false

    if [ -z "${AWS_ACCESS_KEY_ID}" ]; then
        echo "Error: AWS_ACCESS_KEY_ID environment variable is not set"
        missing=true
    fi

    if [ -z "${AWS_SECRET_ACCESS_KEY}" ]; then
        echo "Error: AWS_SECRET_ACCESS_KEY environment variable is not set"
        missing=true
    fi

    if [ "$missing" = true ]; then
        echo ""
        echo "Please set the required environment variables:"
        echo "export AWS_ACCESS_KEY_ID='your_access_key'"
        echo "export AWS_SECRET_ACCESS_KEY='your_secret_key'"
        exit 1
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        [0-9]*)
            SECONDS_TO_FETCH=$1
            shift
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Ensure AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed"
    exit 1
fi

# Check AWS environment variables
check_aws_env

# Function to get the latest log stream
get_latest_stream() {
    aws logs describe-log-streams \
        --log-group-name $LOG_GROUP \
        --order-by LastEventTime \
        --descending \
        --limit 1 \
        --query 'logStreams[0].logStreamName' \
        --output text \
        --region $AWS_REGION
}

# Function to convert seconds to milliseconds timestamp
get_start_time() {
    local seconds=$1
    echo $(($(date +%s) - seconds))000
}

# If no seconds specified stream logs in real-time
if [ -z "$SECONDS_TO_FETCH" ]; then
    echo "Streaming logs in real-time from $LOG_GROUP in ${AWS_REGION} (Ctrl+C to stop)..."
    aws logs tail $LOG_GROUP --follow --region $AWS_REGION
else
    # Get the latest log stream silently
    LOG_STREAM=$(get_latest_stream 2>/dev/null)
    if [ -z "$LOG_STREAM" ]; then
        exit 1 2>/dev/null
    fi

    # Create logs directory and prepare output file
    mkdir -p ./logs 2>/dev/null
    output_file="./logs/cloudwatch_logs_$(date +%Y%m%d_%H%M%S).log"

    echo "Fetching logs from the last $SECONDS_TO_FETCH seconds..."

    # Fetch and process logs silently to file
    aws logs get-log-events \
        --log-group-name "$LOG_GROUP" \
        --log-stream-name "$LOG_STREAM" \
        --start-time $(get_start_time $SECONDS_TO_FETCH) \
        --limit 10000 \
        --query 'events[*].[timestamp,message]' \
        --output text \
        --region "$AWS_REGION" 2>/dev/null | \
    while read -r timestamp message; do
        if [[ "$message" =~ \[([0-9]{2}/[A-Za-z]{3}/[0-9]{4}:[0-9]{2}:[0-9]{2}:[0-9]{2} [+-][0-9]{4})\] ]]; then
            echo "$message" >> "$output_file"
        else
            if [[ ${#timestamp} -eq 13 ]]; then
                timestamp=${timestamp%???}
            fi
            if [[ "$timestamp" =~ ^[0-9]+$ ]]; then
                formatted_date=$(TZ=UTC date -d "@$timestamp" "+[%d/%b/%Y:%H:%M:%S %z]" 2>/dev/null)
                echo "$formatted_date $message" >> "$output_file"
            fi
        fi
    done 2>/dev/null

    echo "Logs saved to $output_file"
fi
