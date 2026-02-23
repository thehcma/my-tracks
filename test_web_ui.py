"""Tests for web_ui views."""

import re
from pathlib import Path
from unittest.mock import patch

import netifaces
import pytest
from django.test import Client
from hamcrest import (assert_that, contains_string, equal_to, greater_than,
                      has_item, has_key, has_length, instance_of, is_, is_not,
                      not_none)
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
