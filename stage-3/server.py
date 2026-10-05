"""Single-process HTTP service with serializable, prepare-before-publish writes."""
import gzip
import os
import re
import socket
import socketserver
import sys
import threading
import time
import traceback
import zlib
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import exactjson as j
import domain


class PreparedBody:
    """Fully validated JSON output with shared, bounded-size zero blocks."""
    def __init__(self, parts):
        self.parts = tuple(p if isinstance(p, j.ZeroRun) else p.encode('ascii') for p in parts)
        self.length = sum(p.count if isinstance(p, j.ZeroRun) else len(p) for p in self.parts)

    def blocks(self):
        zeros = b'0' * (256 * 1024)
        for part in self.parts:
            if isinstance(part, j.ZeroRun):
                left = part.count
                while left:
                    size = min(left, len(zeros))
                    yield zeros[:size]
                    left -= size
            else:
                yield part

    def compressed(self):
        compressor = zlib.compressobj(1, zlib.DEFLATED, 31)
        parts = [compressor.compress(block) for block in self.blocks()]
        parts.append(compressor.flush())
        return b''.join(parts)


def sparse_output(value):
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, j.IntegerSum):
            return True
        if type(item) is dict:
            stack.extend(item.values())
        elif type(item) is list:
            stack.extend(item)
    return False


class Store:
    def __init__(self):
        self.lock = threading.RLock()
        self.state = domain.empty_state()

    def prepare(self, candidate, response, compressed):
        # These independently named preparation steps are ordinary production work,
        # and can be fault-injected by source-level verification before publication.
        encoded = (PreparedBody(j.chunks(response, sparse=True)) if sparse_output(response)
                   else j.dumps(response) if response is not None else b'')
        if candidate is not None:
            for _ in j.chunks(candidate):
                pass
        wire = (encoded.compressed() if isinstance(encoded, PreparedBody) else
                gzip.compress(encoded, compresslevel=1, mtime=0)) if compressed and encoded else encoded
        return wire

    def request(self, method, path, query, headers, body):
        with self.lock:
            status, response, candidate = domain.dispatch(self.state, method, path, query, headers, body)
            compressed = 'gzip' in headers.get('accept-encoding', '').lower() and status != 204
            wire = self.prepare(candidate, response, compressed)
            # The only irreversible mutation in the service. No fallible preparation
            # follows this assignment. Network loss occurs outside this transaction.
            if candidate is not None:
                self.state = candidate
            return status, wire, compressed


STORE = Store()
WEB = Path(__file__).resolve().parent / 'web'
ASSETS = {path: ((WEB / 'index.html').read_bytes(), 'text/html; charset=utf-8')
          for path in ('/', '/signup', '/login', '/lookup')}
ASSETS.update({path: ((WEB / filename).read_bytes(), mime) for path, filename, mime in (
    ('/assets/app.js', 'app.js', 'text/javascript; charset=utf-8'),
    ('/assets/style.css', 'style.css', 'text/css; charset=utf-8'))})
HEADER_NAME = re.compile(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")
METHOD = re.compile(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")


class RequestReader:
    """One absolute deadline, checked around each single socket receive.

    Buffered file read/readline may perform many receives while renewing the same
    idle timeout. This reader returns to our deadline check after every receive.
    """
    def __init__(self, connection, deadline):
        self.connection, self.deadline = connection, deadline
        self.buffer = bytearray()

    def remaining(self):
        value = self.deadline - time.monotonic()
        domain.require(value > 0, 'malformed_request', 400)
        return value

    def receive(self, maximum):
        self.connection.settimeout(self.remaining())
        data = self.connection.recv(maximum)
        domain.require(bool(data), 'malformed_request', 400)
        self.remaining()
        return data

    def line(self):
        while True:
            self.remaining()
            end = self.buffer.find(b'\n')
            if end >= 0:
                value = bytes(self.buffer[:end + 1])
                del self.buffer[:end + 1]
                domain.require(value.endswith(b'\r\n') and len(value) <= 65536, 'malformed_request', 400)
                return value[:-2]
            domain.require(len(self.buffer) < 65536, 'malformed_request', 400)
            self.buffer.extend(self.receive(65536 - len(self.buffer)))

    def body(self, length):
        result = bytearray(self.buffer[:length])
        del self.buffer[:length]
        while len(result) < length:
            result.extend(self.receive(min(65536, length - len(result))))
        self.remaining()
        return bytes(result)


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        deadline = time.monotonic() + 3
        method = None
        mime = 'application/json; charset=utf-8'
        try:
            reader = RequestReader(self.connection, deadline)
            first = reader.line().split(b' ')
            domain.require(len(first) == 3, 'malformed_request', 400)
            verb, target, version = first
            domain.require(METHOD.fullmatch(verb) and version in (b'HTTP/1.0', b'HTTP/1.1'), 'malformed_request', 400)
            domain.require(target.startswith(b'/') and all(32 < c < 127 for c in target), 'malformed_request', 400)
            method = verb.decode('ascii')
            headers, count = {}, 0
            while True:
                value = reader.line()
                if not value:
                    break
                count += len(value) + 2
                domain.require(count <= 65536 and b':' in value, 'malformed_request', 400)
                key, value = value.split(b':', 1)
                domain.require(HEADER_NAME.fullmatch(key), 'malformed_request', 400)
                domain.require(all(c == 9 or 32 <= c <= 126 or c >= 128 for c in value), 'malformed_request', 400)
                key, value = key.decode('ascii').lower(), value.strip(b' \t').decode('latin1')
                domain.require(key not in headers, 'malformed_request', 400)
                headers[key] = value
            domain.require('transfer-encoding' not in headers, 'malformed_request', 400)
            length = headers.get('content-length', '0')
            domain.require(re.fullmatch('[0-9]+', length), 'malformed_request', 400)
            length = int(length)
            if headers.get('expect', '').lower() == '100-continue':
                self.wfile.write(b'HTTP/1.1 100 Continue\r\n\r\n')
                self.wfile.flush()
            raw = reader.body(length)
            parsed = j.loads(raw) if raw else {}
            if method in ('POST', 'PATCH', 'PUT'):
                domain.obj(parsed)
            address = urlsplit(target.decode('ascii'))
            domain.require(not address.fragment, 'malformed_request', 400)
            # Route separators stay encoded until individual captures are decoded;
            # opaque restaurant IDs may themselves contain a slash.
            path = address.path
            query = dict(parse_qsl(address.query, keep_blank_values=True, encoding='utf-8', errors='strict'))
            if method in ('GET', 'HEAD') and path in ASSETS:
                wire, mime = ASSETS[path]
                status, compressed = 200, False
            else:
                status, wire, compressed = STORE.request(method, path, query, headers, parsed)
        except domain.Fault as err:
            status, wire, compressed = err.status, j.dumps({'error': {'code': err.code, 'message': err.message}}), False
        except (ValueError, UnicodeError, OSError, OverflowError):
            status, wire, compressed = 400, j.dumps({'error': {'code': 'malformed_request', 'message': 'Invalid request framing or JSON'}}), False
        except Exception:
            traceback.print_exc(file=sys.stderr)
            status, wire, compressed = 422, j.dumps({'error': {'code': 'validation_failed', 'message': 'Request could not be prepared'}}), False
        try:
            self.connection.settimeout(4)
            phrases = {200: 'OK', 201: 'Created', 204: 'No Content', 400: 'Bad Request', 401: 'Unauthorized',
                       403: 'Forbidden', 404: 'Not Found', 409: 'Conflict', 422: 'Unprocessable Content'}
            length = wire.length if isinstance(wire, PreparedBody) else len(wire)
            head = f'HTTP/1.1 {status} {phrases.get(status, "Error")}\r\nContent-Type: {mime}\r\nContent-Length: {length}\r\nConnection: close\r\nX-Content-Type-Options: nosniff\r\nCache-Control: no-store\r\n'
            if mime.startswith('text/html'):
                head += "Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; base-uri 'self'; frame-ancestors 'none'\r\n"
            if compressed:
                head += 'Content-Encoding: gzip\r\nVary: Accept-Encoding\r\n'
            self.wfile.write(head.encode('ascii') + b'\r\n')
            if method != 'HEAD':
                for block in wire.blocks() if isinstance(wire, PreparedBody) else (wire,):
                    self.wfile.write(block)
            self.wfile.flush()
        except OSError:
            pass
        # Deliberately no keep-alive: unread/rejected bytes cannot be another request.


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 128


if __name__ == '__main__':
    with Server(('0.0.0.0', int(os.environ.get('PORT', '8080'))), Handler) as server:
        print('Juniper Tablekeeper Stage 2 ready', flush=True)
        server.serve_forever()
