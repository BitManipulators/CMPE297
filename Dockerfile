# ==============================
# Stage 1: Build the App
# ==============================
FROM ubuntu:20.04 AS builder

# Define the argument key
ARG BACKEND_BASE_URL_ARG
ARG WEBSOCKET_BASE_URL_ARG

RUN if [ -z "$BACKEND_BASE_URL_ARG" ]; then \
        echo "ERROR: BACKEND_BASE_URL_ARG must be supplied via --build-arg."; \
        exit 1; \
    else \
        echo "INFO: BACKEND_BASE_URL_ARG is $BACKEND_BASE_URL_ARG"; \
    fi
RUN if [ -z "$WEBSOCKET_BASE_URL_ARG" ]; then \
        echo "ERROR: WEBSOCKET_BASE_URL_ARG must be supplied via --build-arg."; \
        exit 1; \
    else \
        echo "INFO: WEBSOCKET_BASE_URL_ARG is $WEBSOCKET_BASE_URL_ARG"; \
    fi

# 1. Install basics
RUN apt-get update && apt-get install -y \
    curl git unzip xz-utils zip libglu1-mesa \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /home/developer

# 2. Install Flutter
RUN git clone https://github.com/flutter/flutter.git -b stable
ENV PATH="$PATH:/home/developer/flutter/bin"

# 3. Copy source code
WORKDIR /app
COPY pubspec.yaml /app/pubspec.yaml
COPY pubspec.lock /app/pubspec.lock

# 4. Get dependencies
RUN flutter pub get

# Use it in the build command
# The --dart-define flag writes the value into the compiled JS files
COPY . .
RUN flutter build web --release --dart-define=BACKEND_BASE_URL=$BACKEND_BASE_URL_ARG --dart-define=WEBSOCKET_BASE_URL=$WEBSOCKET_BASE_URL_ARG
# ----------------------

# ==============================
# Stage 2: Serve with Nginx
# ==============================
FROM nginx:alpine

# Copy the compiled static files from the builder
COPY --from=builder /app/build/web /usr/share/nginx/html

# Copy your Nginx config (created in previous steps)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
