"""Tests for PKI (Certificate Authority) functionality."""
from typing import Any

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from hamcrest import (assert_that, contains_string, equal_to, greater_than,
                      has_key, has_length, is_, is_not, not_none, starts_with)
from rest_framework import status
from rest_framework.test import APIClient

from my_tracks.models import CertificateAuthority
from my_tracks.pki import (ALLOWED_KEY_SIZES, decrypt_private_key,
                           encrypt_private_key, generate_ca_certificate,
                           get_certificate_expiry, get_certificate_fingerprint,
                           get_certificate_subject)


@pytest.mark.django_db
class TestPKICryptoUtilities:
    """Test low-level PKI crypto functions."""

    def test_generate_ca_certificate_returns_pem(self) -> None:
        """Test that generate_ca_certificate returns valid PEM data."""
        cert_pem, key_pem = generate_ca_certificate()
        assert_that(cert_pem, is_(not_none()))
        assert_that(key_pem, is_(not_none()))
        assert_that(cert_pem.decode(), starts_with("-----BEGIN CERTIFICATE-----"))
        assert_that(key_pem.decode(), starts_with("-----BEGIN PRIVATE KEY-----"))

    def test_generate_ca_certificate_custom_cn(self) -> None:
        """Test CA generation with custom common name."""
        cert_pem, _ = generate_ca_certificate(common_name="Test CA")
        subject = get_certificate_subject(cert_pem)
        assert_that(subject, equal_to("Test CA"))

    def test_generate_ca_certificate_is_ca(self) -> None:
        """Test that generated certificate has CA basic constraint."""
        cert_pem, _ = generate_ca_certificate()
        cert = x509.load_pem_x509_certificate(cert_pem)
        bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
        assert_that(bc.value.ca, is_(True))

    def test_generate_ca_certificate_key_usage(self) -> None:
        """Test that CA cert has correct key usage flags."""
        cert_pem, _ = generate_ca_certificate()
        cert = x509.load_pem_x509_certificate(cert_pem)
        ku = cert.extensions.get_extension_for_class(x509.KeyUsage)
        assert_that(ku.value.digital_signature, is_(True))
        assert_that(ku.value.key_cert_sign, is_(True))
        assert_that(ku.value.crl_sign, is_(True))

    def test_generate_ca_certificate_custom_validity(self) -> None:
        """Test CA generation with custom validity period."""
        cert_pem, _ = generate_ca_certificate(validity_days=365)
        cert = x509.load_pem_x509_certificate(cert_pem)
        delta = cert.not_valid_after_utc - cert.not_valid_before_utc
        assert_that(delta.days, equal_to(365))

    def test_encrypt_decrypt_roundtrip(self) -> None:
        """Test that encrypting then decrypting recovers the original data."""
        _, key_pem = generate_ca_certificate()
        encrypted = encrypt_private_key(key_pem)
        assert_that(encrypted, is_not(equal_to(key_pem)))
        decrypted = decrypt_private_key(encrypted)
        assert_that(decrypted, equal_to(key_pem))

    def test_get_certificate_fingerprint_format(self) -> None:
        """Test fingerprint is colon-separated hex string."""
        cert_pem, _ = generate_ca_certificate()
        fp = get_certificate_fingerprint(cert_pem)
        parts = fp.split(":")
        assert_that(parts, has_length(32))
        for part in parts:
            assert_that(len(part), equal_to(2))

    def test_generate_ca_certificate_custom_key_size(self) -> None:
        """Test CA generation with custom key size."""
        cert_pem, _ = generate_ca_certificate(key_size=2048)
        cert = x509.load_pem_x509_certificate(cert_pem)
        public_key = cert.public_key()
        assert_that(public_key.key_size, equal_to(2048))

    def test_generate_ca_certificate_default_key_size(self) -> None:
        """Test CA generation uses 4096-bit key by default."""
        cert_pem, _ = generate_ca_certificate()
        cert = x509.load_pem_x509_certificate(cert_pem)
        public_key = cert.public_key()
        assert_that(public_key.key_size, equal_to(4096))

    def test_generate_ca_certificate_invalid_key_size(self) -> None:
        """Test that invalid key size raises ValueError."""
        from hamcrest import calling, raises
        assert_that(
            calling(generate_ca_certificate).with_args(key_size=1024),
            raises(ValueError, "Expected key_size in"),
        )

    def test_allowed_key_sizes_constant(self) -> None:
        """Test ALLOWED_KEY_SIZES contains expected values."""
        assert_that(ALLOWED_KEY_SIZES, equal_to((2048, 3072, 4096)))

    def test_get_certificate_expiry_returns_datetime(self) -> None:
        """Test expiry extraction returns a datetime."""
        cert_pem, _ = generate_ca_certificate(validity_days=365)
        expiry = get_certificate_expiry(cert_pem)
        assert_that(expiry, is_(not_none()))


@pytest.mark.django_db
class TestCertificateAuthorityModel:
    """Test the CertificateAuthority model."""

    def test_create_ca_model(self) -> None:
        """Test creating a CA record in the database."""
        cert_pem, key_pem = generate_ca_certificate(common_name="Test CA", key_size=2048)
        encrypted_key = encrypt_private_key(key_pem)

        ca = CertificateAuthority.objects.create(
            certificate_pem=cert_pem.decode(),
            encrypted_private_key=encrypted_key,
            common_name=get_certificate_subject(cert_pem),
            fingerprint=get_certificate_fingerprint(cert_pem),
            key_size=2048,
            not_valid_before=get_certificate_expiry(cert_pem),
            not_valid_after=get_certificate_expiry(cert_pem),
            is_active=True,
        )
        assert_that(ca.pk, is_(not_none()))
        assert_that(ca.common_name, equal_to("Test CA"))
        assert_that(ca.key_size, equal_to(2048))
        assert_that(ca.is_active, is_(True))

    def test_create_ca_model_default_key_size(self) -> None:
        """Test that CA model defaults to 4096-bit key size."""
        cert_pem, key_pem = generate_ca_certificate(common_name="Default Key")
        encrypted_key = encrypt_private_key(key_pem)

        ca = CertificateAuthority.objects.create(
            certificate_pem=cert_pem.decode(),
            encrypted_private_key=encrypted_key,
            common_name="Default Key",
            fingerprint=get_certificate_fingerprint(cert_pem),
            not_valid_before=get_certificate_expiry(cert_pem),
            not_valid_after=get_certificate_expiry(cert_pem),
            is_active=True,
        )
        assert_that(ca.key_size, equal_to(4096))

    def test_ca_str_representation(self) -> None:
        """Test __str__ of CertificateAuthority."""
        cert_pem, key_pem = generate_ca_certificate(common_name="My CA")
        encrypted_key = encrypt_private_key(key_pem)

        ca = CertificateAuthority.objects.create(
            certificate_pem=cert_pem.decode(),
            encrypted_private_key=encrypted_key,
            common_name="My CA",
            fingerprint=get_certificate_fingerprint(cert_pem),
            not_valid_before=get_certificate_expiry(cert_pem),
            not_valid_after=get_certificate_expiry(cert_pem),
            is_active=True,
        )
        assert_that(str(ca), equal_to("My CA (active)"))
        ca.is_active = False
        assert_that(str(ca), equal_to("My CA"))

    def test_decrypt_stored_key(self) -> None:
        """Test that a stored encrypted key can be decrypted."""
        cert_pem, key_pem = generate_ca_certificate()
        encrypted_key = encrypt_private_key(key_pem)

        ca = CertificateAuthority.objects.create(
            certificate_pem=cert_pem.decode(),
            encrypted_private_key=encrypted_key,
            common_name="Test CA",
            fingerprint=get_certificate_fingerprint(cert_pem),
            not_valid_before=get_certificate_expiry(cert_pem),
            not_valid_after=get_certificate_expiry(cert_pem),
        )

        ca.refresh_from_db()
        decrypted = decrypt_private_key(bytes(ca.encrypted_private_key))
        assert_that(decrypted, equal_to(key_pem))


@pytest.mark.django_db
class TestCertificateAuthorityAPI:
    """Test CA management REST API endpoints."""

    def test_list_cas_empty(self, admin_api_client: APIClient) -> None:
        """Test GET /api/admin/pki/ca/ returns empty list initially."""
        response = admin_api_client.get('/api/admin/pki/ca/')
        assert_that(response.status_code, equal_to(status.HTTP_200_OK))
        assert_that(response.data, has_length(0))

    def test_create_ca(self, admin_api_client: APIClient) -> None:
        """Test POST /api/admin/pki/ca/ generates a new CA."""
        response = admin_api_client.post('/api/admin/pki/ca/', {
            'common_name': 'Test CA',
            'validity_days': 365,
        }, format='json')
        assert_that(response.status_code, equal_to(status.HTTP_201_CREATED))
        assert_that(response.data, has_key('id'))
        assert_that(response.data['common_name'], equal_to('Test CA'))
        assert_that(response.data['is_active'], is_(True))
        assert_that(response.data['fingerprint'], contains_string(':'))
        assert_that(response.data['certificate_pem'], starts_with('-----BEGIN CERTIFICATE-----'))

    def test_create_ca_with_defaults(self, admin_api_client: APIClient) -> None:
        """Test POST /api/admin/pki/ca/ with no parameters uses defaults."""
        response = admin_api_client.post('/api/admin/pki/ca/', {}, format='json')
        assert_that(response.status_code, equal_to(status.HTTP_201_CREATED))
        assert_that(response.data['common_name'], equal_to('My Tracks CA'))

    def test_create_ca_deactivates_previous(self, admin_api_client: APIClient) -> None:
        """Test that creating a new CA deactivates the previous one."""
        resp1 = admin_api_client.post('/api/admin/pki/ca/', {'common_name': 'CA 1'}, format='json')
        ca1_id = resp1.data['id']

        resp2 = admin_api_client.post('/api/admin/pki/ca/', {'common_name': 'CA 2'}, format='json')
        assert_that(resp2.status_code, equal_to(status.HTTP_201_CREATED))

        ca1 = CertificateAuthority.objects.get(pk=ca1_id)
        assert_that(ca1.is_active, is_(False))

        ca2 = CertificateAuthority.objects.get(pk=resp2.data['id'])
        assert_that(ca2.is_active, is_(True))

    def test_create_ca_invalid_validity(self, admin_api_client: APIClient) -> None:
        """Test that invalid validity_days is rejected."""
        response = admin_api_client.post('/api/admin/pki/ca/', {
            'validity_days': 'abc',
        }, format='json')
        assert_that(response.status_code, equal_to(status.HTTP_400_BAD_REQUEST))
        assert_that(response.data['error'], contains_string('validity_days'))

    def test_create_ca_validity_out_of_range(self, admin_api_client: APIClient) -> None:
        """Test that out-of-range validity_days is rejected."""
        response = admin_api_client.post('/api/admin/pki/ca/', {
            'validity_days': 0,
        }, format='json')
        assert_that(response.status_code, equal_to(status.HTTP_400_BAD_REQUEST))

        response = admin_api_client.post('/api/admin/pki/ca/', {
            'validity_days': 99999,
        }, format='json')
        assert_that(response.status_code, equal_to(status.HTTP_400_BAD_REQUEST))

    def test_create_ca_with_key_size(self, admin_api_client: APIClient) -> None:
        """Test POST /api/admin/pki/ca/ with explicit key_size."""
        response = admin_api_client.post('/api/admin/pki/ca/', {
            'common_name': 'Small Key CA',
            'validity_days': 365,
            'key_size': 2048,
        }, format='json')
        assert_that(response.status_code, equal_to(status.HTTP_201_CREATED))
        assert_that(response.data['key_size'], equal_to(2048))

    def test_create_ca_invalid_key_size(self, admin_api_client: APIClient) -> None:
        """Test that invalid key_size is rejected."""
        response = admin_api_client.post('/api/admin/pki/ca/', {
            'key_size': 1024,
        }, format='json')
        assert_that(response.status_code, equal_to(status.HTTP_400_BAD_REQUEST))
        assert_that(response.data['error'], contains_string('key_size'))

    def test_create_ca_non_integer_key_size(self, admin_api_client: APIClient) -> None:
        """Test that non-integer key_size is rejected."""
        response = admin_api_client.post('/api/admin/pki/ca/', {
            'key_size': 'abc',
        }, format='json')
        assert_that(response.status_code, equal_to(status.HTTP_400_BAD_REQUEST))
        assert_that(response.data['error'], contains_string('key_size'))

    def test_create_ca_default_key_size_in_response(self, admin_api_client: APIClient) -> None:
        """Test that default key_size is 4096 in API response."""
        response = admin_api_client.post('/api/admin/pki/ca/', {}, format='json')
        assert_that(response.status_code, equal_to(status.HTTP_201_CREATED))
        assert_that(response.data['key_size'], equal_to(4096))

    def test_create_ca_empty_common_name(self, admin_api_client: APIClient) -> None:
        """Test that empty common_name is rejected."""
        response = admin_api_client.post('/api/admin/pki/ca/', {
            'common_name': '   ',
        }, format='json')
        assert_that(response.status_code, equal_to(status.HTTP_400_BAD_REQUEST))

    def test_list_cas_after_creation(self, admin_api_client: APIClient) -> None:
        """Test listing CAs after creating some."""
        admin_api_client.post('/api/admin/pki/ca/', {'common_name': 'CA 1'}, format='json')
        admin_api_client.post('/api/admin/pki/ca/', {'common_name': 'CA 2'}, format='json')

        response = admin_api_client.get('/api/admin/pki/ca/')
        assert_that(response.status_code, equal_to(status.HTTP_200_OK))
        assert_that(response.data, has_length(2))

    def test_get_active_ca(self, admin_api_client: APIClient) -> None:
        """Test GET /api/admin/pki/ca/active/ returns the active CA."""
        admin_api_client.post('/api/admin/pki/ca/', {'common_name': 'Active CA'}, format='json')
        response = admin_api_client.get('/api/admin/pki/ca/active/')
        assert_that(response.status_code, equal_to(status.HTTP_200_OK))
        assert_that(response.data['common_name'], equal_to('Active CA'))

    def test_get_active_ca_when_none(self, admin_api_client: APIClient) -> None:
        """Test GET /api/admin/pki/ca/active/ returns 404 when no active CA."""
        response = admin_api_client.get('/api/admin/pki/ca/active/')
        assert_that(response.status_code, equal_to(status.HTTP_404_NOT_FOUND))

    def test_destroy_ca(self, admin_api_client: APIClient) -> None:
        """Test DELETE /api/admin/pki/ca/{id}/ deactivates the CA."""
        resp = admin_api_client.post('/api/admin/pki/ca/', {'common_name': 'To Delete'}, format='json')
        ca_id = resp.data['id']

        response = admin_api_client.delete(f'/api/admin/pki/ca/{ca_id}/')
        assert_that(response.status_code, equal_to(status.HTTP_200_OK))

        ca = CertificateAuthority.objects.get(pk=ca_id)
        assert_that(ca.is_active, is_(False))

    def test_destroy_already_inactive_ca(self, admin_api_client: APIClient) -> None:
        """Test that deactivating an already inactive CA returns 400."""
        resp = admin_api_client.post('/api/admin/pki/ca/', {'common_name': 'CA'}, format='json')
        ca_id = resp.data['id']
        admin_api_client.delete(f'/api/admin/pki/ca/{ca_id}/')

        response = admin_api_client.delete(f'/api/admin/pki/ca/{ca_id}/')
        assert_that(response.status_code, equal_to(status.HTTP_400_BAD_REQUEST))

    def test_destroy_nonexistent_ca(self, admin_api_client: APIClient) -> None:
        """Test that deleting a nonexistent CA returns 404."""
        response = admin_api_client.delete('/api/admin/pki/ca/99999/')
        assert_that(response.status_code, equal_to(status.HTTP_404_NOT_FOUND))

    def test_download_ca_cert(self, admin_api_client: APIClient) -> None:
        """Test GET /api/admin/pki/ca/{id}/download/ returns PEM file."""
        resp = admin_api_client.post('/api/admin/pki/ca/', {'common_name': 'DL Test'}, format='json')
        ca_id = resp.data['id']

        response = admin_api_client.get(f'/api/admin/pki/ca/{ca_id}/download/')
        assert_that(response.status_code, equal_to(status.HTTP_200_OK))
        assert_that(response['Content-Type'], equal_to('application/x-pem-file'))
        assert_that(response['Content-Disposition'], contains_string('.pem'))
        assert_that(response.content.decode(), starts_with('-----BEGIN CERTIFICATE-----'))

    def test_download_nonexistent_ca(self, admin_api_client: APIClient) -> None:
        """Test downloading a nonexistent CA returns 404."""
        response = admin_api_client.get('/api/admin/pki/ca/99999/download/')
        assert_that(response.status_code, equal_to(status.HTTP_404_NOT_FOUND))


@pytest.mark.django_db
class TestCertificateAuthorityPermissions:
    """Test that CA endpoints are admin-only."""

    def test_list_forbidden_for_non_admin(self, auth_api_client: APIClient) -> None:
        """Test non-admin cannot list CAs."""
        response = auth_api_client.get('/api/admin/pki/ca/')
        assert_that(response.status_code, equal_to(status.HTTP_403_FORBIDDEN))

    def test_create_forbidden_for_non_admin(self, auth_api_client: APIClient) -> None:
        """Test non-admin cannot create CA."""
        response = auth_api_client.post('/api/admin/pki/ca/', {'common_name': 'X'}, format='json')
        assert_that(response.status_code, equal_to(status.HTTP_403_FORBIDDEN))

    def test_delete_forbidden_for_non_admin(self, auth_api_client: APIClient) -> None:
        """Test non-admin cannot delete CA."""
        response = auth_api_client.delete('/api/admin/pki/ca/1/')
        assert_that(response.status_code, equal_to(status.HTTP_403_FORBIDDEN))

    def test_active_forbidden_for_non_admin(self, auth_api_client: APIClient) -> None:
        """Test non-admin cannot access active CA endpoint."""
        response = auth_api_client.get('/api/admin/pki/ca/active/')
        assert_that(response.status_code, equal_to(status.HTTP_403_FORBIDDEN))

    def test_list_forbidden_for_unauthenticated(self) -> None:
        """Test unauthenticated cannot list CAs."""
        client = APIClient()
        response = client.get('/api/admin/pki/ca/')
        assert_that(response.status_code, equal_to(status.HTTP_403_FORBIDDEN))
