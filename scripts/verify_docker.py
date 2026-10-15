"""Run with the host Python: python scripts/verify_docker.py.

Uses a uniquely named disposable volume and no external container network.
Requires an already-built lume-finance:local image and a running Docker engine.
"""
import json
import os
import secrets
import subprocess
import tempfile
import time
import uuid

IMAGE = 'lume-finance:local'
name = 'lume-finance-verify-' + uuid.uuid4().hex[:12]
volume = name + '-data'
restored_volume = name + '-restored'
secret = secrets.token_hex(32)
environment = dict(os.environ, SECRET_KEY=secret)


def docker(*args, check=True, input=None):
    result = subprocess.run(['docker', *args], input=input, text=True,
                            capture_output=True, env=environment)
    if check and result.returncode:
        # The secret is passed by variable name, not as a command argument.
        raise RuntimeError(f'Docker operation failed ({args[0]}): {result.stderr.replace(secret, "[redacted]")}')
    return result


HTTP_TEST = r"""
import http.cookiejar, json, re, secrets, sys, urllib.parse, urllib.request
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
root = 'http://127.0.0.1:5000'
def get(path):
    with opener.open(root+path, timeout=5) as response:
        return response.geturl(), response.read().decode()
def token(path):
    return re.search(r'name="csrf_token" value="([^"]+)"',get(path)[1]).group(1)
def post(path, data):
    with opener.open(root+path, urllib.parse.urlencode(data).encode(), timeout=10) as response:
        return response.geturl(), response.read().decode()
assert json.loads(get('/health')[1]) == dict(status='healthy',application='Lume Finance',version='docker-verification')
assert 'More clarity.' in get('/')[1]
assert get('/dashboard')[0].endswith('/login')
# A fixed fictional password allows repeat login after container replacement.
password = 'disposable-verification-passphrase'
if sys.argv[1] == 'create':
    target,_ = post('/register',dict(name='Docker Test',email='docker-test@example.com',password=password,confirm_password=password,csrf_token=token('/register')))
    assert target.endswith('/login')
target,_ = post('/login',dict(email='docker-test@example.com',password=password,csrf_token=token('/login')))
assert target.endswith('/dashboard')
if sys.argv[1] == 'create':
    post('/transactions',dict(description='Docker persistence verification',amount='123.45',type='income',category='Salary',date='2026-10-15',notes='Fictional test only',csrf_token=token('/transactions/new')))
assert 'Docker persistence verification' in get('/dashboard')[1]
assert json.loads(get('/api/summary')[1])['income'] == 12345
for path in ['/budgets','/analytics','/settings','/api/charts','/static/vendor/chart.umd.min.js','/static/css/style.css']:
    get(path)
post('/logout',dict(csrf_token=token('/dashboard')))
assert get('/dashboard')[0].endswith('/login')
print('HTTP, CSRF, login, transaction and local assets verified: '+sys.argv[1])
"""


def start():
    docker('run','--detach','--name',name,'--network','none',
           '--mount',f'type=volume,src={volume},dst=/data',
           '--env','SECRET_KEY','--env','APP_VERSION=docker-verification',IMAGE)
    wait_ready()


def wait_ready():
    for _ in range(45):
        state = json.loads(docker('inspect','--format','{{json .State}}',name).stdout)
        if not state['Running']:
            raise RuntimeError('Container exited: '+docker('logs',name).stdout.replace(secret,'[redacted]'))
        if state['Health']['Status'] == 'healthy':
            return
        time.sleep(1)
    raise RuntimeError('Container did not become healthy within 45 seconds.')


def http_test(phase):
    result=docker('exec','-i',name,'python','-',phase,input=HTTP_TEST)
    print(result.stdout.strip())


try:
    docker('volume','create',volume)
    start()
    uid=docker('exec',name,'id','-u').stdout.strip()
    assert uid == '10001', 'Unexpected container UID'
    print('Non-root UID verified: '+uid)
    # The allowlisted image must not contain a host secret or host database.
    docker('exec',name,'python','-c',
           "from pathlib import Path; p=Path('/srv/lume'); assert not list(p.rglob('.env')); assert not list(p.rglob('*.sqlite*')); assert not (p/'tests').exists()")
    http_test('create')
    docker('restart','--timeout','40',name)
    wait_ready()
    http_test('restart')
    logs=docker('logs',name)
    assert secret not in logs.stdout+logs.stderr
    assert 'disposable-verification-passphrase' not in logs.stdout+logs.stderr
    docker('stop','--time','40',name)
    exit_code=docker('inspect','--format','{{.State.ExitCode}}',name).stdout.strip()
    assert exit_code == '0', 'Gunicorn did not exit cleanly'
    docker('rm',name)
    start()
    http_test('replacement')
    docker('stop','--time','40',name)
    # Exercise the documented archive procedure on test data only.
    with tempfile.TemporaryDirectory(prefix='lume-docker-backup-') as backup_dir:
        docker('run','--rm','--network','none',
               '--mount',f'type=volume,src={volume},dst=/data,readonly',
               '--mount',f'type=bind,src={backup_dir},dst=/backup',
               '--env','BACKUP_FILE=verification.tar.gz','--entrypoint','python',IMAGE,'-c',
               "import os,tarfile; archive=tarfile.open('/backup/'+os.environ['BACKUP_FILE'],'x:gz'); archive.add('/data',arcname='.'); archive.close()")
        docker('volume','create',restored_volume)
        docker('run','--rm','--network','none',
               '--mount',f'type=volume,src={restored_volume},dst=/data',
               '--mount',f'type=bind,src={backup_dir},dst=/backup,readonly',
               '--env','BACKUP_FILE=verification.tar.gz','--entrypoint','python',IMAGE,'-c',
               "import os,tarfile; from pathlib import Path; assert not any(Path('/data').iterdir()); archive=tarfile.open('/backup/'+os.environ['BACKUP_FILE'],'r:gz'); archive.extractall('/data',filter='data'); archive.close()")
        docker('rm',name)
        volume = restored_volume
        start()
        http_test('restored')
    print('PASS: health, non-root, secret exclusion, offline runtime, restart/replacement persistence, backup/restore, and graceful shutdown.')
finally:
    # Only uniquely named resources created by this invocation are removed.
    docker('stop','--time','40',name,check=False)
    docker('rm',name,check=False)
    docker('volume','rm',volume,check=False)
    docker('volume','rm',name+'-data',check=False)
    docker('volume','rm',restored_volume,check=False)
