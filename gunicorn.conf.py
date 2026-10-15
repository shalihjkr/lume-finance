"""Linux container server settings; native Windows still uses python app.py."""
import os

secret = os.environ.get('SECRET_KEY', '')
if len(secret) < 32 or secret == 'replace-with-a-long-random-secret':
    raise RuntimeError('Supply a stable, random SECRET_KEY of at least 32 characters.')
del secret

port = int(os.environ.get('PORT', '5000'))
if not 1 <= port <= 65535:
    raise RuntimeError('PORT must be between 1 and 65535.')

bind = f'0.0.0.0:{port}'
workers = 2
worker_class = 'sync'
# The factory runs migrations once in the master before workers are forked.
# Its application context closes the SQLite connection before the fork.
preload_app = True
timeout = 30
graceful_timeout = 30
keepalive = 2
umask = 0o077
accesslog = '-'
errorlog = '-'
loglevel = 'info'
capture_output = True
# Do not trust forwarded headers without an explicitly configured proxy.
forwarded_allow_ips = ''
