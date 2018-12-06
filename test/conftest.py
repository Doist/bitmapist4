from builtins import range

import pytest
import os
import subprocess
import atexit
import socket
import time
import redis
import bitmapist4

REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6399

BITMAPIST_SERVER_HOST = '127.0.0.1'
BITMAPIST_SERVER_PORT = 6400


@pytest.fixture(scope='session', autouse=True, params=['redis', 'bitmapist-server'])
def redis_server(request):
    """
    Fixture starting Redis or bitmapist-server process
    """
    if request.param == 'redis':
        host, port = REDIS_HOST, REDIS_PORT
    else:
        host, port = BITMAPIST_SERVER_HOST, BITMAPIST_SERVER_PORT

    if is_socket_open(host, port):
        yield host, port
    else:
        proc = start_server(request.param, host, port)
        wait_for_socket(host, port)
        yield host, port
        proc.terminate()


@pytest.fixture
def bitmapist(redis_server):
    conn = redis.StrictRedis(*redis_server)
    obj = bitmapist4.Bitmapist(conn, track_hourly=True)
    yield obj
    flushall(conn)


@pytest.fixture
def bitmapist_non_unique(redis_server):
    conn = redis.StrictRedis(*redis_server)
    obj = bitmapist4.Bitmapist(conn, track_hourly=True, track_unique=False)
    yield obj
    flushall(conn)


@pytest.fixture
def bitmapist_copy(redis_server):
    conn = redis.StrictRedis(*redis_server)
    obj = bitmapist4.Bitmapist(conn)
    yield obj
    flushall(conn)


@pytest.fixture
def db1(redis_server):
    host, port = redis_server
    conn = redis.StrictRedis(host, port, db=1)
    obj = bitmapist4.Bitmapist(conn)
    yield obj
    flushall(conn)


def flushall(conn):
    """
    bitmapist-server-compatible command to delete all keys from the server
    """
    keys = conn.keys('*')
    if keys:
        conn.delete(*keys)


def start_server(server_type, host, port):
    if server_type == 'redis':
        return start_redis_server(host, port)
    else:
        return start_bitmapist_server(host, port)


def start_redis_server(host, port):
    """
    Helper function starting Redis server
    """
    devzero = open(os.devnull, 'r')
    devnull = open(os.devnull, 'w')
    proc = subprocess.Popen(
        ['redis-server', '--bind', host, '--port', str(port)],
        stdin=devzero,
        stdout=devnull,
        stderr=devnull,
        close_fds=True)
    atexit.register(lambda: proc.terminate())
    return proc


def start_bitmapist_server(host, port):
    """
    Helper function starting bitmapist server
    """
    devzero = open(os.devnull, 'r')
    devnull = open(os.devnull, 'w')
    proc = subprocess.Popen(
        ['bitmapist-server', '-addr', '{}:{}'.format(host, port)],
        stdin=devzero,
        stdout=devnull,
        stderr=devnull,
        close_fds=True)
    atexit.register(lambda: proc.terminate())
    return proc


def is_socket_open(host, porto):
    """
    Helper function which tests is the socket open
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.1)
    ok = sock.connect_ex((host, porto)) == 0
    sock.close()
    return ok


def wait_for_socket(host, porto, seconds=3):
    """
    Check if socket is up for :param:`seconds` sec, raise an error otherwise
    """
    polling_interval = 0.2
    iterations = int(seconds / polling_interval)

    time.sleep(polling_interval)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.1)
    for _ in range(iterations):
        time.sleep(polling_interval)
        result = sock.connect_ex((host, porto))
        if result == 0:
            sock.close()
            break
    else:
        raise RuntimeError(
            'Service at %s:%d is unreachable' % (host, porto))
