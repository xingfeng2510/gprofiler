from typing import List

from dataclasses import dataclass


@dataclass
class EnrichmentOptions:
    """
    Profile enrichment options.
    """

    profile_api_version: str  # profile protocol version. v1 does not support container_names and application_metadata.
    container_names: bool  # Include container names for each stack in result profile
    application_identifiers: bool  # Attempt to produce & include appid frames for each stack in result profile
    application_identifier_args_filters: List[str]  # A list of regex filters to add cmdline arguments to the app id
    application_metadata: bool  # Include specialized metadata per application, e.g for Python - the Python version
