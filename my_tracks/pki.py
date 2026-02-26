"""
PKI utilities for certificate generation and key encryption.

Provides functions for generating CA and server certificates, and
encrypting/decrypting private keys at rest using Fernet symmetric encryption
derived from Django's SECRET_KEY.
"""
import base64
import hashlib
import ipaddress
from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from django.conf import settings


def _derive_fernet_key() -> bytes:
    """Derive a Fernet-compatible key from Django's SECRET_KEY."""
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_private_key(pem_data: bytes) -> bytes:
    """Encrypt a PEM-encoded private key for storage at rest."""
    fernet = Fernet(_derive_fernet_key())
    return fernet.encrypt(pem_data)


def decrypt_private_key(encrypted_data: bytes) -> bytes:
    """Decrypt a PEM-encoded private key from storage."""
    fernet = Fernet(_derive_fernet_key())
    return fernet.decrypt(encrypted_data)


ALLOWED_KEY_SIZES = (2048, 3072, 4096)


def generate_ca_certificate(
    common_name: str = "My Tracks CA",
    validity_days: int = 3650,
    key_size: int = 4096,
) -> tuple[bytes, bytes]:
    """
    Generate a self-signed CA certificate and private key.

    Args:
        common_name: Subject Common Name for the CA certificate.
        validity_days: Number of days the certificate is valid.
        key_size: RSA key size in bits (2048, 3072, or 4096).

    Returns:
        Tuple of (certificate_pem, private_key_pem) as bytes.

    Raises:
        ValueError: If key_size is not one of the allowed values.
    """
    if key_size not in ALLOWED_KEY_SIZES:
        raise ValueError(
            f"Expected key_size in {ALLOWED_KEY_SIZES}, got {key_size}"
        )
    key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "My Tracks"),
    ])

    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=validity_days))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )

    return cert_pem, key_pem


def get_certificate_fingerprint(cert_pem: bytes) -> str:
    """Get the SHA-256 fingerprint of a PEM-encoded certificate."""
    cert = x509.load_pem_x509_certificate(cert_pem)
    digest = cert.fingerprint(hashes.SHA256())
    return ":".join(f"{b:02X}" for b in digest)


def get_certificate_subject(cert_pem: bytes) -> str:
    """Get the subject common name of a PEM-encoded certificate."""
    cert = x509.load_pem_x509_certificate(cert_pem)
    cn_attrs = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    if cn_attrs:
        return str(cn_attrs[0].value)
    return str(cert.subject)


def get_certificate_expiry(cert_pem: bytes) -> datetime:
    """Get the expiry datetime of a PEM-encoded certificate."""
    cert = x509.load_pem_x509_certificate(cert_pem)
    return cert.not_valid_after_utc


def get_certificate_sans(cert_pem: bytes) -> list[str]:
    """Get the Subject Alternative Names from a PEM-encoded certificate."""
    cert = x509.load_pem_x509_certificate(cert_pem)
    try:
        san_ext = cert.extensions.get_extension_for_class(
            x509.SubjectAlternativeName
        )
    except x509.ExtensionNotFound:
        return []
    names: list[str] = []
    for name in san_ext.value.get_values_for_type(x509.DNSName):
        names.append(str(name))
    for addr in san_ext.value.get_values_for_type(x509.IPAddress):
        names.append(str(addr))
    return names


def generate_server_certificate(
    ca_cert_pem: bytes,
    ca_key_pem: bytes,
    common_name: str,
    san_entries: list[str],
    validity_days: int = 365,
    key_size: int = 4096,
) -> tuple[bytes, bytes]:
    """
    Generate a server certificate signed by the given CA.

    Args:
        ca_cert_pem: CA certificate in PEM format.
        ca_key_pem: CA private key in PEM format (unencrypted).
        common_name: Subject Common Name for the server certificate.
        san_entries: List of SAN entries (IP addresses and DNS names).
        validity_days: Number of days the certificate is valid.
        key_size: RSA key size in bits (2048, 3072, or 4096).

    Returns:
        Tuple of (certificate_pem, private_key_pem) as bytes.

    Raises:
        ValueError: If key_size is not allowed or san_entries is empty.
    """
    if key_size not in ALLOWED_KEY_SIZES:
        raise ValueError(
            f"Expected key_size in {ALLOWED_KEY_SIZES}, got {key_size}"
        )
    if not san_entries:
        raise ValueError("Expected at least one SAN entry, got empty list")

    ca_cert = x509.load_pem_x509_certificate(ca_cert_pem)
    ca_key = serialization.load_pem_private_key(ca_key_pem, password=None)
    if not isinstance(ca_key, RSAPrivateKey):
        raise ValueError("Expected RSA private key for CA")

    server_key = rsa.generate_private_key(
        public_exponent=65537, key_size=key_size
    )

    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "My Tracks"),
    ])

    san_objects: list[x509.GeneralName] = []
    for entry in san_entries:
        try:
            addr = ipaddress.ip_address(entry)
            san_objects.append(x509.IPAddress(addr))
        except ValueError:
            san_objects.append(x509.DNSName(entry))

    now = datetime.now(UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=validity_days))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName(san_objects),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(
                ca_key.public_key()
            ),
            critical=False,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(
                server_key.public_key()
            ),
            critical=False,
        )
    )

    cert = builder.sign(ca_key, hashes.SHA256())

    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = server_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )

    return cert_pem, key_pem
