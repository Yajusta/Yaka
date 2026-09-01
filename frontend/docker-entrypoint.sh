#!/bin/sh
set -e

# Generate configuration files from environment variables
echo "window.DEMO_MODE = \"${DEMO_MODE:-false}\";" >/usr/share/nginx/html/demo-config.js

echo "window.API_BASE_URL = \"${API_BASE_URL:-http://localhost:8000}\";" >/usr/share/nginx/html/api-config.js
echo "window.BASE_URL = \"${BASE_URL:-http://localhost:3000}\";" >>/usr/share/nginx/html/api-config.js
echo "window.BASE_URL_MOBILE = \"${BASE_URL_MOBILE:-http://localhost:3001}\";" >>/usr/share/nginx/html/api-config.js

exec "$@"
