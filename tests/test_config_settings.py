"""Tests for configuration settings with TOML config file support."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.config.settings import (
    Settings,
    TomlConfigSettingsSource,
    get_config_path,
    create_default_config,
)


class TestGetConfigPath:
    """Tests for get_config_path function."""

    def test_returns_path_object(self):
        """Test that get_config_path returns a Path object."""
        result = get_config_path()
        assert isinstance(result, Path)

    def test_returns_correct_path(self):
        """Test that get_config_path returns ~/.instancepedia/config.toml."""
        result = get_config_path()
        expected = Path.home() / ".instancepedia" / "config.toml"
        assert result == expected

    def test_path_is_absolute(self):
        """Test that the returned path is absolute."""
        result = get_config_path()
        assert result.is_absolute()


class TestCreateDefaultConfig:
    """Tests for create_default_config function."""

    def test_returns_string(self):
        """Test that create_default_config returns a string."""
        result = create_default_config()
        assert isinstance(result, str)

    def test_contains_aws_region_setting(self):
        """Test that default config contains aws_region setting."""
        result = create_default_config()
        assert "aws_region" in result

    def test_contains_aws_profile_setting(self):
        """Test that default config contains aws_profile setting."""
        result = create_default_config()
        assert "aws_profile" in result

    def test_contains_vim_keys_setting(self):
        """Test that default config contains vim_keys setting."""
        result = create_default_config()
        assert "vim_keys" in result

    def test_contains_pricing_concurrency_setting(self):
        """Test that default config contains pricing_concurrency setting."""
        result = create_default_config()
        assert "pricing_concurrency" in result

    def test_contains_timeout_settings(self):
        """Test that default config contains timeout settings."""
        result = create_default_config()
        assert "aws_connect_timeout" in result
        assert "aws_read_timeout" in result
        assert "pricing_read_timeout" in result

    def test_is_valid_toml_syntax(self):
        """Test that the default config is valid TOML syntax."""
        result = create_default_config()
        # All settings are commented out, so it should parse as empty
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib

        # Should not raise an exception
        parsed = tomllib.loads(result)
        # All settings are commented, so parsed should be empty
        assert isinstance(parsed, dict)


class TestTomlConfigSettingsSource:
    """Tests for TomlConfigSettingsSource class."""

    def test_load_config_with_missing_file(self):
        """Test loading config when file doesn't exist."""
        with patch('src.config.settings.get_config_path') as mock_path:
            mock_path.return_value = Path("/nonexistent/config.toml")

            source = TomlConfigSettingsSource(Settings)
            result = source._load_config()

            assert result == {}

    def test_load_config_with_valid_toml(self):
        """Test loading config with valid TOML content."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
            f.write(b'aws_region = "us-west-2"\nvim_keys = true\n')
            temp_path = f.name

        try:
            with patch('src.config.settings.get_config_path') as mock_path:
                mock_path.return_value = Path(temp_path)

                source = TomlConfigSettingsSource(Settings)
                result = source._load_config()

                assert result.get('aws_region') == "us-west-2"
                assert result.get('vim_keys') is True
        finally:
            os.unlink(temp_path)

    def test_load_config_with_invalid_toml(self):
        """Test loading config with invalid TOML content returns empty dict."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
            f.write(b'invalid toml { content [')
            temp_path = f.name

        try:
            with patch('src.config.settings.get_config_path') as mock_path:
                mock_path.return_value = Path(temp_path)

                source = TomlConfigSettingsSource(Settings)
                result = source._load_config()

                # Should return empty dict on parse error
                assert result == {}
        finally:
            os.unlink(temp_path)

    def test_load_config_caches_result(self):
        """Test that _load_config caches the result."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
            f.write(b'aws_region = "eu-west-1"\n')
            temp_path = f.name

        try:
            with patch('src.config.settings.get_config_path') as mock_path:
                mock_path.return_value = Path(temp_path)

                source = TomlConfigSettingsSource(Settings)
                result1 = source._load_config()
                result2 = source._load_config()

                # Should be the same cached object
                assert result1 is result2
        finally:
            os.unlink(temp_path)

    def test_get_field_value_returns_config_value(self):
        """Test get_field_value returns value from config file."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
            f.write(b'aws_region = "ap-southeast-1"\n')
            temp_path = f.name

        try:
            with patch('src.config.settings.get_config_path') as mock_path:
                mock_path.return_value = Path(temp_path)

                source = TomlConfigSettingsSource(Settings)

                # Mock the field object
                mock_field = MagicMock()
                value, field_name, is_complex = source.get_field_value(mock_field, 'aws_region')

                assert value == "ap-southeast-1"
                assert field_name == 'aws_region'
        finally:
            os.unlink(temp_path)

    def test_get_field_value_returns_none_for_missing_field(self):
        """Test get_field_value returns None for fields not in config."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
            f.write(b'aws_region = "us-east-1"\n')
            temp_path = f.name

        try:
            with patch('src.config.settings.get_config_path') as mock_path:
                mock_path.return_value = Path(temp_path)

                source = TomlConfigSettingsSource(Settings)

                mock_field = MagicMock()
                value, field_name, is_complex = source.get_field_value(mock_field, 'nonexistent_field')

                assert value is None
                assert field_name == 'nonexistent_field'
        finally:
            os.unlink(temp_path)

    def test_call_returns_config_dict(self):
        """Test __call__ returns the loaded config dict."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
            f.write(b'vim_keys = true\npricing_concurrency = 20\n')
            temp_path = f.name

        try:
            with patch('src.config.settings.get_config_path') as mock_path:
                mock_path.return_value = Path(temp_path)

                source = TomlConfigSettingsSource(Settings)
                result = source()

                assert result.get('vim_keys') is True
                assert result.get('pricing_concurrency') == 20
        finally:
            os.unlink(temp_path)


class TestSettingsPrecedence:
    """Tests for settings precedence (env vars > config file > defaults)."""

    def test_default_values(self):
        """Test that default values are used when no config/env."""
        with patch('src.config.settings.get_config_path') as mock_path:
            mock_path.return_value = Path("/nonexistent/config.toml")

            # Clear any env vars that might interfere
            env_vars_to_clear = [k for k in os.environ if k.startswith('INSTANCEPEDIA_')]
            original_env = {k: os.environ.pop(k) for k in env_vars_to_clear}

            try:
                settings = Settings()

                assert settings.aws_region == "us-east-1"
                assert settings.vim_keys is False
                assert settings.pricing_concurrency == 10
            finally:
                # Restore env vars
                os.environ.update(original_env)

    def test_config_file_overrides_defaults(self):
        """Test that config file values override defaults."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
            f.write(b'aws_region = "eu-central-1"\nvim_keys = true\n')
            temp_path = f.name

        try:
            with patch('src.config.settings.get_config_path') as mock_path:
                mock_path.return_value = Path(temp_path)

                # Clear any env vars
                env_vars_to_clear = [k for k in os.environ if k.startswith('INSTANCEPEDIA_')]
                original_env = {k: os.environ.pop(k) for k in env_vars_to_clear}

                try:
                    settings = Settings()

                    assert settings.aws_region == "eu-central-1"
                    assert settings.vim_keys is True
                finally:
                    os.environ.update(original_env)
        finally:
            os.unlink(temp_path)

    def test_env_vars_override_config_file(self):
        """Test that environment variables override config file values."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
            f.write(b'aws_region = "eu-central-1"\nvim_keys = true\n')
            temp_path = f.name

        try:
            with patch('src.config.settings.get_config_path') as mock_path:
                mock_path.return_value = Path(temp_path)

                # Set env var to override config
                original_region = os.environ.get('INSTANCEPEDIA_AWS_REGION')
                os.environ['INSTANCEPEDIA_AWS_REGION'] = 'ap-northeast-1'

                try:
                    settings = Settings()

                    # Env var should win over config file
                    assert settings.aws_region == "ap-northeast-1"
                    # Config file value should still apply where no env var
                    assert settings.vim_keys is True
                finally:
                    if original_region is None:
                        os.environ.pop('INSTANCEPEDIA_AWS_REGION', None)
                    else:
                        os.environ['INSTANCEPEDIA_AWS_REGION'] = original_region
        finally:
            os.unlink(temp_path)

    def test_vim_keys_from_env_var(self):
        """Test vim_keys setting from environment variable."""
        with patch('src.config.settings.get_config_path') as mock_path:
            mock_path.return_value = Path("/nonexistent/config.toml")

            original_vim_keys = os.environ.get('INSTANCEPEDIA_VIM_KEYS')
            os.environ['INSTANCEPEDIA_VIM_KEYS'] = 'true'

            try:
                settings = Settings()
                assert settings.vim_keys is True
            finally:
                if original_vim_keys is None:
                    os.environ.pop('INSTANCEPEDIA_VIM_KEYS', None)
                else:
                    os.environ['INSTANCEPEDIA_VIM_KEYS'] = original_vim_keys


class TestSettingsVimKeys:
    """Tests specifically for vim_keys setting."""

    def test_vim_keys_default_is_false(self):
        """Test that vim_keys defaults to False."""
        with patch('src.config.settings.get_config_path') as mock_path:
            mock_path.return_value = Path("/nonexistent/config.toml")

            # Clear vim_keys env var
            original = os.environ.pop('INSTANCEPEDIA_VIM_KEYS', None)

            try:
                settings = Settings()
                assert settings.vim_keys is False
            finally:
                if original is not None:
                    os.environ['INSTANCEPEDIA_VIM_KEYS'] = original

    def test_vim_keys_true_from_config(self):
        """Test vim_keys = true from config file."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
            f.write(b'vim_keys = true\n')
            temp_path = f.name

        try:
            with patch('src.config.settings.get_config_path') as mock_path:
                mock_path.return_value = Path(temp_path)

                original = os.environ.pop('INSTANCEPEDIA_VIM_KEYS', None)

                try:
                    settings = Settings()
                    assert settings.vim_keys is True
                finally:
                    if original is not None:
                        os.environ['INSTANCEPEDIA_VIM_KEYS'] = original
        finally:
            os.unlink(temp_path)

    def test_vim_keys_false_from_config(self):
        """Test vim_keys = false from config file."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
            f.write(b'vim_keys = false\n')
            temp_path = f.name

        try:
            with patch('src.config.settings.get_config_path') as mock_path:
                mock_path.return_value = Path(temp_path)

                original = os.environ.pop('INSTANCEPEDIA_VIM_KEYS', None)

                try:
                    settings = Settings()
                    assert settings.vim_keys is False
                finally:
                    if original is not None:
                        os.environ['INSTANCEPEDIA_VIM_KEYS'] = original
        finally:
            os.unlink(temp_path)


class TestSettingsNumericValues:
    """Tests for numeric settings from config file."""

    def test_pricing_concurrency_from_config(self):
        """Test pricing_concurrency from config file."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
            f.write(b'pricing_concurrency = 25\n')
            temp_path = f.name

        try:
            with patch('src.config.settings.get_config_path') as mock_path:
                mock_path.return_value = Path(temp_path)

                original = os.environ.pop('INSTANCEPEDIA_PRICING_CONCURRENCY', None)

                try:
                    settings = Settings()
                    assert settings.pricing_concurrency == 25
                finally:
                    if original is not None:
                        os.environ['INSTANCEPEDIA_PRICING_CONCURRENCY'] = original
        finally:
            os.unlink(temp_path)

    def test_timeout_values_from_config(self):
        """Test timeout values from config file."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.toml', delete=False) as f:
            f.write(b'aws_connect_timeout = 30\naws_read_timeout = 120\n')
            temp_path = f.name

        try:
            with patch('src.config.settings.get_config_path') as mock_path:
                mock_path.return_value = Path(temp_path)

                # Clear env vars
                originals = {}
                for key in ['INSTANCEPEDIA_AWS_CONNECT_TIMEOUT', 'INSTANCEPEDIA_AWS_READ_TIMEOUT']:
                    originals[key] = os.environ.pop(key, None)

                try:
                    settings = Settings()
                    assert settings.aws_connect_timeout == 30
                    assert settings.aws_read_timeout == 120
                finally:
                    for key, value in originals.items():
                        if value is not None:
                            os.environ[key] = value
        finally:
            os.unlink(temp_path)
