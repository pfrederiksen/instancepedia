"""Instance type list screen"""

import re
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Tree, Input, Static, Label
from textual.screen import Screen
from textual import events
from typing import List, Optional, Dict, TYPE_CHECKING
from collections import defaultdict

if TYPE_CHECKING:
    from textual.widgets.tree import TreeNode

from src.models.instance_type import InstanceType
from src.services.free_tier_service import FreeTierService
from src.debug import DebugLog, DebugPane
from textual.containers import Vertical
from src.ui.region_selector import RegionSelector


def extract_family_name(instance_type: str) -> str:
    """
    Extract family name from instance type.
    
    Examples:
        t2.micro -> t2
        m5.large -> m5
        c6i.xlarge -> c6i
        r6a.2xlarge -> r6a
    
    Args:
        instance_type: Instance type string (e.g., "t2.micro")
    
    Returns:
        Family name (e.g., "t2")
    """
    # Split by dot and take the first part
    parts = instance_type.split('.')
    if parts:
        return parts[0]
    return instance_type


def get_family_category(family: str) -> str:
    """
    Get category name for a family.
    
    Args:
        family: Family name (e.g., "t2", "m5", "c6i")
    
    Returns:
        Category name for display
    """
    family_lower = family.lower() if family else ''
    first_char = family_lower[0] if family_lower else ''
    
    # Check for specific prefixes first (before first character matching)
    # ML and HPC instances
    if family_lower.startswith('trn'):  # Trainium (ML training)
        return 'Accelerated Computing'
    if family_lower.startswith('inf'):  # Inferentia (ML inference)
        return 'Accelerated Computing'
    if family_lower.startswith('dl'):  # Deep Learning
        return 'Accelerated Computing'
    if family_lower.startswith('hpc'):  # High Performance Computing
        return 'Accelerated Computing'
    
    # Special instance types
    if family_lower.startswith('mac'):
        return 'Mac Instances'
    if family_lower.startswith('x1'):
        return 'Memory Optimized (X1e)'
    if family_lower.startswith('z1'):
        return 'Memory Optimized (Z1d)'
    
    # Map family prefixes to categories
    category_map = {
        't': 'Burstable Performance',
        'm': 'General Purpose',
        'c': 'Compute Optimized',
        'r': 'Memory Optimized',
        'x': 'Memory Optimized (X1e)',
        'z': 'Memory Optimized (Z1d)',
        'd': 'Dense Storage',
        'h': 'High I/O',
        'i': 'Storage Optimized',
        'g': 'GPU Instances',
        'p': 'GPU Instances',
        'f': 'FPGA Instances',
        'a': 'ARM-based (Graviton)',
    }
    
    # Check first character
    if first_char in category_map:
        return category_map[first_char]
    
    # Default
    return 'Other'


class InstanceList(Screen):
    """Screen for displaying list of instance types"""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "back", "Back"),
        ("f", "toggle_free_tier_filter", "Filter Free Tier"),
        ("/", "focus_search", "Search"),
    ]

    def __init__(self, instance_types: List[InstanceType], region: str):
        super().__init__()
        self.all_instance_types = instance_types
        self.filtered_instance_types = instance_types
        self._region = region  # Use _region to avoid conflict with Screen.region property
        self.free_tier_filter = False
        self.search_term = ""
        self._pricing_loading = True  # Track if pricing is being loaded
        self._pricing_loaded_count = 0  # Track how many prices have been loaded
        self._instance_type_map: Dict[str, InstanceType] = {}  # Map instance type names to objects
        self._family_nodes: List['TreeNode'] = []  # Store family nodes to expand when category expands
        self._expanded_categories: set = set()  # Track expanded categories to preserve state
        self._expanded_families: set = set()  # Track expanded families to preserve state
        self._last_pricing_update_count = 0  # Track pricing updates to throttle tree rebuilds

    def compose(self) -> ComposeResult:
        with Vertical():
            with Container(id="list-container"):
                yield Static(
                    f"EC2 Instance Types - {self._region}",
                    id="header"
                )
                yield Static(
                    "",
                    id="pricing-status-header"
                )
                with Horizontal(id="search-container"):
                    yield Label("Search: ", id="search-label")
                    yield Input(
                        placeholder="Type to search...",
                        id="search-input"
                    )
                yield Tree("Instance Types", id="instance-tree")
                with Horizontal(id="status-bar"):
                    yield Static("", id="status-text")
                yield Static(
                    "Enter: View Details | Space: Expand/Collapse | Esc: Back | Q: Quit | /: Search | F: Filter Free Tier",
                    id="help-text"
                )
            if DebugLog.is_enabled():
                yield DebugPane()

    def on_mount(self) -> None:
        """Initialize the tree when screen is mounted"""
        tree = self.query_one("#instance-tree", Tree)
        self._update_pricing_header()
        self._populate_tree()
        self._tree_initialized = True
        # Focus the tree so it can receive keyboard input and scroll
        tree.focus()

    def _group_instances_by_family(self, instances: List[InstanceType]) -> Dict[str, List[InstanceType]]:
        """Group instances by family"""
        families = defaultdict(list)
        for instance in instances:
            family = extract_family_name(instance.instance_type)
            families[family].append(instance)
        
        # Sort instances within each family
        for family in families:
            families[family].sort(key=lambda x: x.instance_type)
        
        return dict(families)

    def _format_instance_label(self, instance: InstanceType) -> str:
        """Format instance type for display in tree"""
        free_tier_service = FreeTierService()
        is_free_tier = free_tier_service.is_eligible(instance.instance_type)
        
        # Format memory
        memory_gb = instance.memory_info.size_in_gb
        if memory_gb < 1:
            memory_str = f"{memory_gb:.2f}GB"
        else:
            memory_str = f"{memory_gb:.1f}GB"
        
        # Format pricing
        if instance.pricing and instance.pricing.on_demand_price is not None:
            price_str = f"${instance.pricing.on_demand_price:.4f}/hr"
        elif self._pricing_loading:
            price_str = "⏳ Loading..."
        else:
            price_str = "N/A"
        
        # Build label
        label_parts = [
            instance.instance_type,
            f"{instance.vcpu_info.default_vcpus}vCPU",
            memory_str,
            price_str
        ]
        
        if is_free_tier:
            label_parts.append("🆓")
        
        return " | ".join(label_parts)

    def _populate_tree(self) -> None:
        """Populate the tree with instance types grouped by family"""
        tree = self.query_one("#instance-tree", Tree)
        
        # Store expanded state before clearing (if tree has content and we want to preserve state)
        # Only preserve state if this is a rebuild (not initial population)
        preserve_state = hasattr(self, '_tree_initialized') and self._tree_initialized
        
        if preserve_state:
            try:
                root = tree.root
                # Try to get expanded state - use multiple methods to check
                if hasattr(root, 'children') or hasattr(root, '_children'):
                    children = getattr(root, 'children', None) or getattr(root, '_children', [])
                    for category_node in children:
                        try:
                            # Check if expanded using various methods
                            is_expanded = (
                                getattr(category_node, 'is_expanded', False) or
                                getattr(category_node, 'expanded', False) or
                                (hasattr(category_node, '_expanded') and category_node._expanded)
                            )
                            if is_expanded:
                                category_label = str(category_node.label)
                                # Extract category name without count for state tracking
                                category_name = self._extract_category_name(category_label)
                                self._expanded_categories.add(category_name)
                                # Check family nodes
                                family_children = getattr(category_node, 'children', None) or getattr(category_node, '_children', [])
                                for family_node in family_children:
                                    try:
                                        family_expanded = (
                                            getattr(family_node, 'is_expanded', False) or
                                            getattr(family_node, 'expanded', False) or
                                            (hasattr(family_node, '_expanded') and family_node._expanded)
                                        )
                                        if family_expanded:
                                            family_label = str(family_node.label)
                                            # Extract family name without count for state tracking
                                            family_name = self._extract_family_name(family_label)
                                            self._expanded_families.add(family_name)
                                    except Exception:
                                        pass
                        except Exception:
                            pass
            except Exception:
                pass  # Ignore errors when storing state
        
        tree.clear()
        
        # Group instances by family
        families = self._group_instances_by_family(self.filtered_instance_types)
        
        # Group families by category
        categories: Dict[str, Dict[str, List[InstanceType]]] = defaultdict(dict)
        for family, instances in families.items():
            category = get_family_category(family)
            categories[category][family] = instances
        
        # Sort categories and families
        sorted_categories = sorted(categories.keys())
        
        # Build tree structure: Root -> Categories -> Families -> Instances
        root = tree.root
        
        # Store instance type mapping for navigation
        self._instance_type_map.clear()
        self._family_nodes.clear()
        # Don't clear expanded state - we want to preserve it across rebuilds
        
        for category in sorted_categories:
            category_families = categories[category]
            sorted_families = sorted(category_families.keys())
            
            # Count instances in this category
            category_count = sum(len(instances) for instances in category_families.values())
            
            # Create category node (branch)
            # Use category name without count for state tracking, but display with count
            category_label = f"{category} ({category_count} instances)"
            # Restore expanded state using category name only (without count)
            category_expanded = category in self._expanded_categories if preserve_state else False
            category_node = root.add(
                category_label,
                expand=category_expanded  # Restore previous state or default to collapsed
            )
            
            for family in sorted_families:
                instances = category_families[family]
                
                # Create family node (branch) with count
                # Use family name without count for state tracking, but display with count
                family_label = f"{family} ({len(instances)} instances)"
                # Restore expanded state using family name only (without count)
                family_expanded = (
                    (family in self._expanded_families or category_expanded) if preserve_state 
                    else category_expanded  # If category is expanded, expand families too
                )
                family_node = category_node.add(
                    family_label,
                    expand=family_expanded  # Expanded if category is expanded or was previously expanded
                )
                # Store family node reference to ensure it's expanded when category expands
                self._family_nodes.append(family_node)
                
                # Add instance nodes (leaves)
                for instance in instances:
                    label = self._format_instance_label(instance)
                    # Store instance type as node data for easy retrieval
                    instance_node = family_node.add_leaf(label, data=instance.instance_type)
                    # Also store in mapping for navigation
                    self._instance_type_map[instance.instance_type] = instance
        
        # Expand root node by default
        try:
            root = tree.root
            root.expand()
        except Exception:
            pass  # Ignore if expansion fails

        # Update status bar
        free_tier_service = FreeTierService()
        total = len(self.all_instance_types)
        filtered = len(self.filtered_instance_types)
        free_tier_count = sum(
            1 for inst in self.filtered_instance_types
            if free_tier_service.is_eligible(inst.instance_type)
        )
        status = f"Showing {filtered} of {total} instance types"
        if free_tier_count > 0:
            status += f" | 🆓 {free_tier_count} free tier eligible"
        if self.free_tier_filter:
            status += " | [Free Tier Filter Active]"
        
        # Add pricing loading status
        if self._pricing_loading:
            pricing_loaded = sum(
                1 for inst in self.filtered_instance_types
                if inst.pricing and inst.pricing.on_demand_price is not None
            )
            if filtered > 0:
                status += f" | ⏳ Loading prices... ({pricing_loaded}/{filtered})"
            else:
                status += " | ⏳ Loading prices..."
        
        self.query_one("#status-text", Static).update(status)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes"""
        if event.input.id == "search-input":
            self.search_term = event.value.lower()
            self._apply_filters()

    def _apply_filters(self) -> None:
        """Apply search and free tier filters"""
        free_tier_service = FreeTierService()
        filtered = self.all_instance_types

        # Apply search filter
        if self.search_term:
            filtered = [
                inst for inst in filtered
                if self.search_term in inst.instance_type.lower()
            ]

        # Apply free tier filter
        if self.free_tier_filter:
            filtered = [
                inst for inst in filtered
                if free_tier_service.is_eligible(inst.instance_type)
            ]

        self.filtered_instance_types = filtered
        # Preserve expanded state when filtering
        self._populate_tree()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection - navigate to detail view if it's an instance"""
        node = event.node
        # Check if this node has instance type data (leaf node)
        if node.data is not None:
            instance_type_name = node.data
            if instance_type_name in self._instance_type_map:
                instance = self._instance_type_map[instance_type_name]
                self._navigate_to_detail(instance)
    
    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        """Handle tree node expansion - track expanded state and expand family nodes when category expands"""
        node = event.node
        # Track expanded state
        if node.data is None:  # Branch node (category or family)
            node_label = str(node.label)
            # Check if this is a category or family by checking if it has a parent that's a category
            try:
                if hasattr(node, 'parent') and node.parent and node.parent == node.tree.root:
                    # This is a category node - extract category name (without count)
                    category_name = self._extract_category_name(node_label)
                    self._expanded_categories.add(category_name)
                    # Expand all family nodes under this category
                    for family_node in self._family_nodes:
                        try:
                            if hasattr(family_node, 'parent') and family_node.parent == node:
                                family_node.expand()
                                family_label = str(family_node.label)
                                family_name = self._extract_family_name(family_label)
                                self._expanded_families.add(family_name)
                        except Exception:
                            pass
                else:
                    # This is a family node - extract family name (without count)
                    family_name = self._extract_family_name(node_label)
                    self._expanded_families.add(family_name)
            except Exception:
                pass  # Ignore errors
    
    def on_tree_node_collapsed(self, event: Tree.NodeCollapsed) -> None:
        """Handle tree node collapse - remove from expanded state sets"""
        node = event.node
        if node.data is None:  # Branch node (category or family)
            node_label = str(node.label)
            try:
                if hasattr(node, 'parent') and node.parent and node.parent == node.tree.root:
                    # This is a category node - remove category name (without count)
                    category_name = self._extract_category_name(node_label)
                    self._expanded_categories.discard(category_name)
                else:
                    # This is a family node - remove family name (without count)
                    family_name = self._extract_family_name(node_label)
                    self._expanded_families.discard(family_name)
            except Exception:
                pass  # Ignore errors
    
    def _extract_category_name(self, label: str) -> str:
        """Extract category name from label (removes instance count)"""
        # Label format: "Category Name (X instances)" or "Category Name (Subname) (X instances)"
        # Extract just the category name by removing the trailing " (X instances)" pattern
        # Match pattern: " (number instances)" at the end of the string
        # This handles category names that contain parentheses like "Memory Optimized (X1e)"
        pattern = r' \(\d+ instances\)$'
        return re.sub(pattern, '', label)
    
    def _extract_family_name(self, label: str) -> str:
        """Extract family name from label (removes instance count)"""
        # Label format: "family (X instances)"
        # Extract just the family name
        if ' (' in label:
            return label.split(' (')[0]
        return label

    def on_key(self, event: events.Key) -> None:
        """Handle key presses"""
        if event.key == "enter":
            tree = self.query_one("#instance-tree", Tree)
            cursor_node = tree.cursor_node
            if cursor_node is not None:
                # Check if this is a leaf node (instance) or branch node (category/family)
                # If node has data, it's an instance (leaf node) - navigate to details
                if cursor_node.data is not None:
                    event.prevent_default()
                    event.stop()
                    instance_type_name = cursor_node.data
                    if instance_type_name in self._instance_type_map:
                        instance = self._instance_type_map[instance_type_name]
                        self._navigate_to_detail(instance)
                else:
                    # Branch node (category/family) - let Tree handle expand/collapse
                    # Don't prevent default, let the Tree widget handle it naturally
                    pass

    def _navigate_to_detail(self, instance: InstanceType) -> None:
        """Navigate to detail view for selected instance"""
        try:
            # Push detail screen BEFORE dismissing - same pattern as region selector
            from src.ui.instance_detail import InstanceDetail
            detail_screen = InstanceDetail(instance)
            await_push = self.app.push_screen(detail_screen)
            DebugLog.log(f"Pushed detail screen for: {instance.instance_type}")
            self.app.refresh()
            
            # Wait for screen to mount, then dismiss this one
            async def dismiss_after_detail_mounts():
                try:
                    await await_push
                    DebugLog.log("Detail screen mounted, dismissing instance list")
                    await asyncio.sleep(0.1)  # Give it time to render
                    self.dismiss(instance)  # This will trigger the handler but detail is already on top
                except Exception as e:
                    DebugLog.log(f"Error in dismiss_after_detail_mounts: {e}")
            
            # Schedule the async task using the app's event loop
            import asyncio
            loop = asyncio.get_event_loop()
            loop.create_task(dismiss_after_detail_mounts())
        except Exception as e:
            DebugLog.log(f"Error navigating to detail: {e}")
            # Ignore errors if row doesn't exist

    def action_toggle_free_tier_filter(self) -> None:
        """Toggle free tier filter"""
        self.free_tier_filter = not self.free_tier_filter
        self._apply_filters()

    def action_focus_search(self) -> None:
        """Focus the search input"""
        self.query_one("#search-input", Input).focus()

    def action_back(self) -> None:
        """Go back to region selector"""
        # Push region selector BEFORE dismissing - same pattern as detail screen
        try:
            from src.services.aws_client import AWSClient
            aws_client = AWSClient("us-east-1", self.app.settings.aws_profile)
            accessible_regions = aws_client.get_accessible_regions()
        except:
            accessible_regions = None
        
        region_selector = RegionSelector(self.app.current_region or self.app.settings.aws_region, accessible_regions)
        await_push = self.app.push_screen(region_selector)
        self.app.refresh()
        
        # Wait for region selector to mount, then dismiss this screen
        async def dismiss_after_region_mounts():
            try:
                await await_push
                await asyncio.sleep(0.1)  # Give it time to render
                self.dismiss(None)  # This will trigger the handler but region selector is already on top
            except Exception as e:
                DebugLog.log(f"Error in dismiss_after_region_mounts: {e}")
        
        # Schedule the async task using the app's event loop
        import asyncio
        loop = asyncio.get_event_loop()
        loop.create_task(dismiss_after_region_mounts())

    def action_quit(self) -> None:
        """Quit application"""
        self.app.exit()
    
    def mark_pricing_loading(self, loading: bool) -> None:
        """Mark pricing loading state"""
        self._pricing_loading = loading
        self._update_pricing_header()
        # Only rebuild tree if it's the first time (not during pricing updates)
        if not hasattr(self, '_tree_initialized'):
            self._populate_tree()
            self._tree_initialized = True
        elif not loading:
            # Pricing is complete - do a final rebuild to show all pricing
            self._populate_tree()
    
    def update_pricing_progress(self) -> None:
        """Update the tree to reflect pricing progress"""
        self._update_pricing_header()
        # Throttle tree updates - only rebuild every 10 pricing updates or when pricing completes
        # This prevents constant collapsing while still showing progress
        if hasattr(self, '_tree_initialized') and self._tree_initialized:
            self._last_pricing_update_count += 1
            # Rebuild tree every 10 updates or if we have a significant number of new prices
            if self._last_pricing_update_count % 10 == 0:
                # Rebuild with state preservation
                self._populate_tree()
            else:
                # Try to update in place (may not work, but worth trying)
                self._update_tree_pricing()
    
    def _update_tree_pricing(self) -> None:
        """Update pricing information in existing tree nodes without rebuilding"""
        tree = self.query_one("#instance-tree", Tree)
        try:
            root = tree.root
            # Walk through the tree and update instance node labels
            # Root -> Categories -> Families -> Instances
            # Try different ways to access children
            def get_children(node):
                """Get children of a node using various methods"""
                if hasattr(node, 'children'):
                    return node.children
                elif hasattr(node, '_children'):
                    return node._children
                elif hasattr(node, 'get_children'):
                    return node.get_children()
                return []
            
            for category_node in get_children(root):
                for family_node in get_children(category_node):
                    for instance_node in get_children(family_node):
                        if instance_node.data is not None:
                            # This is an instance node - update its label
                            instance_type_name = instance_node.data
                            if instance_type_name in self._instance_type_map:
                                instance = self._instance_type_map[instance_type_name]
                                new_label = self._format_instance_label(instance)
                                # Update the node label - try multiple methods
                                try:
                                    # Method 1: set_label method
                                    if hasattr(instance_node, 'set_label'):
                                        instance_node.set_label(new_label)
                                    # Method 2: Direct label assignment
                                    elif hasattr(instance_node, 'label'):
                                        instance_node.label = new_label
                                    # Method 3: Internal _label attribute
                                    elif hasattr(instance_node, '_label'):
                                        instance_node._label = new_label
                                    # Method 4: Update through tree widget
                                    elif hasattr(tree, 'update_node'):
                                        tree.update_node(instance_node, new_label)
                                except Exception:
                                    # If we can't update in place, that's okay
                                    # The pricing will show on next rebuild
                                    pass
        except Exception:
            # If update fails, that's okay - pricing will show on next rebuild
            pass
    
    def _update_pricing_header(self) -> None:
        """Update the pricing status header"""
        try:
            header = self.query_one("#pricing-status-header", Static)
            if self._pricing_loading:
                # Count instances with on-demand pricing (spot prices loaded separately when viewing details)
                pricing_loaded = sum(
                    1 for inst in self.all_instance_types
                    if inst.pricing and inst.pricing.on_demand_price is not None
                )
                total = len(self.all_instance_types)
                header.update(f"💰 ⏳ Loading on-demand prices... ({pricing_loaded}/{total} loaded)")
                header.styles.color = "yellow"
            else:
                # Hide the header once loading is complete
                header.update("")
        except Exception:
            pass  # Header might not exist yet
