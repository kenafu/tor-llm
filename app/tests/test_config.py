from tor_llm_tool.settings import AppConfig


def test_default_config_values():
    config = AppConfig()

    assert config.llm.provider == "lmstudio"
    assert config.llm.base_url == "http://127.0.0.1:1234/v1"
    assert config.ocr.provider == "rapidocr"
    assert config.request.send_image is True
    assert config.request.send_context is True
    assert config.task_presets[0].task_id == "explain-region"
    assert config.request.send_window_title is True


def test_config_accepts_aliases():
    config = AppConfig.model_validate(
        {
            "llm": {"baseUrl": "http://127.0.0.1:1234/v1", "timeoutSec": 30},
            "request": {"sendImage": False, "sendContext": True},
        }
    )

    assert config.llm.timeout_sec == 30
    assert config.request.send_image is False
    assert config.request.send_context is True


def test_config_accepts_task_preset_alias():
    config = AppConfig.model_validate(
        {"taskPresets": [{"id": "custom-task", "label": "Custom", "enabled": False}]}
    )

    assert config.task_presets[0].task_id == "custom-task"
    assert config.task_presets[0].enabled is False
