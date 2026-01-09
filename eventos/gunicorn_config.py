import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Prevent zombie database connections
max_requests = 1000  # Restart workers after 1000 requests
max_requests_jitter = 50  # Add randomness to prevent all workers restarting simultaneously

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "eventos_backend"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = None
# certfile = None

# Database connection optimization
# These settings help prevent zombie connections to failed databases
preload_app = False  # Don't preload to allow workers to handle DB failures independently
