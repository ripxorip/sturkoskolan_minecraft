"""Minimal Minecraft RCON client.  python3 rcon.py 'command' ['command' ...]"""
import socket
import struct
import sys


class Rcon:
    def __init__(self, host="127.0.0.1", port=25598, password="sturko-build", timeout=600):
        self.s = socket.create_connection((host, port), timeout=timeout)
        self.rid = 0
        self._send(3, password)
        rid, _, _ = self._recv()
        if rid == -1:
            raise RuntimeError("RCON auth failed")

    def _send(self, typ, payload):
        self.rid += 1
        data = struct.pack("<ii", self.rid, typ) + payload.encode("utf-8") + b"\x00\x00"
        self.s.sendall(struct.pack("<i", len(data)) + data)

    def _recvn(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.s.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("closed")
            buf += chunk
        return buf

    def _recv(self):
        (n,) = struct.unpack("<i", self._recvn(4))
        data = self._recvn(n)
        rid, typ = struct.unpack("<ii", data[:8])
        return rid, typ, data[8:-2].decode("utf-8", "replace")

    def cmd(self, c):
        self._send(2, c)
        return self._recv()[2]


if __name__ == "__main__":
    r = Rcon()
    for c in sys.argv[1:]:
        print(f"> {c}\n{r.cmd(c)}")
