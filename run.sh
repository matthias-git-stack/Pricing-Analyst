#!/usr/bin/env bash
# Start the Pricing Intelligence Tool
cd "$(dirname "$0")"
echo "Starting Pricing Intelligence Tool..."
streamlit run app.py
