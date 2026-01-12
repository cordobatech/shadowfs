"""
Tests for the models module - Model selector like GitHub Copilot.
"""

import os
import pytest
from shadowfs.models import (
    ModelConfig,
    ModelProvider,
    ModelSelector,
    BUILTIN_MODELS,
    get_model_selector,
    set_model,
    get_model,
)


class TestModelConfig:
    """Tests for ModelConfig class."""
    
    def test_create_model_config(self):
        """Test creating a model config."""
        config = ModelConfig(
            id="test-model",
            name="Test Model",
            provider=ModelProvider.OPENAI,
            description="A test model",
            max_tokens=4096,
            context_window=8192,
        )
        
        assert config.id == "test-model"
        assert config.name == "Test Model"
        assert config.provider == ModelProvider.OPENAI
        assert config.max_tokens == 4096
    
    def test_display_name(self):
        """Test display name property."""
        config = ModelConfig(
            id="gpt-4",
            name="GPT-4",
            provider=ModelProvider.OPENAI,
        )
        
        assert config.display_name == "GPT-4 (openai)"
    
    def test_is_available_no_key_required(self):
        """Test availability when no API key required."""
        config = ModelConfig(
            id="llama",
            name="Llama",
            provider=ModelProvider.OLLAMA,
            api_key_env="",  # No key required
        )
        
        assert config.is_available is True
    
    def test_is_available_key_not_set(self, monkeypatch):
        """Test availability when API key not set."""
        monkeypatch.delenv("TEST_API_KEY", raising=False)
        
        config = ModelConfig(
            id="test",
            name="Test",
            provider=ModelProvider.CUSTOM,
            api_key_env="TEST_API_KEY",
        )
        
        assert config.is_available is False
    
    def test_is_available_key_set(self, monkeypatch):
        """Test availability when API key is set."""
        monkeypatch.setenv("TEST_API_KEY", "secret")
        
        config = ModelConfig(
            id="test",
            name="Test",
            provider=ModelProvider.CUSTOM,
            api_key_env="TEST_API_KEY",
        )
        
        assert config.is_available is True
    
    def test_to_dict(self):
        """Test converting to dict."""
        config = ModelConfig(
            id="gpt-4",
            name="GPT-4",
            provider=ModelProvider.OPENAI,
            supports_vision=True,
        )
        
        data = config.to_dict()
        
        assert data["id"] == "gpt-4"
        assert data["name"] == "GPT-4"
        assert data["provider"] == "openai"
        assert data["supports_vision"] is True


class TestBuiltinModels:
    """Tests for builtin models."""
    
    def test_builtin_models_exist(self):
        """Test that builtin models are defined."""
        assert len(BUILTIN_MODELS) > 0
    
    def test_gpt4o_exists(self):
        """Test GPT-4o is in builtin models."""
        assert "gpt-4o" in BUILTIN_MODELS
        model = BUILTIN_MODELS["gpt-4o"]
        assert model.name == "GPT-4o"
        assert model.provider == ModelProvider.OPENAI
    
    def test_claude_exists(self):
        """Test Claude models are in builtin models."""
        assert "claude-sonnet-4-20250514" in BUILTIN_MODELS
        model = BUILTIN_MODELS["claude-sonnet-4-20250514"]
        assert model.provider == ModelProvider.ANTHROPIC
    
    def test_ollama_models_exist(self):
        """Test Ollama models are in builtin models."""
        assert "llama3.3" in BUILTIN_MODELS
        model = BUILTIN_MODELS["llama3.3"]
        assert model.provider == ModelProvider.OLLAMA
        assert model.endpoint == "http://localhost:11434"


class TestModelSelector:
    """Tests for ModelSelector class."""
    
    def test_create_selector(self):
        """Test creating a model selector."""
        selector = ModelSelector()
        
        assert selector.current is not None
        assert selector.current_id == "gpt-4o"
    
    def test_create_selector_custom_default(self):
        """Test creating selector with custom default."""
        selector = ModelSelector(default_model="claude-sonnet-4-20250514")
        
        assert selector.current_id == "claude-sonnet-4-20250514"
    
    def test_set_model(self):
        """Test setting the current model."""
        selector = ModelSelector()
        
        model = selector.set_model("gpt-4o-mini")
        
        assert model.id == "gpt-4o-mini"
        assert selector.current_id == "gpt-4o-mini"
    
    def test_set_model_invalid(self):
        """Test setting an invalid model."""
        selector = ModelSelector()
        
        with pytest.raises(ValueError):
            selector.set_model("nonexistent-model")
    
    def test_list_models(self):
        """Test listing all models."""
        selector = ModelSelector()
        
        models = selector.list_models()
        
        assert len(models) > 0
        assert any(m.id == "gpt-4o" for m in models)
    
    def test_list_models_by_provider(self):
        """Test listing models by provider."""
        selector = ModelSelector()
        
        openai_models = selector.list_models(provider=ModelProvider.OPENAI)
        
        assert len(openai_models) > 0
        assert all(m.provider == ModelProvider.OPENAI for m in openai_models)
    
    def test_get_model(self):
        """Test getting a model by ID."""
        selector = ModelSelector()
        
        model = selector.get_model("gpt-4o")
        
        assert model is not None
        assert model.id == "gpt-4o"
    
    def test_get_model_none(self):
        """Test getting nonexistent model."""
        selector = ModelSelector()
        
        model = selector.get_model("nonexistent")
        
        assert model is None
    
    def test_add_custom_model(self):
        """Test adding a custom model."""
        selector = ModelSelector()
        
        custom = ModelConfig(
            id="my-model",
            name="My Custom Model",
            provider=ModelProvider.CUSTOM,
        )
        selector.add_model(custom)
        
        assert selector.get_model("my-model") is not None
    
    def test_remove_model(self):
        """Test removing a model."""
        selector = ModelSelector()
        
        custom = ModelConfig(
            id="temp-model",
            name="Temp",
            provider=ModelProvider.CUSTOM,
        )
        selector.add_model(custom)
        
        result = selector.remove_model("temp-model")
        
        assert result is True
        assert selector.get_model("temp-model") is None
    
    def test_on_change_callback(self):
        """Test model change callback."""
        selector = ModelSelector()
        changed_models = []
        
        selector.on_change(lambda m: changed_models.append(m))
        selector.set_model("gpt-4o-mini")
        
        assert len(changed_models) == 1
        assert changed_models[0].id == "gpt-4o-mini"
    
    def test_quick_select(self):
        """Test quick select shortcuts."""
        selector = ModelSelector()
        
        # Test various shortcuts
        model = selector.quick_select("4o")
        assert model.id == "gpt-4o"
        
        model = selector.quick_select("mini")
        assert model.id == "gpt-4o-mini"
        
        model = selector.quick_select("claude")
        assert model.id == "claude-sonnet-4-20250514"
        
        model = selector.quick_select("opus")
        assert model.id == "claude-opus-4-20250514"
        
        model = selector.quick_select("llama")
        assert model.id == "llama3.3"
    
    def test_quick_select_invalid(self):
        """Test quick select with invalid shortcut."""
        selector = ModelSelector()
        
        model = selector.quick_select("invalid-shortcut-xyz")
        
        assert model is None


class TestGlobalFunctions:
    """Tests for global model functions."""
    
    def test_get_model_selector(self):
        """Test getting global selector."""
        selector1 = get_model_selector()
        selector2 = get_model_selector()
        
        assert selector1 is selector2
    
    def test_set_and_get_model(self):
        """Test global set and get model."""
        set_model("gpt-4o-mini")
        model = get_model()
        
        assert model.id == "gpt-4o-mini"
