"""
Minimal LAN multiplayer transport for two-player games on the same network.

Protocol: each move is sent as a single newline-terminated JSON object:
    {"start": [r, c], "end": [r, c], "promotion": "Q"}

The host always plays White and listens for one client connection; the
client (joiner) always plays Black. All socket I/O runs on a background
thread; the GUI polls `NetworkSession.poll_incoming_move()` each frame.
"""

import json
import queue
import socket
import threading

DEFAULT_PORT = 5555


def get_local_ip():
    """Best-effort local LAN IP so a host can tell the other player what to enter."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except OSError:
        ip = socket.gethostbyname(socket.gethostname())
    finally:
        s.close()
    return ip


class NetworkError(Exception):
    pass


class NetworkSession:
    """Represents one side (host or client) of a LAN game connection."""

    def __init__(self):
        self.sock = None
        self.conn = None  # the active connected socket used for send/recv
        self.incoming = queue.Queue()
        self.status = "idle"       # idle | listening | connecting | connected | error | closed
        self.error_message = ""
        self.is_host = False
        self._recv_thread = None
        self._accept_thread = None

    # ------------------------------------------------------------------ #
    def host(self, port=DEFAULT_PORT):
        self.is_host = True
        self.status = "listening"
        self._accept_thread = threading.Thread(target=self._accept_worker, args=(port,), daemon=True)
        self._accept_thread.start()

    def _accept_worker(self, port):
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("0.0.0.0", port))
            server.listen(1)
            self.sock = server
            conn, _addr = server.accept()
            self.conn = conn
            self.status = "connected"
            self._start_recv_thread()
        except OSError as e:
            self.status = "error"
            self.error_message = str(e)

    # ------------------------------------------------------------------ #
    def join(self, host_ip, port=DEFAULT_PORT, timeout=8.0):
        self.is_host = False
        self.status = "connecting"
        self._accept_thread = threading.Thread(
            target=self._join_worker, args=(host_ip, port, timeout), daemon=True)
        self._accept_thread.start()

    def _join_worker(self, host_ip, port, timeout):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host_ip, port))
            sock.settimeout(None)
            self.conn = sock
            self.status = "connected"
            self._start_recv_thread()
        except OSError as e:
            self.status = "error"
            self.error_message = str(e)

    # ------------------------------------------------------------------ #
    def _start_recv_thread(self):
        self._recv_thread = threading.Thread(target=self._recv_worker, daemon=True)
        self._recv_thread.start()

    def _recv_worker(self):
        buffer = ""
        try:
            while True:
                data = self.conn.recv(4096)
                if not data:
                    break
                buffer += data.decode("utf-8")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        try:
                            self.incoming.put(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except OSError:
            pass
        finally:
            self.status = "closed"

    # ------------------------------------------------------------------ #
    def send_move(self, move):
        if self.conn is None:
            return
        payload = {
            "start": list(move.start),
            "end": list(move.end),
            "promotion": move.promotion_choice,
        }
        line = json.dumps(payload) + "\n"
        try:
            self.conn.sendall(line.encode("utf-8"))
        except OSError:
            self.status = "error"
            self.error_message = "Connection lost while sending move."

    def poll_incoming_move(self):
        try:
            return self.incoming.get_nowait()
        except queue.Empty:
            return None

    def close(self):
        for s in (self.conn, self.sock):
            if s is not None:
                try:
                    s.close()
                except OSError:
                    pass
        self.status = "closed"
