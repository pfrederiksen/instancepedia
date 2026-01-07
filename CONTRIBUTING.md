# Contributing to Instancepedia

Thank you for your interest in contributing to Instancepedia! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Documentation](#documentation)
- [Project Structure](#project-structure)
- [Common Tasks](#common-tasks)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of experience level, gender, gender identity, sexual orientation, disability, personal appearance, body size, race, ethnicity, age, religion, or nationality.

### Expected Behavior

- Be respectful and considerate in your communication
- Welcome newcomers and help them get started
- Focus on what is best for the project and community
- Show empathy towards other community members
- Accept constructive criticism gracefully
- Give credit where credit is due

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Personal attacks or trolling
- Publishing others' private information
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Project maintainers have the right and responsibility to remove, edit, or reject comments, commits, code, issues, and other contributions that do not align with this Code of Conduct. Violations may result in temporary or permanent bans from the project.

## Getting Started

### Prerequisites

- **Python**: 3.9 or higher
- **Git**: For version control
- **AWS Account**: For testing (optional, but recommended)
- **pip**: Python package manager

### Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/instancepedia.git
   cd instancepedia
   ```
3. **Set up upstream remote**:
   ```bash
   git remote add upstream https://github.com/pfrederiksen/instancepedia.git
   ```
4. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
5. **Install in development mode**:
   ```bash
   pip install -e ".[dev]"
   ```
6. **Run tests** to verify setup:
   ```bash
   pytest
   ```

## Development Setup

### Installing Development Dependencies

The development dependencies include testing tools and build utilities:

```bash
pip install -e ".[dev]"
```

This installs:
- `pytest` - Testing framework
- `pytest-asyncio` - Async testing support
- `build` - Package building
- `twine` - Package publishing

### Setting Up AWS Credentials (Optional)

For testing with real AWS APIs:

```bash
aws configure
# Or use environment variables:
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

**Note**: Most tests use mocks and don't require AWS credentials.

### Running the Application

**TUI Mode**:
```bash
python -m src.main --tui
```

**CLI Mode**:
```bash
python -m src.main list --region us-east-1
```

**With Debug Mode**:
```bash
python -m src.main --tui --debug
```

## How to Contribute

### Reporting Bugs

Before creating a bug report:
1. **Check existing issues**: https://github.com/pfrederiksen/instancepedia/issues
2. **Try the latest version**: Update to ensure the bug hasn't been fixed
3. **Check TROUBLESHOOTING.md**: Your issue might have a known solution

When creating a bug report, include:
- **Clear title**: Concise description of the issue
- **Environment**: OS, Python version, instancepedia version
- **Steps to reproduce**: Exact commands/actions
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Error messages**: Full error text or screenshots
- **Debug logs**: If available (`--debug` mode)

**Template**:
```markdown
**Environment:**
- OS: macOS 13.0
- Python: 3.11.5
- Instancepedia: 0.5.0

**Steps to Reproduce:**
1. Run `instancepedia --tui --region us-east-1`
2. Press 'F' to open filters
3. ...

**Expected:** Filter modal should open
**Actual:** Application crashes with error

**Error:**
```
[paste error here]
```

**Debug logs:** [if applicable]
```

### Suggesting Features

Feature requests are welcome! To suggest a feature:

1. **Check existing issues**: Someone might have already suggested it
2. **Describe the use case**: Why is this feature needed?
3. **Propose a solution**: How should it work?
4. **Consider alternatives**: Are there other ways to achieve the goal?

**Template**:
```markdown
**Problem:** [Describe the problem this solves]
**Proposed Solution:** [How should it work?]
**Alternatives:** [Other approaches considered]
**Use Case:** [Real-world scenario where this is needed]
```

### Submitting Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**:
   - Follow coding standards (see below)
   - Add tests for new functionality
   - Update documentation

3. **Test your changes**:
   ```bash
   pytest
   pytest -v  # Verbose output
   ```

4. **Commit with clear messages**:
   ```bash
   git add .
   git commit -m "feat: Add instance filtering by GPU count"
   # or
   git commit -m "fix: Handle pricing timeout gracefully"
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request** on GitHub

## Coding Standards

### Python Style

We follow PEP 8 with some project-specific conventions:

**General Guidelines:**
- **Line length**: 120 characters maximum (not strict 79)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Use double quotes for strings by default
- **Type hints**: Use type hints for function signatures
- **Docstrings**: Use docstrings for classes and non-trivial functions

**Example**:
```python
def fetch_instance_types(
    region: str,
    family: Optional[str] = None
) -> List[InstanceType]:
    """Fetch EC2 instance types for a region.

    Args:
        region: AWS region code (e.g., 'us-east-1')
        family: Optional instance family filter (e.g., 't3')

    Returns:
        List of InstanceType objects

    Raises:
        AWSRegionError: If region is invalid or inaccessible
    """
    # Implementation here
    pass
```

### Error Handling

**NEVER use bare `except:` blocks**:

```python
# Bad ❌
try:
    do_something()
except:
    pass

# Good ✅
try:
    do_something()
except SpecificException as e:
    logger.debug(f"Expected error: {e}")
```

**Always explain why exceptions are expected**:

```python
try:
    widget.update("status")
except Exception as e:
    # Widget may not exist during screen transition
    logger.debug(f"Failed to update widget: {e}")
```

### Logging

Use structured logging with appropriate levels:

```python
import logging

logger = logging.getLogger("instancepedia")

# Debug: Verbose information
logger.debug(f"Cache hit for {instance_type}")

# Info: General operations
logger.info(f"Fetched {len(instances)} instance types")

# Warning: Unexpected but recoverable
logger.warning(f"Pricing unavailable for {instance_type}")

# Error: Errors requiring attention
logger.error(f"Failed to fetch pricing: {e}", exc_info=True)
```

### Async Code (TUI)

**Use async/await for I/O operations**:

```python
async def fetch_pricing(instances: List[str]) -> Dict[str, float]:
    """Fetch pricing data asynchronously."""
    async with AsyncAWSClient(region) as client:
        pricing = await client.get_prices(instances)
        return pricing
```

**Use `call_later()` for UI updates from workers**:

```python
def on_progress(completed: int, total: int):
    def update_ui():
        self.update_status_bar(f"Loading {completed}/{total}")
    self.call_later(update_ui)  # Thread-safe UI update
```

### Testing Standards

**Every feature needs tests**:

```python
def test_instance_filtering_by_family():
    """Test filtering instances by family."""
    instances = [
        create_instance("t3.micro"),
        create_instance("t3.small"),
        create_instance("m5.large"),
    ]

    filtered = filter_by_family(instances, family="t3")

    assert len(filtered) == 2
    assert all(inst.instance_type.startswith("t3.") for inst in filtered)
```

**Use descriptive test names**:
- Describe what is being tested
- Use `test_<feature>_<scenario>` pattern
- Example: `test_pricing_cache_handles_expiration`

**Use mocks to avoid AWS API calls**:

```python
@patch('boto3.client')
def test_fetch_instance_types(mock_boto_client):
    """Test instance type fetching without real AWS calls."""
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    mock_client.describe_instance_types.return_value = {
        'InstanceTypes': [{'InstanceType': 't3.micro'}]
    }

    instances = fetch_instance_types('us-east-1')

    assert len(instances) == 1
    assert instances[0].instance_type == 't3.micro'
```

## Testing Guidelines

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_pricing_service.py

# Run single test
pytest tests/test_pricing_service.py::TestPricingService::test_cache_hit

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src tests/
```

### Test Organization

Tests are organized by component:
- `tests/test_cli_*.py` - CLI-related tests
- `tests/test_tui_*.py` - TUI-related tests
- `tests/test_*_service.py` - Service layer tests
- `tests/test_cache.py` - Caching tests

### Writing Tests

**TUI Tests** (async with Textual):

```python
async def test_instance_list_displays():
    """Test instance list screen displays correctly."""
    instances = [create_mock_instance("t3.micro")]
    app = InstanceListTestApp(instances)

    async with app.run_test() as pilot:
        await pilot.pause()  # Let UI update

        # Assert on screen state
        screen = app.screen
        assert isinstance(screen, InstanceList)
        assert len(screen.filtered_instance_types) == 1
```

**CLI Tests** (with mocks):

```python
@patch('src.services.aws_client.AWSClient')
def test_list_command(mock_aws_client):
    """Test CLI list command."""
    mock_client = Mock()
    mock_aws_client.return_value = mock_client
    mock_client.get_instance_types.return_value = [
        create_mock_instance("t3.micro")
    ]

    # Test the command
    result = cmd_list(
        region="us-east-1",
        output_format="json"
    )

    assert result is not None
    assert "t3.micro" in result
```

### Test Fixtures

Use fixtures for common test data:

```python
@pytest.fixture
def sample_instance():
    """Create a sample instance for testing."""
    return InstanceType(
        instance_type="t3.micro",
        vcpu_info=VCpuInfo(default_vcpus=2),
        memory_info=MemoryInfo(size_in_mib=1024),
        # ... other fields
    )

def test_instance_display(sample_instance):
    """Test using the fixture."""
    label = format_instance_label(sample_instance)
    assert "t3.micro" in label
```

## Pull Request Process

### Before Submitting

1. **Update from upstream**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run all tests**:
   ```bash
   pytest
   ```

3. **Update documentation** (if needed):
   - README.md for user-facing changes
   - CLAUDE.md for developer/architecture changes
   - Docstrings for new functions/classes

4. **Check commit messages**:
   - Use conventional commits format:
     - `feat:` New features
     - `fix:` Bug fixes
     - `docs:` Documentation only
     - `test:` Adding tests
     - `refactor:` Code refactoring
     - `perf:` Performance improvements

### PR Description Template

```markdown
## Summary
[Brief description of changes]

## Changes
- [List of specific changes]
- [One change per line]

## Motivation
[Why is this change needed?]

## Testing
- [ ] All existing tests pass
- [ ] Added tests for new functionality
- [ ] Tested manually in TUI mode
- [ ] Tested manually in CLI mode

## Documentation
- [ ] Updated README.md (if user-facing change)
- [ ] Updated CLAUDE.md (if architectural change)
- [ ] Added/updated docstrings

## Screenshots (if applicable)
[Add screenshots for UI changes]

## Related Issues
Closes #[issue number]
```

### Review Process

1. **Automated checks**: GitHub Actions will run tests
2. **Code review**: Maintainer will review your code
3. **Feedback**: Address any requested changes
4. **Approval**: Once approved, PR will be merged
5. **Credit**: You'll be credited in the commit and release notes

### After Merge

Your contribution will be included in the next release! Thank you! 🎉

## Documentation

### When to Update Documentation

**README.md** - Update when:
- Adding new CLI commands or flags
- Adding new TUI features or keyboard shortcuts
- Changing installation process
- Adding configuration options
- Modifying user-facing behavior

**CLAUDE.md** - Update when:
- Adding new architectural patterns
- Creating new services or components
- Changing async/threading model
- Adding testing patterns
- Modifying TUI or CLI architecture

**Example Updates**:

```bash
# After adding a new feature
git add README.md CLAUDE.md
git commit -m "docs: Document new GPU filtering feature"
```

### Documentation Style

- **Be concise**: Short, clear explanations
- **Use examples**: Show, don't just tell
- **Keep updated**: Update docs in the same commit as code
- **Test examples**: Ensure code examples actually work

## Project Structure

```
instancepedia/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── app.py               # TUI main app
│   ├── cli/                 # CLI commands
│   │   ├── commands.py      # Command implementations
│   │   ├── output.py        # Output formatters
│   │   └── parser.py        # Argument parsing
│   ├── ui/                  # TUI screens
│   │   ├── instance_list.py
│   │   ├── instance_detail.py
│   │   ├── instance_comparison.py
│   │   ├── filter_modal.py
│   │   ├── region_selector.py
│   │   └── sort_options.py
│   ├── models/              # Pydantic models
│   │   ├── instance_type.py
│   │   ├── region.py
│   │   └── free_tier.py
│   ├── services/            # Business logic
│   │   ├── aws_client.py            # Sync boto3
│   │   ├── async_aws_client.py      # Async aioboto3
│   │   ├── instance_service.py
│   │   ├── pricing_service.py
│   │   ├── async_pricing_service.py
│   │   └── free_tier_service.py
│   ├── config/
│   │   └── settings.py
│   ├── cache.py             # Pricing cache
│   ├── debug.py             # Debug logging
│   ├── exceptions.py        # Custom exceptions
│   └── logging_config.py    # Logging setup
├── tests/                   # Test suite
│   ├── test_cli_*.py
│   ├── test_tui_*.py
│   └── test_*.py
├── scripts/
│   ├── release.sh           # Release automation
│   └── publish.sh           # PyPI publishing
├── README.md
├── CLAUDE.md
├── CONTRIBUTING.md
├── TROUBLESHOOTING.md
├── LICENSE
├── pyproject.toml
└── requirements.txt
```

### Key Components

**Entry Point** (`src/main.py`):
- Routes to TUI or CLI based on arguments
- Handles global options (--debug, --tui, --region)

**TUI** (`src/app.py`, `src/ui/`):
- Textual-based interactive interface
- Screen-based navigation
- Async pricing with workers

**CLI** (`src/cli/`):
- Headless command-line interface
- Multiple output formats (table, JSON, CSV)
- Scriptable and pipeable

**Services** (`src/services/`):
- Shared between TUI and CLI
- Handles AWS API interactions
- Implements caching and error handling

**Models** (`src/models/`):
- Pydantic models for data validation
- Type-safe data structures

## Common Tasks

### Adding a New TUI Feature

1. **Create or modify screen** in `src/ui/`
2. **Add key binding** to appropriate screen's `BINDINGS`
3. **Implement action method**: `action_your_feature()`
4. **Update help text** in screen's `compose()` method
5. **Add tests** in `tests/test_tui_*.py`
6. **Update README.md** with new keyboard shortcut
7. **Update CLAUDE.md** if architectural change

Example:
```python
# In src/ui/instance_list.py
BINDINGS = [
    # ... existing bindings
    ("n", "new_feature", "New Feature"),
]

def action_new_feature(self) -> None:
    """Handle new feature action."""
    # Implementation
    pass
```

### Adding a New CLI Command

1. **Add parser** in `src/cli/parser.py`
2. **Implement command** in `src/cli/commands.py`
3. **Add output formatter** in `src/cli/output.py` (if needed)
4. **Add tests** in `tests/test_cli_*.py`
5. **Update README.md** with command documentation

Example:
```python
# In src/cli/parser.py
subparsers.add_parser('newcommand', help='Description')

# In src/cli/commands.py
def cmd_newcommand(args):
    """Implementation of newcommand."""
    # ... implementation
```

### Adding a New Filter

1. **Add filter field** to `FilterCriteria` in `src/ui/filter_modal.py`
2. **Add UI input** to `FilterModal.compose()`
3. **Update `_apply_filters()`** to handle new filter
4. **Update `_apply_filters()`** in `src/ui/instance_list.py`
5. **Add tests** for filter logic
6. **Update README.md** filter documentation

### Adding AWS API Integration

1. **Add method to `AWSClient`** (sync) in `src/services/aws_client.py`
2. **Add method to `AsyncAWSClient`** (async) in `src/services/async_aws_client.py`
3. **Add service method** if needed
4. **Add error handling** with custom exceptions
5. **Add tests** with mocked boto3
6. **Update IAM policy** in README.md if new permission needed

## Questions?

- **GitHub Issues**: https://github.com/pfrederiksen/instancepedia/issues
- **Discussions**: Use GitHub Discussions for questions
- **Email**: paul@paulfrederiksen.com

Thank you for contributing to Instancepedia! 🚀
