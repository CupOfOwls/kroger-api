"""request_sent for TLS failures, against a real TLS server on localhost

A TLS error can happen in the handshake, before the request is sent, or while
the response is read, after the request has reached the server. urllib3
reports both as SSLError, so only a rejected certificate, which can only fail
the handshake, may be reported as never sent.
"""
import datetime
import ipaddress
import os
import select
import socket
import ssl
import threading
import time

import pytest

x509 = pytest.importorskip("cryptography.x509")
from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from cryptography.x509.oid import NameOID  # noqa: E402

from kroger_api import KrogerAPI  # noqa: E402
from kroger_api.client import KrogerClient  # noqa: E402
from kroger_api.errors import APIConnectionError  # noqa: E402

CART_ITEM = [{"upc": "0001111041700", "quantity": 1, "modality": "PICKUP"}]


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("KROGER_TOKEN_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    for name in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NO_PROXY", "*")


@pytest.fixture
def certificate(tmp_path):
    """A self-signed certificate for localhost, as (cert_path, key_path)"""
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    cert_path, key_path = tmp_path / "cert.pem", tmp_path / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )
    )
    return str(cert_path), str(key_path)


def _listener():
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(10)
    return listener


def _serve_once(certificate, received, after="garbage"):
    """Accept one TLS connection and read one request, then break the connection

    after="garbage" writes bytes outside TLS, so the client's TLS layer fails
    while it reads the response; after="close" closes the connection without
    an answer. Either way the whole request has arrived. Returns the port.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(*certificate)
    listener = _listener()

    def serve():
        try:
            raw, _ = listener.accept()
        except OSError:
            return
        try:
            conn = context.wrap_socket(raw, server_side=True)
        except (ssl.SSLError, OSError):
            raw.close()
            return  # the client rejected the handshake
        with conn:
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = conn.recv(65536)
                if not chunk:
                    return
                data += chunk
            head, body = data.split(b"\r\n\r\n", 1)
            length = next(
                int(line.split(b":", 1)[1]) for line in head.split(b"\r\n") if line.lower().startswith(b"content-length")
            )
            while len(body) < length:
                body += conn.recv(65536)
            received.append(head.split(b"\r\n")[0].decode())
            if after == "garbage":
                # Write to the socket under the TLS layer, so the bytes are not a TLS record
                os.write(conn.fileno(), b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
            time.sleep(0.2)
        listener.close()

    threading.Thread(target=serve, daemon=True).start()
    return listener.getsockname()[1]


def _connect_proxy(target_port):
    """An HTTP proxy that tunnels one CONNECT request to target_port. Returns its port."""
    listener = _listener()

    def run():
        try:
            client, _ = listener.accept()
        except OSError:
            return
        data = b""
        while b"\r\n\r\n" not in data:
            data += client.recv(4096)
        upstream = socket.create_connection(("127.0.0.1", target_port))
        client.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
        sockets = [client, upstream]
        while True:
            readable, _, _ = select.select(sockets, [], [], 5)
            chunks = [(s, s.recv(65536)) for s in readable]
            if not readable or any(not chunk for _, chunk in chunks):
                break
            for s, chunk in chunks:
                (upstream if s is client else client).sendall(chunk)
        client.close()
        upstream.close()
        listener.close()

    threading.Thread(target=run, daemon=True).start()
    return listener.getsockname()[1]


def _closed_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _cart_add_error(port, monkeypatch):
    monkeypatch.setattr(KrogerClient, "BASE_URL", f"https://localhost:{port}")
    api = KrogerAPI(client_id="id", client_secret="secret", timeout=10)
    api.client.token_info = {"access_token": "user", "expires_at": time.time() + 1800}
    with pytest.raises(APIConnectionError) as excinfo:
        api.cart.add_to_cart(CART_ITEM)
    return excinfo.value


def test_tls_error_after_the_request_was_sent_leaves_the_outcome_unknown(certificate, monkeypatch):
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", certificate[0])
    received = []
    error = _cart_add_error(_serve_once(certificate, received), monkeypatch)
    assert received == ["PUT /v1/cart/add HTTP/1.1"]
    assert type(error.__cause__).__name__ == "SSLError"
    assert error.request_sent is None
    assert error.outcome_unknown is True


def test_rejected_certificate_means_the_request_was_never_sent(certificate, monkeypatch):
    # The client does not trust the self-signed certificate
    received = []
    error = _cart_add_error(_serve_once(certificate, received), monkeypatch)
    assert received == []
    assert "CERTIFICATE_VERIFY_FAILED" in error.message
    assert error.request_sent is False
    assert error.outcome_unknown is False


def test_connection_lost_after_sending_through_a_proxy_leaves_the_outcome_unknown(certificate, monkeypatch):
    # urllib3 reports this as ProxyError, like a proxy it could not use
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", certificate[0])
    received = []
    server_port = _serve_once(certificate, received, after="close")
    monkeypatch.delenv("NO_PROXY")
    monkeypatch.setenv("HTTPS_PROXY", f"http://127.0.0.1:{_connect_proxy(server_port)}")
    error = _cart_add_error(server_port, monkeypatch)
    assert received == ["PUT /v1/cart/add HTTP/1.1"]
    assert type(error.__cause__).__name__ == "ProxyError"
    assert error.request_sent is None
    assert error.outcome_unknown is True


def test_refused_proxy_connection_means_the_request_was_never_sent(monkeypatch):
    monkeypatch.delenv("NO_PROXY")
    monkeypatch.setenv("HTTPS_PROXY", f"http://127.0.0.1:{_closed_port()}")
    error = _cart_add_error(_closed_port(), monkeypatch)
    assert type(error.__cause__).__name__ == "ProxyError"
    assert error.request_sent is False
    assert error.outcome_unknown is False
