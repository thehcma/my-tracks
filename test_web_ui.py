"""Tests for web_ui views."""

import re
from pathlib import Path
from unittest.mock import patch

import netifaces
import pytest
from django.contrib.auth.models import User
from django.test import Client
from hamcrest import (assert_that, contains_string, equal_to, greater_than,
                      has_item, has_key, has_length, instance_of, is_, is_not,
                      not_, not_none)
from rest_framework import status


@pytest.mark.django_db
class TestWebUIViews:
    """Test the web UI view functions."""

    def test_home_view_returns_html(self, logged_in_client: Client) -> None:
        """Test that the home view returns HTML content."""
        response = logged_in_client.get('/')

        assert_that(response.status_code, equal_to(status.HTTP_200_OK))
        assert_that(response['Content-Type'], contains_string('text/html'))

    def test_home_view_contains_expected_elements(self, logged_in_client: Client) -> None:
        """Test that the home view contains expected HTML elements."""
        response = logged_in_client.get('/')

        content = response.content.decode('utf-8')
        assert_that(content, contains_string('<!DOCTYPE html>'))
        assert_that(content, contains_string('<title>My Tracks - OwnTracks Backend</title>'))
        assert_that(content, contains_string('leaflet'))  # Map library

    def test_home_view_contains_historic_controls(self, logged_in_client: Client) -> None:
        """Test that the home view contains date picker and time slider controls."""
        response = logged_in_client.get('/')

        content = response.content.decode('utf-8')
        assert_that(content, contains_string('id="historic-controls"'))
        assert_that(content, contains_string('id="historic-date"'))
        assert_that(content, contains_string('id="time-slider"'))
        assert_that(content, contains_string('id="time-slider-label"'))

    def test_home_view_no_cache_headers(self, logged_in_client: Client) -> None:
        """Test that the home view sets no-cache headers."""
        response = logged_in_client.get('/')

        assert_that(response['Cache-Control'], contains_string('no-cache'))
        assert_that(response['Pragma'], equal_to('no-cache'))
        assert_that(response['Expires'], equal_to('0'))

    def test_home_view_shows_username_and_logout(self, logged_in_client: Client) -> None:
        """Test that the home view shows the logged-in username and a POST logout form."""
        response = logged_in_client.get('/')

        content = response.content.decode('utf-8')
        assert_that(content, contains_string('class="user-menu"'))
        assert_that(content, contains_string('testuser'))
        assert_that(content, contains_string('action="/logout/"'))
        assert_that(content, contains_string('method="post"'))
        assert_that(content, contains_string('Logout'))
        assert_that(content, contains_string('id="hamburger-btn"'))

    def test_home_redirects_unauthenticated(self) -> None:
        """Test that unauthenticated users are redirected to login."""
        client = Client()
        response = client.get('/')
        assert_that(response.status_code, equal_to(status.HTTP_302_FOUND))
        assert_that(response.url, contains_string('/login/'))

    def test_health_endpoint_returns_ok(self) -> None:
        """Test that the health endpoint returns status ok (no auth required)."""
        client = Client()
        response = client.get('/health/')

        assert_that(response.status_code, equal_to(status.HTTP_200_OK))
        data = response.json()
        assert_that(data, has_key('status'))
        assert_that(data['status'], equal_to('ok'))

    def test_network_info_returns_expected_fields(self, logged_in_client: Client) -> None:
        """Test that network_info returns required fields."""
        response = logged_in_client.get('/network-info/', SERVER_PORT='8080')

        assert_that(response.status_code, equal_to(status.HTTP_200_OK))
        data = response.json()
        assert_that(data, has_key('hostname'))
        assert_that(data, has_key('local_ip'))
        assert_that(data, has_key('local_ips'))
        assert_that(data, has_key('port'))
        assert_that(data['port'], equal_to(8080))
        assert_that(data['local_ips'], instance_of(list))


@pytest.mark.django_db
class TestNetworkDiscovery:
    """Test network IP discovery functions."""

    def test_get_all_local_ips_returns_list(self) -> None:
        """Test that get_all_local_ips returns a list of non-loopback IPs."""
        from web_ui.views import get_all_local_ips

        ips = get_all_local_ips()
        assert_that(ips, instance_of(list))
        # Should not contain loopback addresses
        for ip in ips:
            assert_that(ip.startswith('127.'), is_(False))

    def test_get_all_local_ips_returns_sorted(self) -> None:
        """Test that get_all_local_ips returns sorted, deduplicated IPs."""
        from web_ui.views import get_all_local_ips

        ips = get_all_local_ips()
        assert_that(ips, equal_to(sorted(set(ips))))

    def test_get_all_local_ips_excludes_tunnel_interfaces(self) -> None:
        """IPs without a broadcast address (VPN/tunnels) are excluded."""
        from web_ui.views import get_all_local_ips

        mock_interfaces = {
            'en0': {netifaces.AF_INET: [{'addr': '192.168.1.10', 'broadcast': '192.168.1.255'}]},
            'utun0': {netifaces.AF_INET: [{'addr': '100.99.77.90'}]},
            'tun0': {netifaces.AF_INET: [{'addr': '10.8.0.1'}]},
        }

        with (
            patch('web_ui.views.netifaces.interfaces', return_value=list(mock_interfaces.keys())),
            patch('web_ui.views.netifaces.ifaddresses', side_effect=lambda iface: mock_interfaces[iface]),
        ):
            ips = get_all_local_ips()
            assert_that(ips, equal_to(['192.168.1.10']))

    def test_update_allowed_hosts_adds_new_ips(self) -> None:
        """Test that update_allowed_hosts adds IPs not already in ALLOWED_HOSTS."""
        from django.conf import settings

        from web_ui.views import update_allowed_hosts

        original = settings.ALLOWED_HOSTS.copy()
        try:
            test_ip = '10.99.99.99'
            if test_ip in settings.ALLOWED_HOSTS:
                settings.ALLOWED_HOSTS.remove(test_ip)
            update_allowed_hosts([test_ip])
            assert_that(settings.ALLOWED_HOSTS, has_item(test_ip))
        finally:
            settings.ALLOWED_HOSTS[:] = original

    def test_update_allowed_hosts_no_duplicates(self) -> None:
        """Test that update_allowed_hosts does not add duplicate IPs."""
        from django.conf import settings

        from web_ui.views import update_allowed_hosts

        original = settings.ALLOWED_HOSTS.copy()
        try:
            test_ip = '10.99.99.99'
            settings.ALLOWED_HOSTS.append(test_ip)
            count_before = settings.ALLOWED_HOSTS.count(test_ip)
            update_allowed_hosts([test_ip])
            count_after = settings.ALLOWED_HOSTS.count(test_ip)
            assert_that(count_after, equal_to(count_before))
        finally:
            settings.ALLOWED_HOSTS[:] = original


@pytest.mark.django_db
class TestNetworkState:
    """Test the NetworkState helper class."""

    def test_get_current_ip_returns_string(self) -> None:
        """Test that get_current_ip returns an IP address string."""
        from web_ui.views import NetworkState

        ip = NetworkState.get_current_ip()
        assert_that(ip, instance_of(str))
        assert_that(ip, has_length(greater_than(0)))

    def test_get_current_ips_returns_list(self) -> None:
        """Test that get_current_ips returns a list of IP strings."""
        from web_ui.views import NetworkState

        ips = NetworkState.get_current_ips()
        assert_that(ips, instance_of(list))
        for ip in ips:
            assert_that(ip, instance_of(str))
            assert_that(ip.startswith('127.'), is_(False))

    def test_check_and_update_ip_returns_tuple(self) -> None:
        """Test that check_and_update_ip returns (ip, changed) tuple."""
        from web_ui.views import NetworkState

        # Reset state for clean test
        NetworkState.last_known_ips = None

        ip, changed = NetworkState.check_and_update_ip()
        assert_that(ip, instance_of(str))
        assert_that(changed, instance_of(bool))
        # First call should not show change
        assert_that(changed, equal_to(False))

    def test_check_and_update_ips_detects_change(self) -> None:
        """Test that check_and_update_ips detects IP changes."""
        from web_ui.views import NetworkState

        # Set a fake previous IP list
        NetworkState.last_known_ips = ["192.168.0.1"]

        # Current IPs should be different (unless by coincidence)
        current_ips = NetworkState.get_current_ips()
        if set(current_ips) != {"192.168.0.1"}:
            ips, changed = NetworkState.check_and_update_ips()
            assert_that(changed, equal_to(True))

    def test_check_and_update_ips_no_change_when_same(self) -> None:
        """Test that check_and_update_ips shows no change when IPs are same."""
        from web_ui.views import NetworkState

        # Set current IPs as last known
        current_ips = NetworkState.get_current_ips()
        NetworkState.last_known_ips = current_ips

        ips, changed = NetworkState.check_and_update_ips()
        assert_that(changed, equal_to(False))
        assert_that(ips, equal_to(current_ips))


@pytest.mark.django_db
class TestMQTTEndpointDisplay:
    """Test MQTT endpoint display in web UI."""

    def test_home_view_shows_http_enabled(self, logged_in_client: Client) -> None:
        """Test that home view shows HTTP server as enabled."""
        response = logged_in_client.get('/')

        content = response.content.decode('utf-8')
        assert_that(content, contains_string('HTTP Server'))
        assert_that(content, contains_string('● Enabled'))

    def test_home_view_shows_mqtt_disabled_by_default(self, logged_in_client: Client) -> None:
        """Test that home view shows MQTT disabled when port < 0."""
        from unittest.mock import patch

        with patch('web_ui.views.get_mqtt_port', return_value=-1):
            response = logged_in_client.get('/')

        content = response.content.decode('utf-8')
        assert_that(content, contains_string('○ Disabled'))
        assert_that(content, contains_string('--mqtt-port 1883'))

    def test_home_view_shows_mqtt_enabled(self, logged_in_client: Client) -> None:
        """Test that home view shows MQTT info when enabled."""
        from unittest.mock import patch

        with (
            patch('web_ui.views.get_mqtt_port', return_value=1883),
            patch('web_ui.views.get_actual_mqtt_port', return_value=None),
        ):
            response = logged_in_client.get('/')

        content = response.content.decode('utf-8')
        assert_that(content, contains_string('● Enabled'))
        assert_that(content, contains_string('1883'))
        assert_that(content, contains_string('MQTT Broker'))

    def test_home_view_shows_actual_mqtt_port(self, logged_in_client: Client) -> None:
        """Test that home view shows actual port when OS-allocated."""
        from unittest.mock import patch

        with (
            patch('web_ui.views.get_mqtt_port', return_value=0),
            patch('web_ui.views.get_actual_mqtt_port', return_value=54321),
        ):
            response = logged_in_client.get('/')

        content = response.content.decode('utf-8')
        assert_that(content, contains_string('54321'))

    def test_home_view_shows_mqtt_config_instructions(self, logged_in_client: Client) -> None:
        """Test that home view shows MQTT configuration instructions when enabled."""
        from unittest.mock import patch

        with (
            patch('web_ui.views.get_mqtt_port', return_value=1883),
            patch('web_ui.views.get_actual_mqtt_port', return_value=None),
        ):
            response = logged_in_client.get('/')

        content = response.content.decode('utf-8')
        assert_that(content, contains_string('MQTT (Recommended)'))
        assert_that(content, contains_string('For MQTT Mode'))
        assert_that(content, contains_string('For HTTP Mode'))


# CSS custom properties that must be defined in both light and dark theme blocks.
# Keep in sync with REQUIRED_THEME_VARIABLES in theme.ts.
REQUIRED_CSS_VARIABLES = [
    '--bg-main',
    '--bg-left',
    '--text-main',
    '--text-secondary',
    '--text-left',
    '--border-color',
    '--endpoint-bg',
    '--endpoint-border',
    '--code-bg',
    '--log-entry-bg',
    '--log-entry-border',
    '--log-time-color',
    '--link-color',
    '--status-color',
    '--log-device-color',
    '--log-coords-color',
    '--right-header-color',
]

CSS_PATH = Path(__file__).parent / 'web_ui' / 'static' / 'web_ui' / 'css' / 'main.css'
HTML_PATH = Path(__file__).parent / 'web_ui' / 'templates' / 'web_ui' / 'home.html'


def _extract_css_block(css: str, selector: str) -> str:
    """Extract the content of a CSS block matching a selector.

    Finds the selector and extracts everything until the matching
    closing brace, handling nested braces correctly.
    """
    pattern = re.escape(selector) + r'\s*\{'
    match = re.search(pattern, css)
    if not match:
        return ''
    start = match.end()
    depth = 1
    pos = start
    while pos < len(css) and depth > 0:
        if css[pos] == '{':
            depth += 1
        elif css[pos] == '}':
            depth -= 1
        pos += 1
    return css[start:pos - 1]


class TestThemeCSS:
    """Validate that CSS defines all required variables for both themes."""

    def test_light_theme_block_exists(self) -> None:
        """CSS must have a [data-theme='light'] block."""
        css = CSS_PATH.read_text()
        block = _extract_css_block(css, '[data-theme="light"]')
        assert_that(block, is_not(equal_to('')))

    def test_dark_theme_block_exists(self) -> None:
        """CSS must have a [data-theme='dark'] block."""
        css = CSS_PATH.read_text()
        block = _extract_css_block(css, '[data-theme="dark"]')
        assert_that(block, is_not(equal_to('')))

    @pytest.mark.parametrize('variable', REQUIRED_CSS_VARIABLES)
    def test_light_theme_has_variable(self, variable: str) -> None:
        """Each required CSS variable must be defined in the light theme."""
        css = CSS_PATH.read_text()
        block = _extract_css_block(css, '[data-theme="light"]')
        assert_that(
            block,
            contains_string(f'{variable}:'),
        )

    @pytest.mark.parametrize('variable', REQUIRED_CSS_VARIABLES)
    def test_dark_theme_has_variable(self, variable: str) -> None:
        """Each required CSS variable must be defined in the dark theme."""
        css = CSS_PATH.read_text()
        block = _extract_css_block(css, '[data-theme="dark"]')
        assert_that(
            block,
            contains_string(f'{variable}:'),
        )

    def test_light_and_dark_use_different_bg_main(self) -> None:
        """Light and dark themes must have distinct --bg-main values."""
        css = CSS_PATH.read_text()
        light = _extract_css_block(css, '[data-theme="light"]')
        dark = _extract_css_block(css, '[data-theme="dark"]')

        light_bg = re.search(r'--bg-main:\s*([^;]+);', light)
        dark_bg = re.search(r'--bg-main:\s*([^;]+);', dark)

        assert_that(light_bg, is_(not_none()))
        assert_that(dark_bg, is_(not_none()))
        assert_that(
            light_bg.group(1).strip(),  # type: ignore[union-attr]
            is_not(equal_to(dark_bg.group(1).strip())),  # type: ignore[union-attr]
        )

    def test_light_and_dark_use_different_text_main(self) -> None:
        """Light and dark themes must have distinct --text-main values."""
        css = CSS_PATH.read_text()
        light = _extract_css_block(css, '[data-theme="light"]')
        dark = _extract_css_block(css, '[data-theme="dark"]')

        light_text = re.search(r'--text-main:\s*([^;]+);', light)
        dark_text = re.search(r'--text-main:\s*([^;]+);', dark)

        assert_that(light_text, is_(not_none()))
        assert_that(dark_text, is_(not_none()))
        assert_that(
            light_text.group(1).strip(),  # type: ignore[union-attr]
            is_not(equal_to(dark_text.group(1).strip())),  # type: ignore[union-attr]
        )


@pytest.mark.django_db
class TestThemeHTMLIntegration:
    """Validate that the HTML template supports theme toggling."""

    def test_template_has_theme_toggle_button(self) -> None:
        """HTML template must include the theme toggle button."""
        html = HTML_PATH.read_text()
        assert_that(html, contains_string('id="theme-toggle"'))

    def test_template_loads_css(self) -> None:
        """HTML template must load the main CSS stylesheet."""
        html = HTML_PATH.read_text()
        assert_that(html, contains_string("main.css"))

    def test_home_response_has_theme_toggle(self, logged_in_client: Client) -> None:
        """Rendered home page must contain the theme toggle button."""
        response = logged_in_client.get('/')
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('id="theme-toggle"'))

    def test_home_response_has_data_theme_support(self, logged_in_client: Client) -> None:
        """Rendered page must include JS that sets data-theme attribute."""
        response = logged_in_client.get('/')
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('/static/web_ui/js/main.'))


@pytest.mark.django_db
class TestAdminBadge:
    """Test admin badge display in the header."""

    def test_admin_user_sees_admin_badge(self, admin_logged_in_client: Client) -> None:
        """Admin users should see the admin badge in the header."""
        response = admin_logged_in_client.get('/')
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('class="admin-badge"'))
        assert_that(content, contains_string('admin'))

    def test_regular_user_does_not_see_admin_badge(self, logged_in_client: Client) -> None:
        """Regular users should not see the admin badge."""
        response = logged_in_client.get('/')
        content = response.content.decode('utf-8')
        assert_that(content, not_(contains_string('class="admin-badge"')))

    def test_hamburger_has_profile_link(self, logged_in_client: Client) -> None:
        """Hamburger menu should have a link to the profile page."""
        response = logged_in_client.get('/')
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('href="/profile/"'))


@pytest.mark.django_db
class TestProfilePage:
    """Test the user profile page."""

    def test_profile_page_renders(self, logged_in_client: Client) -> None:
        """Profile page should render for authenticated users."""
        response = logged_in_client.get('/profile/')
        assert_that(response.status_code, equal_to(status.HTTP_200_OK))
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('testuser'))

    def test_profile_page_redirects_unauthenticated(self) -> None:
        """Unauthenticated users should be redirected to login."""
        client = Client()
        response = client.get('/profile/')
        assert_that(response.status_code, equal_to(status.HTTP_302_FOUND))
        assert_that(response.url, contains_string('/login/'))

    def test_profile_shows_admin_badge_for_admin(self, admin_logged_in_client: Client) -> None:
        """Profile page shows Administrator badge for admin users."""
        response = admin_logged_in_client.get('/profile/')
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('Administrator'))
        assert_that(content, contains_string('role-badge admin'))

    def test_profile_shows_user_badge_for_regular_user(self, logged_in_client: Client) -> None:
        """Profile page shows User badge for regular users."""
        response = logged_in_client.get('/profile/')
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('role-badge user'))

    def test_profile_update_name(self, logged_in_client: Client, user: User) -> None:
        """Updating first and last name via the profile form."""
        response = logged_in_client.post('/profile/', {
            'form_type': 'profile',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': user.email,
        })
        assert_that(response.status_code, equal_to(status.HTTP_200_OK))
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('Profile updated successfully'))

        user.refresh_from_db()
        assert_that(user.first_name, equal_to('John'))
        assert_that(user.last_name, equal_to('Doe'))

    def test_profile_update_email(self, logged_in_client: Client, user: User) -> None:
        """Updating email via the profile form."""
        response = logged_in_client.post('/profile/', {
            'form_type': 'profile',
            'first_name': '',
            'last_name': '',
            'email': 'newemail@example.com',
        })
        assert_that(response.status_code, equal_to(status.HTTP_200_OK))

        user.refresh_from_db()
        assert_that(user.email, equal_to('newemail@example.com'))

    def test_password_change_success(self, logged_in_client: Client, user: User) -> None:
        """Changing password with correct current password."""
        response = logged_in_client.post('/profile/', {
            'form_type': 'password',
            'current_password': 'testpass123',
            'new_password': 'newSecureP@ss99',
            'confirm_password': 'newSecureP@ss99',
        })
        assert_that(response.status_code, equal_to(status.HTTP_200_OK))
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('Password changed successfully'))

        user.refresh_from_db()
        assert_that(user.check_password('newSecureP@ss99'), is_(True))

    def test_password_change_wrong_current_password(self, logged_in_client: Client) -> None:
        """Changing password with wrong current password should fail."""
        response = logged_in_client.post('/profile/', {
            'form_type': 'password',
            'current_password': 'wrongpassword',
            'new_password': 'newSecureP@ss99',
            'confirm_password': 'newSecureP@ss99',
        })
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('Current password is incorrect'))

    def test_password_change_mismatch(self, logged_in_client: Client) -> None:
        """Changing password with mismatched new passwords should fail."""
        response = logged_in_client.post('/profile/', {
            'form_type': 'password',
            'current_password': 'testpass123',
            'new_password': 'newSecureP@ss99',
            'confirm_password': 'differentP@ss99',
        })
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('New passwords do not match'))

    def test_password_change_too_short(self, logged_in_client: Client) -> None:
        """Changing password to something too short should fail."""
        response = logged_in_client.post('/profile/', {
            'form_type': 'password',
            'current_password': 'testpass123',
            'new_password': 'short',
            'confirm_password': 'short',
        })
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('at least 8 characters'))

    def test_password_change_keeps_session(self, logged_in_client: Client) -> None:
        """Changing password should not log the user out."""
        logged_in_client.post('/profile/', {
            'form_type': 'password',
            'current_password': 'testpass123',
            'new_password': 'newSecureP@ss99',
            'confirm_password': 'newSecureP@ss99',
        })
        response = logged_in_client.get('/profile/')
        assert_that(response.status_code, equal_to(status.HTTP_200_OK))

    def test_profile_has_back_to_map_link(self, logged_in_client: Client) -> None:
        """Profile page should have a link back to the map."""
        response = logged_in_client.get('/profile/')
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('Back to Map'))
        assert_that(content, contains_string('href="/"'))

    def test_profile_shows_member_since(self, logged_in_client: Client) -> None:
        """Profile page should show the member since date."""
        response = logged_in_client.get('/profile/')
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('Member since'))


@pytest.mark.django_db
class TestSessionConfiguration:
    """Test session configuration settings."""

    def test_session_cookie_age_is_7_days(self) -> None:
        """Session cookie age should be 7 days (604800 seconds)."""
        from django.conf import settings
        assert_that(settings.SESSION_COOKIE_AGE, equal_to(604800))

    def test_session_save_every_request(self) -> None:
        """Session should be saved on every request for sliding window expiry."""
        from django.conf import settings
        assert_that(settings.SESSION_SAVE_EVERY_REQUEST, is_(True))


@pytest.mark.django_db
class TestAdminPanel:
    """Test the admin panel page."""

    def test_admin_panel_renders_for_admin(self, admin_logged_in_client: Client) -> None:
        """Admin panel should render for staff users."""
        response = admin_logged_in_client.get('/admin-panel/')
        assert_that(response.status_code, equal_to(status.HTTP_200_OK))
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('Admin Panel'))
        assert_that(content, contains_string('Create User'))

    def test_admin_panel_rejected_for_regular_user(self, logged_in_client: Client) -> None:
        """Regular users should be redirected away from admin panel."""
        response = logged_in_client.get('/admin-panel/')
        assert_that(response.status_code, equal_to(status.HTTP_302_FOUND))

    def test_admin_panel_redirects_unauthenticated(self) -> None:
        """Unauthenticated users should be redirected to login."""
        client = Client()
        response = client.get('/admin-panel/')
        assert_that(response.status_code, equal_to(status.HTTP_302_FOUND))
        assert_that(response.url, contains_string('/login/'))

    def test_admin_panel_shows_user_list(
        self, admin_logged_in_client: Client, user: User, admin_user: User
    ) -> None:
        """Admin panel should show all users in a table."""
        response = admin_logged_in_client.get('/admin-panel/')
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('testuser'))
        assert_that(content, contains_string('admin'))
        assert_that(content, contains_string('user-table'))

    def test_admin_panel_create_user(self, admin_logged_in_client: Client) -> None:
        """Creating a user through the admin panel form."""
        response = admin_logged_in_client.post('/admin-panel/', {
            'form_type': 'create_user',
            'username': 'newperson',
            'email': 'new@test.com',
            'password': 'secureP@ss99',
            'first_name': 'Jane',
            'last_name': 'Doe',
        })
        assert_that(response.status_code, equal_to(status.HTTP_200_OK))
        content = response.content.decode('utf-8')
        assert_that(content, contains_string("created as user"))

        created = User.objects.get(username='newperson')
        assert_that(created.first_name, equal_to('Jane'))
        assert_that(created.last_name, equal_to('Doe'))
        assert_that(created.email, equal_to('new@test.com'))

    def test_admin_panel_create_admin_user(self, admin_logged_in_client: Client) -> None:
        """Creating an admin user through the admin panel form."""
        response = admin_logged_in_client.post('/admin-panel/', {
            'form_type': 'create_user',
            'username': 'newadmin',
            'email': 'admin2@test.com',
            'password': 'secureP@ss99',
            'is_admin': 'on',
        })
        assert_that(response.status_code, equal_to(status.HTTP_200_OK))
        content = response.content.decode('utf-8')
        assert_that(content, contains_string("created as administrator"))

        new_admin = User.objects.get(username='newadmin')
        assert_that(new_admin.is_staff, is_(True))
        assert_that(new_admin.is_superuser, is_(True))

    def test_admin_panel_create_user_missing_username(self, admin_logged_in_client: Client) -> None:
        """Creating a user without username shows error."""
        response = admin_logged_in_client.post('/admin-panel/', {
            'form_type': 'create_user',
            'username': '',
            'password': 'secureP@ss99',
        })
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('Username is required'))

    def test_admin_panel_create_user_missing_password(self, admin_logged_in_client: Client) -> None:
        """Creating a user without password shows error."""
        response = admin_logged_in_client.post('/admin-panel/', {
            'form_type': 'create_user',
            'username': 'someone',
            'password': '',
        })
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('Password is required'))

    def test_admin_panel_create_user_short_password(self, admin_logged_in_client: Client) -> None:
        """Creating a user with short password shows error."""
        response = admin_logged_in_client.post('/admin-panel/', {
            'form_type': 'create_user',
            'username': 'someone',
            'password': 'short',
        })
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('at least 8 characters'))

    def test_admin_panel_create_duplicate_user(
        self, admin_logged_in_client: Client, user: User
    ) -> None:
        """Creating a user with existing username shows error."""
        response = admin_logged_in_client.post('/admin-panel/', {
            'form_type': 'create_user',
            'username': 'testuser',
            'password': 'secureP@ss99',
        })
        content = response.content.decode('utf-8')
        assert_that(content, contains_string("already exists"))

    def test_hamburger_menu_shows_admin_panel_for_admin(self, admin_logged_in_client: Client) -> None:
        """Hamburger menu should contain admin panel link for admin users."""
        response = admin_logged_in_client.get('/')
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('id="hamburger-dropdown"'))
        assert_that(content, contains_string('Admin Panel'))
        assert_that(content, contains_string('href="/admin-panel/"'))

    def test_hamburger_menu_hides_admin_panel_for_regular_user(self, logged_in_client: Client) -> None:
        """Hamburger menu should not contain admin panel link for regular users."""
        response = logged_in_client.get('/')
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('id="hamburger-dropdown"'))
        assert_that(content, not_(contains_string('Admin Panel')))

    def test_hamburger_menu_shows_profile_link(self, logged_in_client: Client) -> None:
        """Hamburger menu should contain profile link for all users."""
        response = logged_in_client.get('/')
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('hamburger-item'))
        assert_that(content, contains_string('Profile'))

    def test_hamburger_menu_shows_logout(self, logged_in_client: Client) -> None:
        """Hamburger menu should contain logout option."""
        response = logged_in_client.get('/')
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('Logout'))

    def test_admin_panel_has_back_to_map_link(self, admin_logged_in_client: Client) -> None:
        """Admin panel should have a link back to the map."""
        response = admin_logged_in_client.get('/admin-panel/')
        content = response.content.decode('utf-8')
        assert_that(content, contains_string('Back to Map'))
        assert_that(content, contains_string('href="/"'))
