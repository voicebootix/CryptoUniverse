import pytest
from app.core.config import Settings

@pytest.mark.parametrize(
    "input_value, expected",
    [
        ("", ["*"]),
        ("*", ["*"]),
        ("https://url1,https://url2", ["https://url1", "https://url2"]),
        ('["https://url1", "https://url2"]', ["https://url1", "https://url2"]),
        ("invalid json", ["invalid json"]),  # Fallback to split, but could enhance
    ]
)
def test_cors_origins_parsing(input_value, expected):
    settings = Settings(BACKEND_CORS_ORIGINS=input_value)
    assert settings.BACKEND_CORS_ORIGINS.split(',') == expected  # Adjust if using computed field
