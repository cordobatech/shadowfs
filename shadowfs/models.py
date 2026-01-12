"""
Models - Model registry and selector for LLM interactions.
Similar to GitHub Copilot's model selector GUI.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class ModelProvider(Enum):
    """Supported model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    OLLAMA = "ollama"
    CUSTOM = "custom"


@dataclass
class ModelConfig:
    """Configuration for an LLM model."""
    id: str
    name: str
    provider: ModelProvider
    description: str = ""
    max_tokens: int = 4096
    supports_vision: bool = False
    supports_tools: bool = True
    supports_streaming: bool = True
    context_window: int = 8192
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    api_key_env: str = ""
    endpoint: Optional[str] = None
    default_params: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def display_name(self) -> str:
        """Get display name with provider."""
        return f"{self.name} ({self.provider.value})"
    
    @property
    def is_available(self) -> bool:
        """Check if model is available (API key set)."""
        if not self.api_key_env:
            return True  # No key required (e.g., Ollama)
        return bool(os.environ.get(self.api_key_env))
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider.value,
            "description": self.description,
            "max_tokens": self.max_tokens,
            "supports_vision": self.supports_vision,
            "supports_tools": self.supports_tools,
            "context_window": self.context_window,
        }


# Pre-configured models (like Copilot's model list)
BUILTIN_MODELS: Dict[str, ModelConfig] = {
    # OpenAI Models
    "gpt-4o": ModelConfig(
        id="gpt-4o",
        name="GPT-4o",
        provider=ModelProvider.OPENAI,
        description="Most capable OpenAI model, multimodal",
        max_tokens=16384,
        supports_vision=True,
        context_window=128000,
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015,
        api_key_env="OPENAI_API_KEY",
    ),
    "gpt-4o-mini": ModelConfig(
        id="gpt-4o-mini",
        name="GPT-4o Mini",
        provider=ModelProvider.OPENAI,
        description="Fast and affordable, good for most tasks",
        max_tokens=16384,
        supports_vision=True,
        context_window=128000,
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
        api_key_env="OPENAI_API_KEY",
    ),
    "gpt-4-turbo": ModelConfig(
        id="gpt-4-turbo",
        name="GPT-4 Turbo",
        provider=ModelProvider.OPENAI,
        description="Previous flagship with vision",
        max_tokens=4096,
        supports_vision=True,
        context_window=128000,
        cost_per_1k_input=0.01,
        cost_per_1k_output=0.03,
        api_key_env="OPENAI_API_KEY",
    ),
    "o1": ModelConfig(
        id="o1",
        name="o1",
        provider=ModelProvider.OPENAI,
        description="Advanced reasoning model",
        max_tokens=100000,
        supports_vision=True,
        context_window=200000,
        cost_per_1k_input=0.015,
        cost_per_1k_output=0.06,
        api_key_env="OPENAI_API_KEY",
    ),
    "o1-mini": ModelConfig(
        id="o1-mini",
        name="o1 Mini",
        provider=ModelProvider.OPENAI,
        description="Fast reasoning model",
        max_tokens=65536,
        supports_vision=False,
        context_window=128000,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.012,
        api_key_env="OPENAI_API_KEY",
    ),
    
    # Anthropic Models
    "claude-sonnet-4-20250514": ModelConfig(
        id="claude-sonnet-4-20250514",
        name="Claude Sonnet 4",
        provider=ModelProvider.ANTHROPIC,
        description="Latest Claude, excellent for coding",
        max_tokens=8192,
        supports_vision=True,
        context_window=200000,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        api_key_env="ANTHROPIC_API_KEY",
    ),
    "claude-opus-4-20250514": ModelConfig(
        id="claude-opus-4-20250514",
        name="Claude Opus 4",
        provider=ModelProvider.ANTHROPIC,
        description="Most capable Claude model",
        max_tokens=8192,
        supports_vision=True,
        context_window=200000,
        cost_per_1k_input=0.015,
        cost_per_1k_output=0.075,
        api_key_env="ANTHROPIC_API_KEY",
    ),
    "claude-3-5-sonnet-20241022": ModelConfig(
        id="claude-3-5-sonnet-20241022",
        name="Claude 3.5 Sonnet",
        provider=ModelProvider.ANTHROPIC,
        description="Balanced performance and speed",
        max_tokens=8192,
        supports_vision=True,
        context_window=200000,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        api_key_env="ANTHROPIC_API_KEY",
    ),
    "claude-3-5-haiku-20241022": ModelConfig(
        id="claude-3-5-haiku-20241022",
        name="Claude 3.5 Haiku",
        provider=ModelProvider.ANTHROPIC,
        description="Fast and efficient",
        max_tokens=8192,
        supports_vision=True,
        context_window=200000,
        cost_per_1k_input=0.0008,
        cost_per_1k_output=0.004,
        api_key_env="ANTHROPIC_API_KEY",
    ),
    
    # Google Models
    "gemini-2.0-flash": ModelConfig(
        id="gemini-2.0-flash",
        name="Gemini 2.0 Flash",
        provider=ModelProvider.GOOGLE,
        description="Fast multimodal model",
        max_tokens=8192,
        supports_vision=True,
        context_window=1000000,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        api_key_env="GOOGLE_API_KEY",
    ),
    "gemini-1.5-pro": ModelConfig(
        id="gemini-1.5-pro",
        name="Gemini 1.5 Pro",
        provider=ModelProvider.GOOGLE,
        description="Long context window",
        max_tokens=8192,
        supports_vision=True,
        context_window=2000000,
        cost_per_1k_input=0.00125,
        cost_per_1k_output=0.005,
        api_key_env="GOOGLE_API_KEY",
    ),
    
    # Local Models (Ollama)
    "llama3.3": ModelConfig(
        id="llama3.3",
        name="Llama 3.3 70B",
        provider=ModelProvider.OLLAMA,
        description="Open source, runs locally",
        max_tokens=4096,
        supports_vision=False,
        context_window=131072,
        endpoint="http://localhost:11434",
    ),
    "codellama": ModelConfig(
        id="codellama",
        name="Code Llama",
        provider=ModelProvider.OLLAMA,
        description="Specialized for code",
        max_tokens=4096,
        supports_vision=False,
        context_window=16384,
        endpoint="http://localhost:11434",
    ),
    "deepseek-coder-v2": ModelConfig(
        id="deepseek-coder-v2",
        name="DeepSeek Coder V2",
        provider=ModelProvider.OLLAMA,
        description="Excellent code generation",
        max_tokens=4096,
        supports_vision=False,
        context_window=128000,
        endpoint="http://localhost:11434",
    ),
    "qwen2.5-coder": ModelConfig(
        id="qwen2.5-coder",
        name="Qwen 2.5 Coder",
        provider=ModelProvider.OLLAMA,
        description="Strong coding capabilities",
        max_tokens=4096,
        supports_vision=False,
        context_window=131072,
        endpoint="http://localhost:11434",
    ),
}


class ModelSelector:
    """
    Model selector with GUI-like interface.
    Similar to GitHub Copilot's model dropdown.
    
    Usage:
        selector = ModelSelector()
        
        # Show available models
        selector.show()
        
        # Select interactively
        model = selector.select()
        
        # Or set directly
        selector.set_model("gpt-4o")
        
        # Get current model
        current = selector.current
    """
    
    def __init__(
        self,
        default_model: str = "gpt-4o",
        custom_models: Optional[Dict[str, ModelConfig]] = None,
    ):
        """
        Initialize model selector.
        
        Args:
            default_model: Default model ID.
            custom_models: Additional custom models.
        """
        self._models: Dict[str, ModelConfig] = BUILTIN_MODELS.copy()
        
        if custom_models:
            self._models.update(custom_models)
        
        self._current_model_id = default_model
        self._on_change_callbacks: List[Callable[[ModelConfig], None]] = []
    
    @property
    def current(self) -> ModelConfig:
        """Get current selected model."""
        return self._models.get(self._current_model_id, BUILTIN_MODELS["gpt-4o"])
    
    @property
    def current_id(self) -> str:
        """Get current model ID."""
        return self._current_model_id
    
    def set_model(self, model_id: str) -> ModelConfig:
        """
        Set the current model.
        
        Args:
            model_id: Model ID to select.
            
        Returns:
            Selected ModelConfig.
        """
        if model_id not in self._models:
            raise ValueError(f"Unknown model: {model_id}. Use list_models() to see available models.")
        
        self._current_model_id = model_id
        model = self._models[model_id]
        
        # Notify callbacks
        for callback in self._on_change_callbacks:
            callback(model)
        
        return model
    
    def on_change(self, callback: Callable[[ModelConfig], None]) -> None:
        """Register a callback for model changes."""
        self._on_change_callbacks.append(callback)
    
    def add_model(self, config: ModelConfig) -> None:
        """Add a custom model."""
        self._models[config.id] = config
    
    def remove_model(self, model_id: str) -> bool:
        """Remove a model."""
        if model_id in self._models:
            del self._models[model_id]
            return True
        return False
    
    def list_models(
        self,
        provider: Optional[ModelProvider] = None,
        available_only: bool = False,
    ) -> List[ModelConfig]:
        """
        List all models.
        
        Args:
            provider: Filter by provider.
            available_only: Only show models with API keys configured.
            
        Returns:
            List of ModelConfig.
        """
        models = list(self._models.values())
        
        if provider:
            models = [m for m in models if m.provider == provider]
        
        if available_only:
            models = [m for m in models if m.is_available]
        
        return sorted(models, key=lambda m: (m.provider.value, m.name))
    
    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """Get a model by ID."""
        return self._models.get(model_id)
    
    def show(self, show_unavailable: bool = True) -> None:
        """
        Display model selector GUI.
        
        Similar to Copilot's model dropdown.
        """
        from .gui import Colors, c, supports_color
        
        width = 75
        
        print()
        print(c("╔" + "═" * (width - 2) + "╗", Colors.CYAN))
        print(c("║", Colors.CYAN) + c("  🤖 Model Selector", Colors.BOLD, Colors.WHITE) + " " * (width - 23) + c("║", Colors.CYAN))
        print(c("╠" + "═" * (width - 2) + "╣", Colors.CYAN))
        
        # Group by provider
        by_provider: Dict[ModelProvider, List[ModelConfig]] = {}
        for model in self._models.values():
            if model.provider not in by_provider:
                by_provider[model.provider] = []
            by_provider[model.provider].append(model)
        
        for provider in ModelProvider:
            if provider not in by_provider:
                continue
            
            models = sorted(by_provider[provider], key=lambda m: m.name)
            
            # Provider header
            provider_icons = {
                ModelProvider.OPENAI: "🟢",
                ModelProvider.ANTHROPIC: "🟠",
                ModelProvider.GOOGLE: "🔵",
                ModelProvider.AZURE: "☁️",
                ModelProvider.OLLAMA: "🦙",
                ModelProvider.CUSTOM: "⚙️",
            }
            icon = provider_icons.get(provider, "•")
            
            print(c("║", Colors.CYAN) + " " * (width - 2) + c("║", Colors.CYAN))
            print(c("║", Colors.CYAN) + f"  {icon} {c(provider.value.upper(), Colors.BOLD)}" + " " * (width - 8 - len(provider.value)) + c("║", Colors.CYAN))
            print(c("║", Colors.CYAN) + c("  ─" * 35, Colors.DIM) + " " + c("║", Colors.CYAN))
            
            for model in models:
                # Check if selected
                is_selected = model.id == self._current_model_id
                
                # Check availability
                available = model.is_available
                
                if not available and not show_unavailable:
                    continue
                
                # Selection indicator
                if is_selected:
                    indicator = c("● ", Colors.GREEN, Colors.BOLD)
                else:
                    indicator = c("○ ", Colors.DIM)
                
                # Model name
                name = model.name[:20]
                if is_selected:
                    name_str = c(name, Colors.GREEN, Colors.BOLD)
                elif not available:
                    name_str = c(name, Colors.DIM)
                else:
                    name_str = c(name, Colors.WHITE)
                
                # Features
                features = []
                if model.supports_vision:
                    features.append("👁")
                if model.supports_tools:
                    features.append("🔧")
                features_str = " ".join(features) if features else "  "
                
                # Context window
                ctx = f"{model.context_window // 1000}K"
                
                # Availability
                if not available:
                    status = c("(no key)", Colors.RED)
                else:
                    status = ""
                
                line = f"  {indicator}{name_str:<22} {features_str:<6} {ctx:>6} {status}"
                padding = width - 4 - 22 - 8 - 8 - len(status) + (len(name_str) - len(name))
                print(c("║", Colors.CYAN) + f"  {indicator}{name_str}" + " " * (22 - len(name)) + f"{features_str:<6} {ctx:>6} {status}" + " " * max(1, 15 - len(status)) + c("║", Colors.CYAN))
        
        # Legend
        print(c("║", Colors.CYAN) + " " * (width - 2) + c("║", Colors.CYAN))
        print(c("╠" + "═" * (width - 2) + "╣", Colors.CYAN))
        print(c("║", Colors.CYAN) + c("  Legend: 👁 Vision  🔧 Tools  ● Selected", Colors.DIM) + " " * 25 + c("║", Colors.CYAN))
        print(c("║", Colors.CYAN) + c(f"  Current: {self.current.name}", Colors.GREEN) + " " * (width - 14 - len(self.current.name)) + c("║", Colors.CYAN))
        print(c("╚" + "═" * (width - 2) + "╝", Colors.CYAN))
    
    def select(self) -> Optional[ModelConfig]:
        """
        Interactive model selection.
        
        Returns selected model or None if cancelled.
        """
        from .gui import Colors, c
        
        models = self.list_models()
        
        print(c("\n🤖 Select a model:\n", Colors.BOLD))
        
        # Group by provider
        by_provider: Dict[ModelProvider, List[ModelConfig]] = {}
        for model in models:
            if model.provider not in by_provider:
                by_provider[model.provider] = []
            by_provider[model.provider].append(model)
        
        idx = 1
        model_map: Dict[int, ModelConfig] = {}
        
        for provider in ModelProvider:
            if provider not in by_provider:
                continue
            
            provider_models = sorted(by_provider[provider], key=lambda m: m.name)
            print(c(f"  {provider.value.upper()}", Colors.BOLD, Colors.CYAN))
            
            for model in provider_models:
                is_current = model.id == self._current_model_id
                available = model.is_available
                
                current_marker = c(" ◀", Colors.GREEN) if is_current else ""
                unavailable = c(" (no key)", Colors.RED) if not available else ""
                
                if is_current:
                    name_str = c(model.name, Colors.GREEN)
                elif not available:
                    name_str = c(model.name, Colors.DIM)
                else:
                    name_str = model.name
                
                print(f"    {c(str(idx), Colors.CYAN)}) {name_str}{current_marker}{unavailable}")
                print(f"       {c(model.description, Colors.DIM)}")
                
                model_map[idx] = model
                idx += 1
            
            print()
        
        print(f"  {c('0', Colors.CYAN)}) Cancel")
        print()
        
        try:
            choice = input(c("Enter number: ", Colors.YELLOW))
            num = int(choice)
            
            if num == 0:
                print(c("Cancelled.", Colors.DIM))
                return None
            
            if num not in model_map:
                print(c("Invalid choice.", Colors.RED))
                return None
            
            model = model_map[num]
            self.set_model(model.id)
            
            print(c(f"\n✅ Selected: {model.name}", Colors.GREEN))
            return model
            
        except (ValueError, KeyboardInterrupt):
            print(c("\nCancelled.", Colors.DIM))
            return None
    
    def quick_select(self, shortcut: str) -> Optional[ModelConfig]:
        """
        Quick model selection by shortcut.
        
        Shortcuts:
            - "4o" / "gpt4o" -> gpt-4o
            - "4m" / "mini" -> gpt-4o-mini
            - "claude" / "sonnet" -> claude-sonnet-4
            - "opus" -> claude-opus-4
            - "haiku" -> claude-3-5-haiku
            - "gemini" / "flash" -> gemini-2.0-flash
            - "llama" -> llama3.3
            - "o1" -> o1
        """
        shortcuts = {
            "4o": "gpt-4o",
            "gpt4o": "gpt-4o",
            "4m": "gpt-4o-mini",
            "mini": "gpt-4o-mini",
            "turbo": "gpt-4-turbo",
            "o1": "o1",
            "o1m": "o1-mini",
            "claude": "claude-sonnet-4-20250514",
            "sonnet": "claude-sonnet-4-20250514",
            "sonnet4": "claude-sonnet-4-20250514",
            "opus": "claude-opus-4-20250514",
            "opus4": "claude-opus-4-20250514",
            "haiku": "claude-3-5-haiku-20241022",
            "3.5": "claude-3-5-sonnet-20241022",
            "gemini": "gemini-2.0-flash",
            "flash": "gemini-2.0-flash",
            "pro": "gemini-1.5-pro",
            "llama": "llama3.3",
            "codellama": "codellama",
            "deepseek": "deepseek-coder-v2",
            "qwen": "qwen2.5-coder",
        }
        
        model_id = shortcuts.get(shortcut.lower(), shortcut)
        
        if model_id in self._models:
            return self.set_model(model_id)
        
        return None


# Global model selector instance
_global_selector: Optional[ModelSelector] = None


def get_model_selector() -> ModelSelector:
    """Get or create global model selector."""
    global _global_selector
    if _global_selector is None:
        _global_selector = ModelSelector()
    return _global_selector


def set_model(model_id: str) -> ModelConfig:
    """Set the global model."""
    return get_model_selector().set_model(model_id)


def get_model() -> ModelConfig:
    """Get the current global model."""
    return get_model_selector().current


def show_models() -> None:
    """Show model selector GUI."""
    get_model_selector().show()


def select_model() -> Optional[ModelConfig]:
    """Interactive model selection."""
    return get_model_selector().select()
