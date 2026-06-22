"""Configuration resolution for environment and fallback settings."""

import os
import sys
from typing import Optional

import mc_user_info as user_info
from dotenv import find_dotenv, load_dotenv

dotenv_path = find_dotenv(usecwd=True)
if dotenv_path:
    load_dotenv(dotenv_path=dotenv_path, override=False)
else:
    load_dotenv(override=False)


def resolve(name: str, default: Optional[object] = None) -> Optional[object]:
    """Return value from env/.env first, then mc_user_info, then default."""
    env_value = os.getenv(name)
    if env_value is not None and env_value != "":
        return env_value

    if user_info is not None and hasattr(user_info, name):
        config_value = getattr(user_info, name)
        if config_value is not None and config_value != "":
            return config_value

    return default


def normalize_emails(raw_value: Optional[object]) -> Optional[list[str]]:
    """Normalize approved user emails to a list."""
    if raw_value is None:
        return None

    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]

    if isinstance(raw_value, str):
        return [email.strip() for email in raw_value.split(",") if email.strip()]

    return [str(raw_value).strip()] if str(raw_value).strip() else None


def validate(bot_mode: bool, require_operational: bool = True) -> None:
    """Validate required configuration values and exit on missing values.

    When require_operational is False, skip validation (e.g. CLI help or demo report).
    When True, require IOS and Meraki settings; if bot_mode, also require Teams bot settings.
    """
    if not require_operational:
        return

    required_vars = [
        "IOS_USERNAME",
        "IOS_PASSWORD",
        "IOS_SECRET",
        "MERAKI_API_KEY",
        "MERAKI_ORG_NAME",
    ]

    if bot_mode:
        required_vars.extend(
            [
                "TEAMS_BOT_EMAIL",
                "TEAMS_BOT_TOKEN",
                "TEAMS_BOT_APP_NAME",
                "TEAMS_EMAILS",
            ]
        )

    missing_vars: list[str] = []
    for var_name in required_vars:
        value = resolve(var_name)
        if value is None:
            missing_vars.append(var_name)
            continue
        if isinstance(value, str) and value.strip() == "":
            missing_vars.append(var_name)
            continue
        if var_name == "TEAMS_EMAILS" and normalize_emails(value) in (None, []):
            missing_vars.append(var_name)

    if missing_vars:
        print(
            "Error: Missing required setting(s). "
            "Set them as environment variables, in a .env file, or in mc_user_info.py:"
        )
        for var_name in missing_vars:
            print(f"  - {var_name}")
        sys.exit(1)


IOS_USERNAME = resolve("IOS_USERNAME")
IOS_PASSWORD = resolve("IOS_PASSWORD")
IOS_SECRET = resolve("IOS_SECRET")
IOS_PORT = resolve("IOS_PORT", default=22)
MERAKI_API_KEY = resolve("MERAKI_API_KEY")
MERAKI_ORG_NAME = resolve("MERAKI_ORG_NAME")
TEAMS_BOT_EMAIL = resolve("TEAMS_BOT_EMAIL")
TEAMS_BOT_TOKEN = resolve("TEAMS_BOT_TOKEN")
TEAMS_BOT_APP_NAME = resolve("TEAMS_BOT_APP_NAME")
TEAMS_EMAILS = normalize_emails(resolve("TEAMS_EMAILS"))

if isinstance(IOS_PORT, str):
    try:
        IOS_PORT = int(IOS_PORT)
    except ValueError:
        print("Error: IOS_PORT must be a valid integer.")
        sys.exit(1)
