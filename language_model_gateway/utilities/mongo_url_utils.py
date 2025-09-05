import urllib.parse


class MongoUrlHelpers:
    @staticmethod
    def add_credentials_to_mongo_url(
        *, mongo_url: str, username: str | None, password: str | None
    ) -> str:
        """
        Adds username and password to a MongoDB connection string.
        Args:
            mongo_url (str): Original MongoDB connection string (e.g., 'mongodb://mongo:27017?appName=fhir-server')
            username (str): MongoDB username
            password (str): MongoDB password
        Returns:
            str: Updated connection string with credentials
        """

        if not username or not password:
            return mongo_url

        # Parse the URL
        parsed = urllib.parse.urlparse(mongo_url)
        # URL-encode username and password
        username = urllib.parse.quote_plus(username)
        password = urllib.parse.quote_plus(password)
        # Build netloc with credentials
        if "@" in parsed.netloc:
            # Already has credentials, replace them
            host = parsed.netloc.split("@")[1]
        else:
            host = parsed.netloc
        netloc = f"{username}:{password}@{host}"
        # Reconstruct the URL
        new_url = urllib.parse.urlunparse(
            (
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )
        return new_url
