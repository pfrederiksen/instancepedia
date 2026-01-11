# Keyboard Shortcuts Reference

Complete guide to keyboard shortcuts in Instancepedia's TUI mode.

Press `?` in the TUI to view this help screen anytime.

## Quick Reference

| Key | Action |
|-----|--------|
| `?` | Show help modal with all shortcuts |
| `Q` or `Esc` | Quit application / Close modal / Cancel |

## Navigation

### Tree Navigation (Standard)

| Key | Action |
|-----|--------|
| `↑` / `k` | Move up one item |
| `↓` / `j` | Move down one item |
| `←` / `h` | Collapse current category |
| `→` / `l` | Expand current category |
| `Home` | Jump to first item |
| `End` | Jump to last item |
| `Page Up` | Scroll up one page |
| `Page Down` | Scroll down one page |
| `Space` | Expand/collapse current node |
| `Enter` | View instance details (if instance selected) |

**Note**: `hjkl` Vim-style navigation is available when `vim_keys = true` in config.

### Detail View Navigation

| Key | Action |
|-----|--------|
| `↑` / `k` | Scroll up |
| `↓` / `j` | Scroll down |
| `Page Up` | Scroll up one page |
| `Page Down` | Scroll down one page |
| `Home` | Scroll to top |
| `End` | Scroll to bottom |
| `Q` / `Esc` | Return to instance list |

## Search and Filter

### Search

| Key | Action |
|-----|--------|
| `/` | Activate search mode |
| `Esc` | Clear search and return to normal mode |
| `Enter` | (In search) Jump to first result |

When search is active:
- Type to search across instance types and attributes
- Results filter in real-time as you type
- Tree shows only matching instances

### Filter Modal

| Key | Action |
|-----|--------|
| `F` | Open filter modal |
| `Tab` | Move to next filter field |
| `Shift+Tab` | Move to previous filter field |
| `Space` | Toggle checkbox |
| `Enter` | Apply filters and close modal |
| `Esc` / `Q` | Cancel and close modal |

**Filter Modal Controls**:
- **Apply**: Apply filters and close (or press `Enter`)
- **Save Preset**: Save current filters as a custom preset
- **Reset All**: Clear all filters
- **Cancel**: Close without applying (or press `Esc`)

### Filter Preset Loading

In the filter modal:
- **Preset Dropdown**: Select a preset from the dropdown at the top
- Loads both built-in and custom presets
- Automatically populates all filter fields

## Sorting

| Key | Action |
|-----|--------|
| `S` | Cycle through sort options (forward) |
| `Shift+S` | Cycle through sort options (backward) |

**Sort Options** (cycles in this order):
1. Name (A-Z)
2. Name (Z-A)
3. vCPU (Low-High)
4. vCPU (High-Low)
5. Memory (Low-High)
6. Memory (High-Low)
7. Price (Low-High)
8. Price (High-Low)

Current sort order is displayed in the status bar at the bottom.

## Instance Actions

| Key | Action |
|-----|--------|
| `Enter` | View detailed specifications for selected instance |
| `C` | Mark/unmark instance for comparison (max 2) |
| `V` | Compare marked instances (requires exactly 2 marked) |
| `P` | View spot price history (30 days) for selected instance |
| `O` | View cost optimization recommendations for selected instance |
| `R` | Compare pricing across all regions for selected instance |
| `E` | Export current view to JSON and CSV |

### Instance Detail View

When viewing instance details (after pressing `Enter`):

| Key | Action |
|-----|--------|
| `P` | View spot price history for this instance |
| `O` | View cost optimization recommendations for this instance |
| `R` | Compare pricing across regions for this instance |
| `Q` / `Esc` | Return to instance list |
| `↑` / `↓` | Scroll detail view |

## Comparison View

After marking 2 instances and pressing `C`:

| Key | Action |
|-----|--------|
| `↑` / `k` | Scroll up |
| `↓` / `j` | Scroll down |
| `Page Up` | Scroll up one page |
| `Page Down` | Scroll down one page |
| `Q` / `Esc` | Return to instance list |

**Comparison Display**:
- Side-by-side specifications
- Price differences highlighted
- Feature differences shown
- Cost savings calculations

## Pricing Modals

### Spot Price History (`P`)

| Key | Action |
|-----|--------|
| `↑` / `k` | Scroll up |
| `↓` / `j` | Scroll down |
| `Q` / `Esc` | Close modal |

**Displays**:
- 30-day price chart (visual)
- Current spot price
- Average, min, max prices
- Standard deviation (volatility)
- Percentage of on-demand price

### Cost Optimization (`O`)

| Key | Action |
|-----|--------|
| `↑` / `k` | Scroll up |
| `↓` / `j` | Scroll down |
| `Q` / `Esc` | Close modal |

**Displays**:
- Spot instance savings potential
- Reserved Instance options (1-year, 3-year)
- Savings Plans options
- Right-sizing suggestions
- Usage pattern recommendations

### Region Comparison (`R`)

| Key | Action |
|-----|--------|
| `↑` / `k` | Scroll up |
| `↓` / `j` | Scroll down |
| `Q` / `Esc` | Close modal |

**Displays**:
- All AWS regions
- On-demand and spot pricing for each region
- Sorted by price (cheapest first)
- Cost savings by region

## Export

| Key | Action |
|-----|--------|
| `E` | Export current view to JSON and CSV |

**Export Behavior**:
- Exports all instances currently visible (respects filters and search)
- Creates two files: `instancepedia_export.json` and `instancepedia_export.csv`
- Includes all specifications and pricing data
- Files saved to current working directory

**Export Confirmation Modal**:
- Shows export location
- Press `Enter` or `Space` to confirm
- Press `Esc` or `Q` to cancel

## Status Bar

The status bar at the bottom shows:

- **Left Side**:
  - Active filters indicator (if any)
  - Current search term (if searching)
  - Marked instances count (if any marked)

- **Right Side**:
  - Current sort order
  - Total instances shown / Total instances available

Example: `Filters: 3 active | Marked: 2 | Sort: Price (Low-High) | Showing: 45/823`

## Help Modal

| Key | Action |
|-----|--------|
| `?` | Show help modal (this reference) |
| `↑` / `↓` | Scroll help text |
| `Page Up` / `Page Down` | Scroll by page |
| `Q` / `Esc` / `Space` / `Enter` | Close help modal |

## Vim-Style Navigation

Enable with `vim_keys = true` in `~/.instancepedia/config.toml`.

When enabled:

| Standard | Vim | Action |
|----------|-----|--------|
| `↑` | `k` | Move up |
| `↓` | `j` | Move down |
| `←` | `h` | Collapse / Move left |
| `→` | `l` | Expand / Move right |

**Note**: Arrow keys still work when Vim keys are enabled.

## Global Actions

Available from any screen:

| Key | Action |
|-----|--------|
| `?` | Show help |
| `Q` | Quit (or go back one level) |
| `Esc` | Cancel / Go back |
| `Ctrl+C` | Force quit |

## Tips

### Efficient Workflow

1. **Quick Search**: Press `/` and start typing immediately
2. **Filter First**: Press `F`, set filters, then browse refined results
3. **Mark and Compare**: Mark 2 similar instances with `C`, press `V` to compare side-by-side
4. **Check Spot History**: Before using spot, press `P` to check price stability
5. **Optimize**: Press `O` to get automated recommendations

### Power User Shortcuts

- **Fast Navigation**: Use `Home` / `End` to jump to top/bottom
- **Page Scrolling**: `Page Up` / `Page Down` for quick browsing
- **Sort Cycling**: Tap `S` repeatedly to find best sort order
- **Preset Workflow**: Create custom presets with `F` → Set Filters → Save Preset

### Keyboard-Only Operation

Instancepedia is fully keyboard-driven:
- No mouse required
- All features accessible via keyboard
- Efficient for terminal-focused workflows
- Works great over SSH

## Context-Sensitive Keys

Some keys have different meanings depending on context:

- **`Enter`**:
  - In instance list: View details
  - In filter modal: Apply filters
  - In help modal: Close help

- **`Q` / `Esc`**:
  - In main list: Quit application
  - In detail view: Return to list
  - In modal: Close modal
  - In filter modal: Cancel without applying

- **`Space`**:
  - In tree view: Expand/collapse node
  - In filter modal checkbox: Toggle checkbox
  - In export modal: Confirm export

## Accessibility

### Screen Reader Support

- All UI elements have descriptive labels
- Status updates announced
- Modal titles and content clearly structured

### High Contrast

Instancepedia uses terminal color scheme:
- Respects terminal's color settings
- Works in light and dark themes
- Clear visual hierarchy

### Keyboard-Only

- 100% keyboard navigable
- No mouse required
- Clear focus indicators
- Logical tab order

## Configuration

Customize keyboard behavior in `~/.instancepedia/config.toml`:

```toml
# Enable Vim-style hjkl navigation
vim_keys = true

# (More configuration options in CONFIGURATION.md)
```

## Troubleshooting

**Keys not responding?**
- Ensure TUI has focus (click terminal if needed)
- Check if terminal emulator captures the key (some intercept function keys)
- Try alternative keys (e.g., `Q` vs `Esc`)

**Vim keys not working?**
- Check `vim_keys = true` in `~/.instancepedia/config.toml`
- Restart instancepedia after changing config

**Help modal not showing?**
- Press `Shift+/` (question mark) clearly
- Try pressing `?` multiple times
- Check terminal keyboard layout

## See Also

- [QUICKSTART.md](QUICKSTART.md) - Get started in 5 minutes
- [FEATURES.md](FEATURES.md) - Complete feature list
- [CONFIGURATION.md](CONFIGURATION.md) - Customize settings
- [CLI_REFERENCE.md](CLI_REFERENCE.md) - CLI commands (non-interactive)
