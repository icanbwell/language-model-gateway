from urllib.parse import urlparse
from typing import Set, Optional
import ipaddress


class URLValidator:
    # Cloud metadata endpoints and dangerous hosts
    BLOCKED_HOSTS = {
        "169.254.169.254",
        "metadata.google.internal",
        "metadata",
        "metadata.azure.com",
        "metadata.packet.net",
    }

    # Private IP ranges
    PRIVATE_RANGES = [
        ipaddress.ip_network("127.0.0.0/8"),  # Loopback
        ipaddress.ip_network("10.0.0.0/8"),  # Private
        ipaddress.ip_network("172.16.0.0/12"),  # Private
        ipaddress.ip_network("192.168.0.0/16"),  # Private
        ipaddress.ip_network("169.254.0.0/16"),  # Link-local (AWS metadata)
        ipaddress.ip_network("::1/128"),  # IPv6 loopback
        ipaddress.ip_network("fc00::/7"),  # IPv6 private
        ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
    ]

    @classmethod
    def _is_subdomain_of_allowed(cls, hostname: str, allowed_domains: Set[str]) -> bool:
        """
        Check if hostname matches or is a subdomain of any allowed domain
        """
        hostname_lower = hostname.lower()

        for allowed_domain in allowed_domains:
            allowed_lower = allowed_domain.lower()

            # Exact match (works for both domains and service names)
            if hostname_lower == allowed_lower:
                return True

            # Subdomain match (ends with .allowed_domain)
            # Only applies to domains with dots
            if "." in allowed_lower and hostname_lower.endswith(f".{allowed_lower}"):
                return True

        return False

    @classmethod
    def _is_private_ip(cls, hostname: str) -> tuple[bool, Optional[str]]:
        """Check if hostname is a private IP address"""
        try:
            ip = ipaddress.ip_address(hostname)

            for private_range in cls.PRIVATE_RANGES:
                if ip in private_range:
                    return (
                        True,
                        f"Private IP address blocked: {hostname} in {private_range}",
                    )

            return False, None

        except ValueError:
            # Not an IP address
            return False, None

    @classmethod
    def validate(
            cls,
            url: str,
            allowed_domains: Set[str],
            allowed_internal_services: Optional[Set[str]] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate URL against allowed domains with SSRF protection

        Args:
            url: The URL to validate
            allowed_domains: Set of allowed public domains (e.g., {'bwell.com', 'example.org'})
                           Subdomains are automatically allowed
            allowed_internal_services: Set of explicitly allowed internal service names
                                      (e.g., {'test-mcp-server', 'my-service'})
                                      These bypass private IP checks

        Returns:
            Tuple of (is_valid, error_message)
        """
        if allowed_internal_services is None:
            allowed_internal_services = set()

        try:
            parsed = urlparse(url)

            # Check scheme
            if parsed.scheme not in ("http", "https"):
                return (
                    False,
                    f"Invalid scheme: {parsed.scheme}. Only http/https allowed",
                )

            hostname = parsed.hostname
            if not hostname:
                return False, "Missing hostname"

            hostname_lower = hostname.lower()

            # Check if it's an explicitly allowed internal service (bypass other checks)
            if hostname_lower in {s.lower() for s in allowed_internal_services}:
                return True, None

            # Check against blocked hosts (metadata endpoints)
            if hostname_lower in cls.BLOCKED_HOSTS:
                return False, f"Blocked hostname: {hostname}"

            # Check if hostname is an IP address and if it's private
            is_private, reason = cls._is_private_ip(hostname)
            if is_private:
                return False, reason

            # Check domain allowlist
            if not cls._is_subdomain_of_allowed(hostname, allowed_domains):
                return False, f"Domain not in allowlist: {hostname}"

            return True, None

        except Exception as e:
            return False, f"URL parsing error: {str(e)}"
