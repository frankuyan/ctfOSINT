"""Platform registry for dynamic module loading."""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import BasePlatform

if TYPE_CHECKING:
    from sherlockml.config import Config, PlatformConfig


class PlatformRegistry:
    """Dynamic platform module loader and registry.
    
    Loads platform modules from:
    1. Built-in platforms in sherlockml.platforms
    2. User plugins from ~/.sherlockml/plugins/
    
    Example:
        >>> registry = PlatformRegistry()
        >>> registry.discover_builtin()
        >>> registry.discover_plugins()
        >>> platforms = registry.get_enabled(config)
    """
    
    def __init__(self, plugins_dir: Path | None = None):
        """Initialize the registry.
        
        Args:
            plugins_dir: Directory containing user plugins.
                        Defaults to ~/.sherlockml/plugins/
        """
        self.plugins_dir = plugins_dir or Path.home() / '.sherlockml' / 'plugins'
        self._platforms: dict[str, type[BasePlatform]] = {}
        self._instances: dict[str, BasePlatform] = {}
    
    @property
    def available_platforms(self) -> list[str]:
        """Get list of all registered platform names."""
        return list(self._platforms.keys())
    
    def register(self, platform_cls: type[BasePlatform]) -> None:
        """Register a platform class.
        
        Args:
            platform_cls: Platform class to register (must have 'name' attribute)
        """
        if not hasattr(platform_cls, 'name'):
            raise ValueError(f"Platform class {platform_cls} missing 'name' attribute")
        
        self._platforms[platform_cls.name] = platform_cls
    
    def get(self, name: str, auth_token: str | None = None) -> BasePlatform | None:
        """Get a platform instance by name.
        
        Args:
            name: Platform name
            auth_token: Optional auth token for the platform
            
        Returns:
            Platform instance or None if not found
        """
        if name not in self._platforms:
            return None
        
        # Cache instances
        cache_key = f"{name}:{auth_token or 'none'}"
        if cache_key not in self._instances:
            self._instances[cache_key] = self._platforms[name](auth_token=auth_token)
        
        return self._instances[cache_key]
    
    def discover_builtin(self) -> int:
        """Discover and register built-in platform modules.
        
        Returns:
            Number of platforms discovered
        """
        count = 0
        
        try:
            from sherlockml import platforms
            platforms_path = Path(platforms.__file__).parent
            
            for module_path in platforms_path.glob("*.py"):
                if module_path.name.startswith("_"):
                    continue
                
                module_name = module_path.stem
                try:
                    module = importlib.import_module(f"sherlockml.platforms.{module_name}")
                    
                    # Find all BasePlatform subclasses in the module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, BasePlatform)
                            and attr is not BasePlatform
                            and hasattr(attr, 'name')
                        ):
                            self.register(attr)
                            count += 1
                            
                except Exception as e:
                    # Log but continue on errors
                    logging.warning("Failed to load platform %s: %s", module_name, e)
                    
        except ImportError:
            # No platforms module yet
            pass
        
        return count
    
    def discover_plugins(self) -> int:
        """Discover and register user plugins from plugins directory.
        
        Returns:
            Number of plugins discovered
        """
        if not self.plugins_dir.exists():
            return 0
        
        count = 0
        
        for plugin_path in self.plugins_dir.glob("*.py"):
            if plugin_path.name.startswith("_"):
                continue
            
            try:
                # Load the module dynamically
                spec = importlib.util.spec_from_file_location(
                    f"sherlockml_plugin_{plugin_path.stem}",
                    plugin_path,
                )
                if spec is None or spec.loader is None:
                    continue
                
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)
                
                # Find all BasePlatform subclasses
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BasePlatform)
                        and attr is not BasePlatform
                        and hasattr(attr, 'name')
                    ):
                        self.register(attr)
                        count += 1
                        
            except Exception as e:
                logging.warning("Failed to load plugin %s: %s", plugin_path, e)
        
        return count
    
    def get_enabled(
        self,
        config: "Config",
        sort_by_priority: bool = True,
    ) -> list[BasePlatform]:
        """Get list of enabled platforms based on configuration.
        
        Args:
            config: Application configuration
            sort_by_priority: Sort by priority_weight descending
            
        Returns:
            List of enabled platform instances
        """
        enabled: list[tuple[float, BasePlatform]] = []
        
        for name, platform_cls in self._platforms.items():
            platform_config = config.get_platform(name)
            
            if not platform_config.enabled:
                continue
            
            platform = self.get(name, auth_token=platform_config.auth_token)
            if platform:
                enabled.append((platform_config.priority_weight, platform))
        
        if sort_by_priority:
            enabled.sort(key=lambda x: x[0], reverse=True)
        
        return [p for _, p in enabled]
    
    def get_by_category(
        self,
        category: str,
        config: "Config" | None = None,
    ) -> list[BasePlatform]:
        """Get platforms by category.
        
        Args:
            category: Category to filter by (e.g., 'social', 'code')
            config: Optional config for auth tokens
            
        Returns:
            List of platforms in the category
        """
        from sherlockml.enum.platform_base import PlatformCategory
        
        try:
            cat = PlatformCategory(category.lower())
        except ValueError:
            return []
        
        result: list[BasePlatform] = []
        
        for name, platform_cls in self._platforms.items():
            if hasattr(platform_cls, 'category') and platform_cls.category == cat:
                auth_token = None
                if config:
                    auth_token = config.get_platform(name).auth_token
                
                platform = self.get(name, auth_token=auth_token)
                if platform:
                    result.append(platform)
        
        return result


# Global registry instance
_registry: PlatformRegistry | None = None


def get_registry() -> PlatformRegistry:
    """Get the global platform registry.
    
    Returns:
        Global PlatformRegistry instance
    """
    global _registry
    
    if _registry is None:
        _registry = PlatformRegistry()
        _registry.discover_builtin()
        _registry.discover_plugins()
    
    return _registry
