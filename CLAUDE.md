# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Detailed documentation is organized into topic-specific files in `docs/.claude/`. Read them as needed:**
- [`architecture.md`](docs/.claude/architecture.md) - Project architecture, dual-mode design, services
- [`cli-reference.md`](docs/.claude/cli-reference.md) - CLI commands, modules, filters, presets
- [`implementation-details.md`](docs/.claude/implementation-details.md) - Performance, async, caching, AWS client config
- [`testing.md`](docs/.claude/testing.md) - Test patterns, requirements, examples
- [`error-handling.md`](docs/.claude/error-handling.md) - Exception handling best practices
- [`known-issues.md`](docs/.claude/known-issues.md) - Common pitfalls and how to avoid them

---

## Documentation Maintenance - CRITICAL

**ALWAYS update documentation when making changes!** This is non-negotiable for project maintainability.

### When to Update Each File

**Update `CLAUDE.md`** when you:
- Add new architectural patterns or best practices
- Create new services or core components
- Change the documentation structure itself

**Update `README.md`** when you:
- Add new CLI commands or flags
- Add new TUI features or keyboard shortcuts
- Change user-facing functionality

**Update `docs/.claude/` files** when you:
- Add implementation details (→ `implementation-details.md`)
- Add CLI commands or filters (→ `cli-reference.md`)
- Change architecture (→ `architecture.md`)
- Add test patterns (→ `testing.md`)
- Discover known issues (→ `known-issues.md`)

### Documentation Update Process

**CRITICAL**: After ANY feature addition, bug fix, or change, review ALL documentation files to ensure they're updated.

1. **Make code changes first**
2. **Review ALL .md files** - determine which need updates
3. **Update documentation in the SAME commit/PR** - never defer documentation
4. **Be specific** - include examples, code snippets, and clear explanations
5. **Update multiple files if needed**
6. **Test your examples** - ensure code snippets and commands work

---

## Test Coverage - MANDATORY

**100% test coverage is required for all new code.** Every new feature, function, or bug fix MUST include corresponding tests.

### Test Requirements

1. **All CLI commands must have tests** - Every `cmd_*` function requires tests
2. **All services must have tests** - New service methods require unit tests with mocked dependencies
3. **All TUI components must have tests** - New screens, widgets, or interactions require TUI tests
4. **Error cases must be tested** - Test both success and failure scenarios
5. **Edge cases must be tested** - Empty inputs, None values, boundary conditions

**See [`docs/.claude/testing.md`](docs/.claude/testing.md) for detailed test patterns and examples.**

### Before Submitting Code

1. **Run all tests**: `pytest tests/ -v`
2. **Verify new tests pass**: `pytest tests/test_your_new_file.py -v`
3. **Check test coverage for changed files**: Review that all new code paths are tested
4. **Test error scenarios**: Ensure exceptions and edge cases are covered

**Never skip tests.** If a test is difficult to write, that's often a sign the code needs refactoring.

---

## Project Overview

Instancepedia is an EC2 Instance Type Browser with both TUI (Terminal User Interface) and CLI (Command-Line Interface) modes. It provides detailed EC2 instance information, pricing (on-demand, spot, savings plans, reserved instances), and free tier eligibility indicators.

### Cost Philosophy - IMPORTANT

**All instancepedia operations MUST be free.** This tool should never incur AWS charges for users.

**Free AWS APIs used:**
- `ec2:DescribeInstanceTypes` - Instance specifications (free)
- `ec2:DescribeSpotPriceHistory` - Spot pricing (free)
- `pricing:GetProducts` - On-demand/RI/Savings Plan pricing (free)
- `ec2:DescribeRegions` - Available regions (free)

**APIs/Services to AVOID:**
- CloudWatch metrics (costs money)
- AWS Compute Optimizer (requires running instances - wrong use case)
- Any API that requires provisioned resources
- Any API with per-request charges

**When adding new features, verify:**
1. The AWS API is free tier eligible with no usage limits
2. No provisioned resources are required
3. The feature works for users with read-only AWS access
4. Document any new APIs in `docs/.claude/cli-reference.md`

---

## Common Commands

### Development Setup
```bash
# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run the application in TUI mode
instancepedia --tui

# Run with debug mode
instancepedia --tui --debug
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_tui_instance_list.py

# Run with verbose output
pytest -v
```

### Release and Publishing
```bash
# Create a new release (patch/minor/major)
echo "y" | ./scripts/release.sh patch    # 0.2.2 -> 0.2.3
echo "y" | ./scripts/release.sh minor    # 0.2.2 -> 0.3.0

# Publish to PyPI
./scripts/publish.sh pypi
```

---

## Quick Reference

### Architecture
- **Dual-mode design**: TUI (interactive) and CLI (scriptable)
- **Sync vs Async**: CLI uses boto3, TUI uses aioboto3
- **Services**: Shared between modes (see `docs/.claude/architecture.md`)

### Key Patterns
- **Async pricing**: Use callbacks with `call_later()` for UI updates
- **Error handling**: NEVER use bare `except:` blocks
- **Logging**: `logger = logging.getLogger("instancepedia")`
- **Git workflow**: NEVER push directly to main - always use PRs

### Git Configuration
- Email: `paul@paulfrederiksen.com`
- Name: `Paul Frederiksen`
- **Branch workflow**: Feature branches → PR → Squash merge to main

### Python Version
Requires Python >= 3.9 (for async features and type hints)

---

## Need More Details?

**Read the detailed documentation in `docs/.claude/`:**
- **Architecture details** → [`architecture.md`](docs/.claude/architecture.md)
- **CLI commands reference** → [`cli-reference.md`](docs/.claude/cli-reference.md)
- **Performance & async** → [`implementation-details.md`](docs/.claude/implementation-details.md)
- **Test patterns** → [`testing.md`](docs/.claude/testing.md)
- **Error handling** → [`error-handling.md`](docs/.claude/error-handling.md)
- **Known issues** → [`known-issues.md`](docs/.claude/known-issues.md)
