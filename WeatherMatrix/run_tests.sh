#!/bin/bash
# Run all tests for the weather matrix display
# This can be run locally without hardware

set -e

echo "Running Weather Matrix Display Tests"
echo "===================================="
echo ""

# Run tests with coverage
echo "Running unit tests..."
pytest test_matrix_operations.py test_matrix_integration.py test_font_rendering.py test_layout.py test_weather_data.py test_weather_service.py -v --cov=. --cov-report=term-missing

echo ""
echo "===================================="
echo "Tests complete!"
echo ""
echo "To run specific test files:"
echo "  pytest test_matrix_operations.py -v"
echo "  pytest test_matrix_integration.py -v"
echo "  pytest test_font_rendering.py -v"

