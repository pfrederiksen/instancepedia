"""Instance type list screen"""

import asyncio
import re
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Tree, Input, Static, Label
from textual.screen import Screen
from textual import events
from typing import TYPE_CHECKING
from collections import defaultdict

if TYPE_CHECKING:
    from textual.widgets.tree import TreeNode

from src.models.instance_type import InstanceType
from src.services.free_tier_service import FreeTierService
from src.debug import DebugLog, DebugPane
from src.config.settings import Settings
from textual.containers import Vertical
from src.ui.region_selector import RegionSelector
from src.ui.filter_modal import FilterModal, FilterCriteria
from src.ui.sort_options import SortOption


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
        ("f", "show_filters", "Filters"),
        ("s", "cycle_sort", "Sort"),
        ("r", "retry_pricing", "Retry Pricing"),
        ("/", "focus_search", "Search"),
        ("c", "mark_for_comparison", "Mark for Compare"),
        ("v", "view_comparison", "View Compare"),
        ("e", "export_instances", "Export to File"),
    ]

    def __init__(self, instance_types: list[InstanceType], region: str):
        super().__init__()
        self.all_instance_types = instance_types
        self.filtered_instance_types = instance_types
        self._region = region  # Use _region to avoid conflict with Screen.region property
        self.free_tier_filter = False  # Deprecated - kept for backwards compatibility
        self.search_term = ""
        self.filter_criteria = FilterCriteria()  # Advanced filter criteria
        self.sort_option = SortOption.DEFAULT  # Current sort option
        self._pricing_loading = True  # Track if pricing is being loaded
        self._pricing_loaded_count = 0  # Track how many prices have been loaded
        self._pricing_failed_count = 0  # Track how many pricing requests failed
        self._pricing_error_message = None  # Store last pricing error message
        self._instance_type_map: dict[str, InstanceType] = {}  # Map instance type names to objects
        self._family_nodes: list['TreeNode'] = []  # Store family nodes to expand when category expands
        self._expanded_categories: set = set()  # Track expanded categories to preserve state
        self._expanded_families: set = set()  # Track expanded families to preserve state
        self._last_pricing_update_count = 0  # Track pricing updates to throttle tree rebuilds
        self._cache_hits = 0  # Track actual cache hits during pricing fetch
        self._total_prices = 0  # Track total prices loaded
        self._marked_for_comparison: list[InstanceType] = []  # Track instances marked for comparison
        self._settings = Settings()  # Load settings for vim_keys and other options
        self._family_instances: dict[str, list[InstanceType]] = {}  # Lazy loading: instances per family
        self._populated_families: set = set()  # Track which families have had their instances added

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
                    "Enter: View | /: Search | F: Filters | S: Sort | R: Retry | C: Mark | V: Compare | E: Export | Esc: Back | Q: Quit",
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

    def _group_instances_by_family(self, instances: list[InstanceType]) -> dict[str, list[InstanceType]]:
        """Group instances by family"""
        families = defaultdict(list)
        for instance in instances:
            family = extract_family_name(instance.instance_type)
            families[family].append(instance)

        # Sort instances within each family using the current sort option
        for family in families:
            families[family] = self.sort_option.sort(families[family])

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

        # Format instance storage
        storage_str = None
        if instance.instance_storage_info and instance.instance_storage_info.total_size_in_gb:
            storage_gb = instance.instance_storage_info.total_size_in_gb
            nvme_indicator = " NVMe" if instance.instance_storage_info.nvme_support == "required" else ""
            storage_str = f"{storage_gb}GB{nvme_indicator}"

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
            memory_str
        ]

        # Add storage if available
        if storage_str:
            label_parts.append(storage_str)

        # Add pricing
        label_parts.append(price_str)

        if is_free_tier:
            label_parts.append("🆓")

        # Add comparison marker if instance is marked
        if instance in self._marked_for_comparison:
            label_parts.append("[COMPARE]")

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
        categories: dict[str, dict[str, list[InstanceType]]] = defaultdict(dict)
        for family, instances in families.items():
            category = get_family_category(family)
            categories[category][family] = instances
        
        # Sort categories and families
        sorted_categories = sorted(categories.keys())
        
        # Build tree structure: Root -> Categories -> Families -> Instances (lazy loaded)
        root = tree.root

        # Store instance type mapping for navigation
        self._instance_type_map.clear()
        self._family_nodes.clear()
        self._family_instances.clear()  # Clear lazy loading cache
        self._populated_families.clear()  # Reset populated families
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
                    expand=family_expanded,  # Expanded if category is expanded or was previously expanded
                    allow_expand=True  # Allow expansion even without children (for lazy loading)
                )
                # Store family node reference to ensure it's expanded when category expands
                self._family_nodes.append(family_node)

                # Store instances for lazy loading (keyed by family name)
                self._family_instances[family] = instances

                # Store in instance map for navigation (always needed)
                for instance in instances:
                    self._instance_type_map[instance.instance_type] = instance

                # If family should be expanded, populate it immediately
                if family_expanded:
                    self._populate_family_instances(family_node, family)
        
        # Expand root node by default
        try:
            root = tree.root
            root.expand()
        except Exception:
            pass  # Ignore if expansion fails

        # Update status bar
        self._update_status_bar()

    def _populate_family_instances(self, family_node: 'TreeNode', family_name: str) -> None:
        """Lazy-load instance nodes for a family when expanded.

        This method is called when a family node is expanded for the first time.
        It adds instance leaf nodes to the family node.
        """
        # Skip if already populated
        if family_name in self._populated_families:
            return

        # Get instances for this family
        instances = self._family_instances.get(family_name, [])

        # Add instance nodes (leaves)
        for instance in instances:
            label = self._format_instance_label(instance)
            # Store instance type as node data for easy retrieval
            family_node.add_leaf(label, data=instance.instance_type)

        # Mark as populated
        self._populated_families.add(family_name)

    def _update_status_bar(self) -> None:
        """Update the status bar with current filter, sort, and pricing information"""
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

        # Show active filters indicator
        if self.filter_criteria.has_active_filters():
            status += " | 🔍 Filters active"
        elif self.free_tier_filter:
            # Backwards compatibility
            status += " | [Free Tier Filter Active]"

        # Show sort order if not default
        if self.sort_option != SortOption.DEFAULT:
            status += f" | 📊 {self.sort_option.display_name}"

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
        elif self._pricing_failed_count > 0:
            # Show failed pricing count and offer retry
            status += f" | ⚠️ {self._pricing_failed_count} prices unavailable (Press R to retry)"
        elif self._total_prices > 0:
            # Show cache statistics in status bar
            cache_pct = (self._cache_hits / self._total_prices * 100) if self._total_prices > 0 else 0
            status += f" | 📦 Cache: {cache_pct:.0f}%"

        self.query_one("#status-text", Static).update(status)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes"""
        if event.input.id == "search-input":
            self.search_term = event.value.lower()
            self._apply_filters()

    def _apply_filters(self) -> None:
        """Apply search and attribute filters"""
        filtered = self.all_instance_types

        # Apply filters in phases
        filtered = self._apply_search_filter(filtered)
        filtered = self._apply_vcpu_filters(filtered)
        filtered = self._apply_memory_filters(filtered)
        filtered = self._apply_boolean_filters(filtered)
        filtered = self._apply_processor_filters(filtered)
        filtered = self._apply_network_filters(filtered)
        filtered = self._apply_family_filter(filtered)
        filtered = self._apply_storage_filters(filtered)
        filtered = self._apply_price_filter(filtered)

        self.filtered_instance_types = filtered
        # Preserve expanded state when filtering
        self._populate_tree()

    def _apply_search_filter(self, instances: list[InstanceType]) -> list[InstanceType]:
        """Apply search term filter"""
        if not self.search_term:
            return instances

        return [
            inst for inst in instances
            if self.search_term in inst.instance_type.lower()
        ]

    def _apply_vcpu_filters(self, instances: list[InstanceType]) -> list[InstanceType]:
        """Apply vCPU min/max filters"""
        filtered = instances
        criteria = self.filter_criteria

        if criteria.min_vcpu is not None:
            filtered = [inst for inst in filtered if inst.vcpu_info.default_vcpus >= criteria.min_vcpu]
        if criteria.max_vcpu is not None:
            filtered = [inst for inst in filtered if inst.vcpu_info.default_vcpus <= criteria.max_vcpu]

        return filtered

    def _apply_memory_filters(self, instances: list[InstanceType]) -> list[InstanceType]:
        """Apply memory min/max filters"""
        filtered = instances
        criteria = self.filter_criteria

        if criteria.min_memory_gb is not None:
            filtered = [inst for inst in filtered if inst.memory_info.size_in_gb >= criteria.min_memory_gb]
        if criteria.max_memory_gb is not None:
            filtered = [inst for inst in filtered if inst.memory_info.size_in_gb <= criteria.max_memory_gb]

        return filtered

    def _apply_boolean_filters(self, instances: list[InstanceType]) -> list[InstanceType]:
        """Apply boolean filters: GPU, current generation, burstable, free tier"""
        free_tier_service = FreeTierService()
        filtered = instances
        criteria = self.filter_criteria

        # Backwards compatible free tier filter (deprecated)
        if self.free_tier_filter:
            filtered = [
                inst for inst in filtered
                if free_tier_service.is_eligible(inst.instance_type)
            ]

        # GPU filter
        if criteria.gpu_filter == "yes":
            filtered = [inst for inst in filtered if inst.gpu_info and inst.gpu_info.total_gpu_count > 0]
        elif criteria.gpu_filter == "no":
            filtered = [inst for inst in filtered if not inst.gpu_info or inst.gpu_info.total_gpu_count == 0]

        # Current generation filter
        if criteria.current_generation == "yes":
            filtered = [inst for inst in filtered if inst.current_generation]
        elif criteria.current_generation == "no":
            filtered = [inst for inst in filtered if not inst.current_generation]

        # Burstable performance filter
        if criteria.burstable == "yes":
            filtered = [inst for inst in filtered if inst.burstable_performance_supported]
        elif criteria.burstable == "no":
            filtered = [inst for inst in filtered if not inst.burstable_performance_supported]

        # Free tier filter (from advanced filters)
        if criteria.free_tier == "yes":
            filtered = [inst for inst in filtered if free_tier_service.is_eligible(inst.instance_type)]
        elif criteria.free_tier == "no":
            filtered = [inst for inst in filtered if not free_tier_service.is_eligible(inst.instance_type)]

        return filtered

    def _apply_processor_filters(self, instances: list[InstanceType]) -> list[InstanceType]:
        """Apply architecture and processor family filters"""
        filtered = instances
        criteria = self.filter_criteria

        # Architecture filter
        if criteria.architecture != "any":
            filtered = [
                inst for inst in filtered
                if criteria.architecture in inst.processor_info.supported_architectures
            ]

        # Processor family filter
        if criteria.processor_family != "any":
            if criteria.processor_family == "intel":
                # Intel processors typically don't have specific identifiers in instance names
                # but are implied when not AMD or Graviton
                filtered = [
                    inst for inst in filtered
                    if "amd" not in inst.instance_type.lower() and "arm64" not in inst.processor_info.supported_architectures
                ]
            elif criteria.processor_family == "amd":
                # AMD instances have 'a' suffix (e.g., m5a, c5a, r5a)
                filtered = [
                    inst for inst in filtered
                    if "a." in inst.instance_type or inst.instance_type.endswith("a")
                ]
            elif criteria.processor_family == "graviton":
                # Graviton instances support arm64 architecture
                filtered = [
                    inst for inst in filtered
                    if "arm64" in inst.processor_info.supported_architectures
                ]

        return filtered

    def _apply_network_filters(self, instances: list[InstanceType]) -> list[InstanceType]:
        """Apply network performance filter"""
        criteria = self.filter_criteria

        if criteria.network_performance == "any":
            return instances

        perf_map = {
            "low": ["low", "very low", "up to 5 gigabit"],
            "moderate": ["moderate", "up to 10 gigabit", "up to 12 gigabit"],
            "high": ["high", "10 gigabit", "12 gigabit", "25 gigabit", "up to 25 gigabit"],
            "very_high": ["50 gigabit", "100 gigabit", "200 gigabit", "up to 100 gigabit", "up to 200 gigabit"]
        }
        target_perfs = perf_map.get(criteria.network_performance, [])

        return [
            inst for inst in instances
            if any(perf.lower() in inst.network_info.network_performance.lower() for perf in target_perfs)
        ]

    def _apply_family_filter(self, instances: list[InstanceType]) -> list[InstanceType]:
        """Apply instance family filter (comma-separated list)"""
        criteria = self.filter_criteria

        if not criteria.family_filter.strip():
            return instances

        families = [f.strip().lower() for f in criteria.family_filter.split(",") if f.strip()]
        if not families:
            return instances

        return [
            inst for inst in instances
            if any(extract_family_name(inst.instance_type).lower() == family for family in families)
        ]

    def _apply_storage_filters(self, instances: list[InstanceType]) -> list[InstanceType]:
        """Apply storage type and NVMe support filters"""
        filtered = instances
        criteria = self.filter_criteria

        # Storage type filter
        if criteria.storage_type == "ebs_only":
            filtered = [
                inst for inst in filtered
                if inst.instance_storage_info is None or inst.instance_storage_info.total_size_in_gb is None or inst.instance_storage_info.total_size_in_gb == 0
            ]
        elif criteria.storage_type == "has_instance_store":
            filtered = [
                inst for inst in filtered
                if inst.instance_storage_info and inst.instance_storage_info.total_size_in_gb and inst.instance_storage_info.total_size_in_gb > 0
            ]

        # NVMe support filter
        if criteria.nvme_support == "required":
            filtered = [inst for inst in filtered if inst.instance_storage_info and inst.instance_storage_info.nvme_support == "required"]
        elif criteria.nvme_support == "supported":
            filtered = [inst for inst in filtered if inst.instance_storage_info and inst.instance_storage_info.nvme_support == "supported"]
        elif criteria.nvme_support == "unsupported":
            filtered = [inst for inst in filtered if not inst.instance_storage_info or not inst.instance_storage_info.nvme_support or inst.instance_storage_info.nvme_support == "unsupported"]

        return filtered

    def _apply_price_filter(self, instances: list[InstanceType]) -> list[InstanceType]:
        """Apply price range filter (only filters instances with pricing data)"""
        criteria = self.filter_criteria

        if criteria.min_price is None and criteria.max_price is None:
            return instances

        def matches_price_range(inst):
            # Only filter instances that have pricing data
            if not inst.pricing or inst.pricing.on_demand_price is None:
                # Keep instances without pricing if we're filtering by price
                # (they might get priced later)
                return True

            price = inst.pricing.on_demand_price
            if criteria.min_price is not None and price < criteria.min_price:
                return False
            if criteria.max_price is not None and price > criteria.max_price:
                return False
            return True

        return [inst for inst in instances if matches_price_range(inst)]

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
        """Handle tree node expansion - track expanded state, lazy-load instances, and expand family nodes"""
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
                                family_label = str(family_node.label)
                                family_name = self._extract_family_name(family_label)
                                # Lazy-load instances for this family
                                self._populate_family_instances(family_node, family_name)
                                family_node.expand()
                                self._expanded_families.add(family_name)
                        except Exception:
                            pass
                else:
                    # This is a family node - extract family name (without count)
                    family_name = self._extract_family_name(node_label)
                    self._expanded_families.add(family_name)
                    # Lazy-load instances for this family
                    self._populate_family_instances(node, family_name)
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
        """Handle key presses including vim-style navigation (hjkl)"""
        tree = self.query_one("#instance-tree", Tree)

        # Vim-style navigation: j=down, k=up, l=expand/enter, h=collapse/back
        # Only active when vim_keys is enabled in settings
        if self._settings.vim_keys:
            if event.key == "j":
                # Move cursor down
                event.prevent_default()
                event.stop()
                tree.action_cursor_down()
                return
            elif event.key == "k":
                # Move cursor up
                event.prevent_default()
                event.stop()
                tree.action_cursor_up()
                return
            elif event.key == "h":
                # Collapse current node or go to parent
                event.prevent_default()
                event.stop()
                cursor_node = tree.cursor_node
                if cursor_node is not None:
                    if cursor_node.is_expanded:
                        cursor_node.collapse()
                    elif cursor_node.parent is not None:
                        tree.select_node(cursor_node.parent)
                return
            elif event.key == "l":
                # Expand node or enter (same as enter for leaf nodes)
                event.prevent_default()
                event.stop()
                cursor_node = tree.cursor_node
                if cursor_node is not None:
                    if cursor_node.data is not None:
                        # Leaf node - navigate to detail
                        instance_type_name = cursor_node.data
                        if instance_type_name in self._instance_type_map:
                            instance = self._instance_type_map[instance_type_name]
                            self._navigate_to_detail(instance)
                    elif not cursor_node.is_expanded:
                        cursor_node.expand()
                return

        # Standard enter key handling
        if event.key == "enter":
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
            loop = asyncio.get_event_loop()
            loop.create_task(dismiss_after_detail_mounts())
        except Exception as e:
            DebugLog.log(f"Error navigating to detail: {e}")
            # Ignore errors if row doesn't exist

    def action_cycle_sort(self) -> None:
        """Cycle to the next sort option"""
        self.sort_option = SortOption.get_next(self.sort_option)
        self._populate_tree()
        # Show sort order in status bar for 3 seconds
        status = self.query_one("#status-text", Static)
        status.update(f"📊 Sorted by: {self.sort_option.display_name}")
        self.set_timer(3.0, lambda: self._update_status_bar())

    def action_retry_pricing(self) -> None:
        """Retry fetching pricing for instances that failed"""
        # Check if there are failed instances
        failed_instances = [
            inst for inst in self.all_instance_types
            if not inst.pricing or inst.pricing.on_demand_price is None
        ]

        if not failed_instances:
            # No failed instances, show message
            status = self.query_one("#status-text", Static)
            status.update("✓ All instances already have pricing")
            self.set_timer(3.0, lambda: self._update_status_bar())
            return

        # Show retry message
        status = self.query_one("#status-text", Static)
        status.update(f"🔄 Retrying pricing for {len(failed_instances)} instances...")

        # Trigger app to retry pricing
        if hasattr(self.app, '_retry_pricing_for_instances'):
            self.app._retry_pricing_for_instances(self, failed_instances)
        else:
            # Fallback: show message that retry isn't available
            status.update("⚠️ Pricing retry not available")
            self.set_timer(3.0, lambda: self._update_status_bar())

    def action_show_filters(self) -> None:
        """Show the filter modal"""
        def handle_filter_result(criteria: FilterCriteria | None) -> None:
            """Handle the filter modal result"""
            if criteria is not None:
                self.filter_criteria = criteria
                self._apply_filters()
                # Update status bar to show active filters
                if criteria.has_active_filters():
                    status = self.query_one("#status-text", Static)
                    filter_count = sum([
                        1 if criteria.min_vcpu is not None else 0,
                        1 if criteria.max_vcpu is not None else 0,
                        1 if criteria.min_memory_gb is not None else 0,
                        1 if criteria.max_memory_gb is not None else 0,
                        1 if criteria.gpu_filter != "any" else 0,
                        1 if criteria.current_generation != "any" else 0,
                        1 if criteria.burstable != "any" else 0,
                        1 if criteria.free_tier != "any" else 0,
                        1 if criteria.architecture != "any" else 0,
                        1 if criteria.processor_family != "any" else 0,
                        1 if criteria.network_performance != "any" else 0,
                        1 if criteria.family_filter.strip() else 0,
                        1 if criteria.storage_type != "any" else 0,
                        1 if criteria.nvme_support != "any" else 0,
                        1 if criteria.min_price is not None else 0,
                        1 if criteria.max_price is not None else 0,
                    ])
                    status.update(f"🔍 {filter_count} filter(s) active - Showing {len(self.filtered_instance_types)} of {len(self.all_instance_types)} instances")
                    # Clear message after 3 seconds
                    self.set_timer(3.0, lambda: self._update_status_bar())

        self.app.push_screen(FilterModal(self.filter_criteria), handle_filter_result)

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
        except Exception as e:
            # Fall back to all regions if we can't fetch accessible ones
            import logging
            logger = logging.getLogger("instancepedia")
            logger.debug(f"Failed to fetch accessible regions: {e}")
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
        loop = asyncio.get_event_loop()
        loop.create_task(dismiss_after_region_mounts())

    def action_mark_for_comparison(self) -> None:
        """Mark/unmark current instance for comparison"""
        tree = self.query_one("#instance-tree", Tree)
        if not tree.cursor_node:
            return

        # Check if this is an instance node (has data)
        if not tree.cursor_node.data:
            return

        instance_type_name = tree.cursor_node.data
        instance = self._instance_type_map.get(instance_type_name)
        if not instance:
            return

        # Toggle marking
        if instance in self._marked_for_comparison:
            self._marked_for_comparison.remove(instance)
            DebugLog.log(f"Unmarked {instance_type_name} for comparison")
        else:
            # Limit to 2 instances for comparison
            if len(self._marked_for_comparison) >= 2:
                # Remove the oldest marked instance
                self._marked_for_comparison.pop(0)
            self._marked_for_comparison.append(instance)
            DebugLog.log(f"Marked {instance_type_name} for comparison ({len(self._marked_for_comparison)}/2)")

        # Rebuild tree to update labels
        self._populate_tree()

        # Update status bar to show marked count
        status = self.query_one("#status-text", Static)
        if len(self._marked_for_comparison) > 0:
            marked_names = [inst.instance_type for inst in self._marked_for_comparison]
            status.update(f"Marked for comparison: {', '.join(marked_names)} ({len(self._marked_for_comparison)}/2)")
        else:
            # Restore normal status
            self._update_status_bar()

    def action_view_comparison(self) -> None:
        """View comparison of marked instances"""
        if len(self._marked_for_comparison) != 2:
            # Show message that we need exactly 2 instances
            status = self.query_one("#status-text", Static)
            if len(self._marked_for_comparison) == 0:
                status.update("No instances marked for comparison. Press 'C' to mark instances.")
            elif len(self._marked_for_comparison) == 1:
                status.update(f"Only 1 instance marked. Mark one more instance with 'C' to compare.")
            return

        # Push comparison screen
        from src.ui.instance_comparison import InstanceComparison
        comparison_screen = InstanceComparison(
            self._marked_for_comparison[0],
            self._marked_for_comparison[1],
            self._region
        )
        self.app.push_screen(comparison_screen)

    def action_export_instances(self) -> None:
        """Export current filtered instances to a file"""
        from datetime import datetime
        from pathlib import Path
        import logging

        logger = logging.getLogger("instancepedia")

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"instancepedia_export_{self._region}_{timestamp}"

        # Export both JSON and CSV for convenience
        export_dir = Path.home() / ".instancepedia" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        json_file = export_dir / f"{base_filename}.json"
        csv_file = export_dir / f"{base_filename}.csv"

        try:
            # Use CLI formatters to export
            from src.cli.output import JSONFormatter, CSVFormatter

            json_formatter = JSONFormatter()
            csv_formatter = CSVFormatter()

            # Export JSON
            json_output = json_formatter.format_instance_list(
                self.filtered_instance_types,
                self._region
            )
            with open(json_file, 'w') as f:
                f.write(json_output)

            # Export CSV
            csv_output = csv_formatter.format_instance_list(
                self.filtered_instance_types,
                self._region
            )
            with open(csv_file, 'w') as f:
                f.write(csv_output)

            # Update status bar with success message
            status = self.query_one("#status-text", Static)
            status.update(f"✓ Exported {len(self.filtered_instance_types)} instances to {export_dir.name}/")
            DebugLog.log(f"Exported to {json_file} and {csv_file}")

            # Clear message after 5 seconds
            self.set_timer(5.0, lambda: self._update_status_bar())

        except Exception as e:
            logger.error(f"Failed to export instances: {e}", exc_info=True)
            status = self.query_one("#status-text", Static)
            status.update(f"✗ Export failed: {str(e)}")
            DebugLog.log(f"Export error: {e}")

    def action_quit(self) -> None:
        """Quit application"""
        self.app.exit()
    
    def mark_pricing_loading(self, loading: bool, cache_hits: int = 0, total_prices: int = 0, failed_count: int = 0) -> None:
        """Mark pricing loading state and update cache statistics

        Args:
            loading: Whether pricing is currently loading
            cache_hits: Number of prices loaded from cache (only used when loading=False)
            total_prices: Total number of prices loaded (only used when loading=False)
            failed_count: Number of pricing requests that failed (only used when loading=False)
        """
        self._pricing_loading = loading
        if not loading:
            # Store cache statistics and failed count when pricing is complete
            self._cache_hits = cache_hits
            self._total_prices = total_prices
            self._pricing_failed_count = failed_count
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

                # Show loading status
                header.update(f"💰 ⏳ Loading on-demand prices... ({pricing_loaded}/{total} loaded)")
                header.styles.color = "yellow"
            else:
                # Show final cache statistics (from actual pricing fetch)
                if self._total_prices > 0:
                    cache_pct = (self._cache_hits / self._total_prices * 100) if self._total_prices > 0 else 0
                    if self._cache_hits > 0:
                        header.update(f"💰 Pricing loaded: {self._cache_hits}/{self._total_prices} from cache ({cache_pct:.0f}%)")
                        header.styles.color = "green"
                    else:
                        header.update(f"💰 Pricing loaded: {self._total_prices} prices (0% cached)")
                        header.styles.color = "cyan"
                else:
                    header.update("")
        except Exception:
            pass  # Header might not exist yet
