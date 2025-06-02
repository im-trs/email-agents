import os
import re
import pytest

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.example')

def test_env_example_exists():
    assert os.path.exists(ENV_PATH), "'.env.example' file is missing"

def test_env_example_contents():
    with open(ENV_PATH, 'r') as f:
        content = f.read()
    # expected keys
    required_keys = [
        'EMAIL_USER',
        'EMAIL_PASSWORD',
        'IMAP_SERVER',
        'SMTP_SERVER'
    ]
    for key in required_keys:
        assert re.search(rf'^{key}=.*', content, re.MULTILINE), f"Missing {key} in .env.example"
