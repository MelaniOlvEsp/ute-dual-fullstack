#!/bin/sh
set -eu
# Solo URL HTTP(S), sin comillas, controles ni caracteres que permitan inyectar JSON/HTML.
printf '%s' "$VITE_API_URL" | grep -Eq '^https?://[][A-Za-z0-9._:-]+(/[A-Za-z0-9._~:/?&=%+-]*)?$' || {
    echo 'VITE_API_URL no válida' >&2
    exit 1
}
printf '{"apiUrl":"%s"}\n' "$VITE_API_URL" > /usr/share/nginx/html/config.json
