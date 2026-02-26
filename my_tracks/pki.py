"""
PKI utilities for certificate generation and key encryption.

Provides functions for generating CA certificates and encrypting/decrypting
private keys at rest using Fernet symmetric encryption derived from
Django's SECRET_KEY.
"""
import base64
import hashlib
from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
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
