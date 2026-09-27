#!/bin/sh
set -e

# Generate configuration files from environment variables
echo "window.DEMO_MODE = \"${DEMO_MODE:-false}\";" >/usr/share/nginx/html/demo-config.js

echo "window.API_BASE_URL = \"${API_BASE_URL:-http://localhost:8000}\";" >/usr/share/nginx/html/api-config.js
echo "window.BASE_URL = \"${BASE_URL:-http://localhost:3000}\";" >>/usr/share/nginx/html/api-config.js
echo "window.BASE_URL_MOBILE = \"${BASE_URL_MOBILE:-http://localhost:3001}\";" >>/usr/share/nginx/html/api-config.js

# Security headers: allow the API origin (scheme://host[:port] of API_BASE_URL)
# in the CSP connect-src. Anything else (relative URL, odd characters) is left
# out: the API is then only reachable on the same origin ('self'). Scheme and
# host are case-insensitive, hence the lowercasing (the path is dropped).
API_ORIGIN=$(printf '%s' "${API_BASE_URL:-http://localhost:8000}" |
	tr '[:upper:]' '[:lower:]' |
	sed -nE 's#^(https?://[a-z0-9.-]+(:[0-9]+)?)([/?].*)?$#\1#p' | head -n 1)
if [ -z "$API_ORIGIN" ]; then
	# IPv6 literals and host names with "_" cannot be expressed in a CSP
	echo "WARNING: API_BASE_URL (${API_BASE_URL}) has no http(s) origin usable in a CSP:" \
		"connect-src limited to 'self', a cross-origin API will be blocked" >&2
fi
sed "s#__API_ORIGIN__#${API_ORIGIN}#" /etc/nginx/security-headers.conf.template \
	>/etc/nginx/yaka/security-headers.conf

exec "$@"
