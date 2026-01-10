"""Tests for filter preset persistence functionality"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.services.filter_preset_service import FilterPresetService, FilterPreset
from src.ui.filter_modal import FilterCriteria
from src.cli.commands import preset_commands


class TestFilterPresetDataclass:
    """Tests for FilterPreset dataclass"""

    def test_filter_preset_creation_minimal(self):
        """Test creating a preset with minimal fields"""
        preset = FilterPreset(name="test")
        assert preset.name == "test"
        assert preset.description is None
        assert preset.min_vcpu is None

    def test_filter_preset_creation_all_fields(self):
        """Test creating a preset with all fields"""
        preset = FilterPreset(
            name="full-test",
            description="Test description",
            min_vcpu=4,
            max_vcpu=16,
            min_memory=8.0,
            max_memory=64.0,
            has_gpu=True,
            current_generation_only=True,
            burstable_only=False,
            free_tier_only=False,
            architecture="arm64",
            instance_families=["t3", "m5"],
            processor_family="graviton",
            network_performance="high",
            storage_type="ebs_only",
            nvme_support="required",
            min_price=0.01,
            max_price=1.00
        )
        assert preset.name == "full-test"
        assert preset.min_vcpu == 4
        assert preset.processor_family == "graviton"

    def test_filter_preset_to_dict(self):
        """Test converting preset to dictionary"""
        preset = FilterPreset(
            name="test",
            min_vcpu=4,
            current_generation_only=True
        )
        result = preset.to_dict()
        assert result["name"] == "test"
        assert result["min_vcpu"] == 4
        assert result["current_generation_only"] == True
        # None values should be excluded
        assert "max_vcpu" not in result
        assert "description" not in result
        # False booleans should be excluded
        assert "burstable_only" not in result

    def test_filter_preset_from_dict(self):
        """Test creating preset from dictionary"""
        data = {
            "name": "from-dict",
            "description": "From dict test",
            "min_vcpu": 8,
            "architecture": "x86_64"
        }
        preset = FilterPreset.from_dict(data)
        assert preset.name == "from-dict"
        assert preset.min_vcpu == 8
        assert preset.architecture == "x86_64"
        assert preset.max_vcpu is None

    def test_filter_preset_from_dict_unknown_fields(self):
        """Test that unknown fields are ignored"""
        data = {
            "name": "test",
            "unknown_field": "should be ignored",
            "another_unknown": 123
        }
        preset = FilterPreset.from_dict(data)
        assert preset.name == "test"
        assert not hasattr(preset, "unknown_field")


class TestFilterPresetConversion:
    """Tests for FilterPreset to/from FilterCriteria conversion"""

    def test_to_filter_criteria_basic(self):
        """Test converting preset to FilterCriteria"""
        preset = FilterPreset(
            name="test",
            min_vcpu=4,
            max_memory=32.0,
            has_gpu=True,
            current_generation_only=True
        )
        criteria = preset.to_filter_criteria()
        assert criteria.min_vcpu == 4
        assert criteria.max_memory_gb == 32.0
        assert criteria.gpu_filter == "yes"
        assert criteria.current_generation == "yes"

    def test_to_filter_criteria_no_gpu(self):
        """Test has_gpu=False maps correctly"""
        preset = FilterPreset(name="test", has_gpu=False)
        criteria = preset.to_filter_criteria()
        assert criteria.gpu_filter == "no"

    def test_to_filter_criteria_extended_fields(self):
        """Test extended fields convert correctly"""
        preset = FilterPreset(
            name="test",
            processor_family="amd",
            network_performance="high",
            storage_type="ebs_only",
            nvme_support="required",
            min_price=0.05
        )
        criteria = preset.to_filter_criteria()
        assert criteria.processor_family == "amd"
        assert criteria.network_performance == "high"
        assert criteria.storage_type == "ebs_only"
        assert criteria.nvme_support == "required"
        assert criteria.min_price == 0.05

    def test_to_filter_criteria_instance_families(self):
        """Test instance families list converts to comma-separated string"""
        preset = FilterPreset(name="test", instance_families=["t3", "m5", "c6i"])
        criteria = preset.to_filter_criteria()
        assert criteria.family_filter == "t3, m5, c6i"

    def test_from_filter_criteria_basic(self):
        """Test creating preset from FilterCriteria"""
        criteria = FilterCriteria()
        criteria.min_vcpu = 8
        criteria.max_memory_gb = 64.0
        criteria.gpu_filter = "yes"
        criteria.current_generation = "yes"

        preset = FilterPreset.from_filter_criteria(
            criteria, name="from-criteria", description="Test"
        )
        assert preset.name == "from-criteria"
        assert preset.min_vcpu == 8
        assert preset.max_memory == 64.0
        assert preset.has_gpu == True
        assert preset.current_generation_only == True

    def test_from_filter_criteria_no_gpu(self):
        """Test gpu_filter=no maps to has_gpu=False"""
        criteria = FilterCriteria()
        criteria.gpu_filter = "no"
        preset = FilterPreset.from_filter_criteria(criteria, "test")
        assert preset.has_gpu == False

    def test_from_filter_criteria_any_values_not_stored(self):
        """Test that 'any' values are not stored in preset"""
        criteria = FilterCriteria()
        criteria.gpu_filter = "any"
        criteria.architecture = "any"
        criteria.processor_family = "any"
        preset = FilterPreset.from_filter_criteria(criteria, "test")
        assert preset.has_gpu is None
        assert preset.architecture is None
        assert preset.processor_family is None

    def test_from_filter_criteria_family_filter(self):
        """Test comma-separated family filter converts to list"""
        criteria = FilterCriteria()
        criteria.family_filter = "t3, m5, c6i"
        preset = FilterPreset.from_filter_criteria(criteria, "test")
        assert preset.instance_families == ["t3", "m5", "c6i"]

    def test_roundtrip_conversion(self):
        """Test that preset -> criteria -> preset preserves values"""
        original = FilterPreset(
            name="roundtrip",
            description="Test roundtrip",
            min_vcpu=4,
            max_vcpu=16,
            min_memory=8.0,
            has_gpu=True,
            current_generation_only=True,
            architecture="arm64",
            processor_family="graviton",
            network_performance="high"
        )
        criteria = original.to_filter_criteria()
        roundtrip = FilterPreset.from_filter_criteria(criteria, "roundtrip", "Test roundtrip")

        assert roundtrip.min_vcpu == original.min_vcpu
        assert roundtrip.max_vcpu == original.max_vcpu
        assert roundtrip.min_memory == original.min_memory
        assert roundtrip.has_gpu == original.has_gpu
        assert roundtrip.current_generation_only == original.current_generation_only
        assert roundtrip.architecture == original.architecture
        assert roundtrip.processor_family == original.processor_family
        assert roundtrip.network_performance == original.network_performance


class TestFilterPresetService:
    """Tests for FilterPresetService"""

    @pytest.fixture
    def temp_presets_dir(self):
        """Create a temporary directory for presets"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def preset_service(self, temp_presets_dir):
        """Create a preset service with temporary storage"""
        with patch.object(FilterPresetService, '__init__', lambda self: None):
            service = FilterPresetService()
            service.presets_dir = temp_presets_dir / "presets"
            service.presets_file = service.presets_dir / "filter_presets.json"
            service.presets_dir.mkdir(parents=True, exist_ok=True)
            service.builtin_presets = {
                "web-server": FilterPreset(name="web-server", description="Web server preset"),
                "database": FilterPreset(name="database", description="Database preset"),
            }
            yield service

    def test_get_builtin_presets(self, preset_service):
        """Test getting built-in presets"""
        presets = preset_service.get_builtin_presets()
        assert "web-server" in presets
        assert "database" in presets

    def test_is_builtin_preset(self, preset_service):
        """Test checking if preset is built-in"""
        assert preset_service.is_builtin_preset("web-server") == True
        assert preset_service.is_builtin_preset("custom") == False

    def test_save_custom_preset(self, preset_service):
        """Test saving a custom preset"""
        preset = FilterPreset(name="my-preset", description="Custom", min_vcpu=4)
        result = preset_service.save_custom_preset(preset)
        assert result == True

        # Verify it was saved
        loaded = preset_service.load_custom_presets()
        assert "my-preset" in loaded
        assert loaded["my-preset"].min_vcpu == 4

    def test_delete_custom_preset(self, preset_service):
        """Test deleting a custom preset"""
        # First save one
        preset = FilterPreset(name="to-delete", description="Will be deleted")
        preset_service.save_custom_preset(preset)

        # Delete it
        result = preset_service.delete_custom_preset("to-delete")
        assert result == True

        # Verify it's gone
        loaded = preset_service.load_custom_presets()
        assert "to-delete" not in loaded

    def test_delete_nonexistent_preset(self, preset_service):
        """Test deleting a preset that doesn't exist"""
        result = preset_service.delete_custom_preset("nonexistent")
        assert result == False

    def test_is_custom_preset(self, preset_service):
        """Test checking if preset is custom"""
        preset = FilterPreset(name="custom-test")
        preset_service.save_custom_preset(preset)

        assert preset_service.is_custom_preset("custom-test") == True
        assert preset_service.is_custom_preset("web-server") == False

    def test_get_all_presets(self, preset_service):
        """Test getting all presets (built-in + custom)"""
        preset = FilterPreset(name="custom")
        preset_service.save_custom_preset(preset)

        all_presets = preset_service.get_all_presets()
        assert "web-server" in all_presets
        assert "database" in all_presets
        assert "custom" in all_presets

    def test_get_preset_custom_first(self, preset_service):
        """Test that custom presets override built-in with same name"""
        # Save a custom preset with same name as built-in
        custom = FilterPreset(name="web-server", description="Custom override", min_vcpu=99)
        preset_service.save_custom_preset(custom)

        # Get should return custom version
        result = preset_service.get_preset("web-server")
        assert result.min_vcpu == 99
        assert result.description == "Custom override"


class TestCLIPresetsSave:
    """Tests for CLI presets save command"""

    @patch('src.cli.commands.preset_commands.FilterPresetService')
    def test_cmd_presets_save_existing_without_force(self, mock_service_class):
        """Test that saving over existing preset fails without --force"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False
        mock_service.get_preset.return_value = FilterPreset(name="existing", min_vcpu=2)
        mock_service_class.return_value = mock_service

        args = Mock()
        args.preset_name = "existing"
        args.description = "Try to overwrite"
        args.min_vcpu = 4
        args.max_vcpu = None
        args.min_memory = None
        args.max_memory = None
        args.has_gpu = None
        args.current_generation = False
        args.burstable = False
        args.free_tier = False
        args.architecture = None
        args.instance_families = None
        args.processor_family = None
        args.network_performance = None
        args.storage_type = None
        args.nvme_support = None
        args.min_price = None
        args.max_price = None
        args.force = False  # Not using --force
        args.format = "table"
        args.quiet = False

        result = preset_commands.cmd_presets_save(args)
        assert result == 1  # Should fail
        mock_service.save_custom_preset.assert_not_called()

    @patch('src.cli.commands.preset_commands.FilterPresetService')
    def test_cmd_presets_save_existing_with_force(self, mock_service_class):
        """Test that saving over existing preset succeeds with --force"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False
        mock_service.get_preset.return_value = FilterPreset(name="existing", min_vcpu=2)
        mock_service.save_custom_preset.return_value = True
        mock_service_class.return_value = mock_service

        args = Mock()
        args.preset_name = "existing"
        args.description = "Overwrite"
        args.min_vcpu = 8
        args.max_vcpu = None
        args.min_memory = None
        args.max_memory = None
        args.has_gpu = None
        args.current_generation = False
        args.burstable = False
        args.free_tier = False
        args.architecture = None
        args.instance_families = None
        args.processor_family = None
        args.network_performance = None
        args.storage_type = None
        args.nvme_support = None
        args.min_price = None
        args.max_price = None
        args.force = True  # Using --force
        args.format = "table"
        args.quiet = False

        result = preset_commands.cmd_presets_save(args)
        assert result == 0  # Should succeed
        mock_service.save_custom_preset.assert_called_once()

    @patch('src.cli.commands.preset_commands.FilterPresetService')
    def test_cmd_presets_save_success(self, mock_service_class):
        """Test successful preset save"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False
        mock_service.get_preset.return_value = None
        mock_service.save_custom_preset.return_value = True
        mock_service_class.return_value = mock_service

        args = Mock()
        args.preset_name = "my-preset"
        args.description = "My description"
        args.min_vcpu = 4
        args.max_vcpu = None
        args.min_memory = None
        args.max_memory = None
        args.has_gpu = None
        args.current_generation = False
        args.burstable = False
        args.free_tier = False
        args.architecture = None
        args.instance_families = None
        args.processor_family = None
        args.network_performance = None
        args.storage_type = None
        args.nvme_support = None
        args.min_price = None
        args.max_price = None
        args.force = False
        args.format = "table"
        args.quiet = False

        result = preset_commands.cmd_presets_save(args)
        assert result == 0
        mock_service.save_custom_preset.assert_called_once()

    @patch('src.cli.commands.preset_commands.FilterPresetService')
    def test_cmd_presets_save_builtin_blocked(self, mock_service_class):
        """Test that built-in presets cannot be overwritten"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = True
        mock_service_class.return_value = mock_service

        args = Mock()
        args.preset_name = "web-server"
        args.description = None

        result = preset_commands.cmd_presets_save(args)
        assert result == 1
        mock_service.save_custom_preset.assert_not_called()

    @patch('src.cli.commands.preset_commands.FilterPresetService')
    def test_cmd_presets_save_no_filters(self, mock_service_class):
        """Test that save fails without any filters"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False
        mock_service.get_preset.return_value = None
        mock_service_class.return_value = mock_service

        args = Mock()
        args.preset_name = "empty"
        args.description = None
        args.min_vcpu = None
        args.max_vcpu = None
        args.min_memory = None
        args.max_memory = None
        args.has_gpu = None
        args.current_generation = False
        args.burstable = False
        args.free_tier = False
        args.architecture = None
        args.instance_families = None
        args.processor_family = None
        args.network_performance = None
        args.storage_type = None
        args.nvme_support = None
        args.min_price = None
        args.max_price = None
        args.force = False

        result = preset_commands.cmd_presets_save(args)
        assert result == 1


class TestCLIPresetsDelete:
    """Tests for CLI presets delete command"""

    @patch('src.cli.commands.preset_commands.FilterPresetService')
    def test_cmd_presets_delete_success(self, mock_service_class):
        """Test successful preset deletion"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False
        mock_service.is_custom_preset.return_value = True
        mock_service.delete_custom_preset.return_value = True
        mock_service_class.return_value = mock_service

        args = Mock()
        args.preset_name = "my-preset"
        args.force = True
        args.quiet = False

        result = preset_commands.cmd_presets_delete(args)
        assert result == 0
        mock_service.delete_custom_preset.assert_called_once_with("my-preset")

    @patch('builtins.input', return_value='y')
    @patch('src.cli.commands.preset_commands.FilterPresetService')
    def test_cmd_presets_delete_confirmed(self, mock_service_class, mock_input):
        """Test delete with user confirmation (y)"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False
        mock_service.is_custom_preset.return_value = True
        mock_service.delete_custom_preset.return_value = True
        mock_service_class.return_value = mock_service

        args = Mock()
        args.preset_name = "my-preset"
        args.force = False  # Will prompt for confirmation
        args.quiet = False

        result = preset_commands.cmd_presets_delete(args)
        assert result == 0
        mock_input.assert_called_once()
        mock_service.delete_custom_preset.assert_called_once_with("my-preset")

    @patch('builtins.input', return_value='yes')
    @patch('src.cli.commands.preset_commands.FilterPresetService')
    def test_cmd_presets_delete_confirmed_yes(self, mock_service_class, mock_input):
        """Test delete with user confirmation (yes)"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False
        mock_service.is_custom_preset.return_value = True
        mock_service.delete_custom_preset.return_value = True
        mock_service_class.return_value = mock_service

        args = Mock()
        args.preset_name = "my-preset"
        args.force = False
        args.quiet = False

        result = preset_commands.cmd_presets_delete(args)
        assert result == 0
        mock_service.delete_custom_preset.assert_called_once()

    @patch('builtins.input', return_value='n')
    @patch('src.cli.commands.preset_commands.FilterPresetService')
    def test_cmd_presets_delete_cancelled(self, mock_service_class, mock_input):
        """Test delete cancelled by user (n)"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False
        mock_service.is_custom_preset.return_value = True
        mock_service_class.return_value = mock_service

        args = Mock()
        args.preset_name = "my-preset"
        args.force = False  # Will prompt for confirmation
        args.quiet = False

        result = preset_commands.cmd_presets_delete(args)
        assert result == 0  # Cancelled is still success (user choice)
        mock_input.assert_called_once()
        mock_service.delete_custom_preset.assert_not_called()

    @patch('builtins.input', return_value='')
    @patch('src.cli.commands.preset_commands.FilterPresetService')
    def test_cmd_presets_delete_cancelled_empty(self, mock_service_class, mock_input):
        """Test delete cancelled with empty input"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False
        mock_service.is_custom_preset.return_value = True
        mock_service_class.return_value = mock_service

        args = Mock()
        args.preset_name = "my-preset"
        args.force = False
        args.quiet = False

        result = preset_commands.cmd_presets_delete(args)
        assert result == 0
        mock_service.delete_custom_preset.assert_not_called()

    @patch('src.cli.commands.preset_commands.FilterPresetService')
    def test_cmd_presets_delete_builtin_blocked(self, mock_service_class):
        """Test that built-in presets cannot be deleted"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = True
        mock_service_class.return_value = mock_service

        args = Mock()
        args.preset_name = "web-server"
        args.force = True

        result = preset_commands.cmd_presets_delete(args)
        assert result == 1
        mock_service.delete_custom_preset.assert_not_called()

    @patch('src.cli.commands.preset_commands.FilterPresetService')
    def test_cmd_presets_delete_not_found(self, mock_service_class):
        """Test deleting non-existent preset"""
        mock_service = Mock()
        mock_service.is_builtin_preset.return_value = False
        mock_service.is_custom_preset.return_value = False
        mock_service_class.return_value = mock_service

        args = Mock()
        args.preset_name = "nonexistent"
        args.force = True

        result = preset_commands.cmd_presets_delete(args)
        assert result == 1


class TestPresetFilterApplication:
    """Tests for applying preset filters to instances"""

    def create_mock_instance(self, name, vcpu=2, memory=4.0, gpu=None, current_gen=True, arch="x86_64"):
        """Create a mock instance for testing"""
        inst = Mock()
        inst.instance_type = name
        inst.vcpu_info = Mock()
        inst.vcpu_info.default_vcpus = vcpu
        inst.memory_info = Mock()
        inst.memory_info.size_in_gb = memory
        inst.gpu_info = gpu
        inst.current_generation = current_gen
        inst.burstable_performance_supported = name.startswith("t")
        inst.processor_info = Mock()
        inst.processor_info.supported_architectures = [arch]
        inst.network_info = Mock()
        inst.network_info.network_performance = "Up to 5 Gigabit"
        inst.instance_storage_info = None
        inst.pricing = None
        return inst

    def test_filter_by_vcpu(self):
        """Test filtering by vCPU count"""
        instances = [
            self.create_mock_instance("t3.small", vcpu=2),
            self.create_mock_instance("t3.medium", vcpu=4),
            self.create_mock_instance("t3.large", vcpu=8),
        ]
        preset = FilterPreset(name="test", min_vcpu=4)
        result = preset_commands._apply_preset_filters(instances, preset)
        assert len(result) == 2
        assert all(i.vcpu_info.default_vcpus >= 4 for i in result)

    def test_filter_by_memory(self):
        """Test filtering by memory"""
        instances = [
            self.create_mock_instance("t3.small", memory=2.0),
            self.create_mock_instance("t3.medium", memory=4.0),
            self.create_mock_instance("t3.large", memory=8.0),
        ]
        preset = FilterPreset(name="test", min_memory=4.0, max_memory=8.0)
        result = preset_commands._apply_preset_filters(instances, preset)
        assert len(result) == 2

    def test_filter_by_gpu(self):
        """Test filtering by GPU"""
        instances = [
            self.create_mock_instance("t3.small", gpu=None),
            self.create_mock_instance("p3.large", gpu=Mock()),
        ]
        preset = FilterPreset(name="test", has_gpu=True)
        result = preset_commands._apply_preset_filters(instances, preset)
        assert len(result) == 1
        assert result[0].instance_type == "p3.large"

    def test_filter_by_architecture(self):
        """Test filtering by architecture"""
        instances = [
            self.create_mock_instance("t3.small", arch="x86_64"),
            self.create_mock_instance("t4g.small", arch="arm64"),
        ]
        preset = FilterPreset(name="test", architecture="arm64")
        result = preset_commands._apply_preset_filters(instances, preset)
        assert len(result) == 1
        assert result[0].instance_type == "t4g.small"
