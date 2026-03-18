"""Tests for LangGraphStreamingManager secure filename generation and tool-end handling."""

import re
from typing import Any, Optional, cast, override

import pytest
from langchain_core.messages import ToolMessage
from langchain_core.runnables.schema import StandardStreamEvent

from language_model_gateway.gateway.converters.streaming_manager import (
    LangGraphStreamingManager,
)
from language_model_gateway.gateway.file_managers.file_manager import FileManager
from language_model_gateway.gateway.file_managers.file_manager_factory import (
    FileManagerFactory,
)
from language_model_gateway.gateway.schema.openai.completions import ChatRequest
from language_model_gateway.gateway.structures.openai.request.chat_completion_api_request_wrapper import (
    ChatCompletionApiRequestWrapper,
)
from language_model_gateway.gateway.utilities.token_reducer.token_reducer import (
    TokenReducer,
)
from tests.common import TestLanguageModelGatewayEnvironmentVariables


# ─────────────────────────────────────────────────────────────────────────────
# Stubs / helpers
# ─────────────────────────────────────────────────────────────────────────────


class MockTokenReducer(TokenReducer):
    """TokenReducer that avoids network I/O by skipping tiktoken initialisation."""

    def __init__(self) -> None:
        # Do NOT call super().__init__() – it downloads tiktoken vocab files.
        pass

    @override
    def count_tokens(self, text: str | None) -> int:
        # Simple character-based approximation; accuracy is irrelevant for these tests.
        return len(text) // 4 if text else 0

    @override
    def reduce_tokens(
        self,
        text: str,
        max_tokens: int,
        preserve_start: Optional[int] = None,
    ) -> str:
        return text


class MockFileManager(FileManager):
    """In-memory file manager that records all save calls without touching disk."""

    def __init__(self, *, return_path: Optional[str] = "/tmp/test_output.txt") -> None:
        self.saved_calls: list[dict[str, Any]] = []
        self._return_path = return_path

    @override
    async def save_file_async(
        self,
        *,
        file_data: bytes,
        folder: str,
        filename: str,
        content_type: str,
    ) -> Optional[str]:
        self.saved_calls.append(
            {
                "file_data": file_data,
                "folder": folder,
                "filename": filename,
                "content_type": content_type,
            }
        )
        return self._return_path

    @override
    def get_full_path(self, *, filename: str, folder: str) -> str:
        return f"{folder}/{filename}"


class MockFileManagerFactory(FileManagerFactory):
    """FileManagerFactory that always returns a pre-created MockFileManager."""

    def __init__(self, *, file_manager: MockFileManager) -> None:
        self._file_manager = file_manager
        # Intentionally skip super().__init__() – we don't need AwsClientFactory here.

    @override
    def get_file_manager(self, *, folder: str) -> FileManager:
        return self._file_manager


class ConfigurableEnvironmentVariables(TestLanguageModelGatewayEnvironmentVariables):
    """Environment variables with an overridable maximum_inline_tool_output_size."""

    def __init__(self, *, maximum_inline_tool_output_size: int = 100) -> None:
        self._maximum_inline_tool_output_size = maximum_inline_tool_output_size

    @override
    @property
    def maximum_inline_tool_output_size(self) -> int:
        return self._maximum_inline_tool_output_size


def _make_streaming_manager(
    *,
    file_manager: Optional[MockFileManager] = None,
    maximum_inline_tool_output_size: int = 100,
) -> tuple[LangGraphStreamingManager, MockFileManager]:
    if file_manager is None:
        file_manager = MockFileManager()
    manager = LangGraphStreamingManager(
        token_reducer=MockTokenReducer(),
        file_manager_factory=MockFileManagerFactory(file_manager=file_manager),
        environment_variables=ConfigurableEnvironmentVariables(
            maximum_inline_tool_output_size=maximum_inline_tool_output_size
        ),
    )
    return manager, file_manager


def _make_chat_request_wrapper() -> ChatCompletionApiRequestWrapper:
    chat_request = ChatRequest(
        messages=[{"role": "user", "content": "hello"}],
        model="test-model",
    )
    return ChatCompletionApiRequestWrapper(chat_request=chat_request)


def _make_tool_end_event(*, tool_name: str, content: str) -> StandardStreamEvent:
    tool_message = ToolMessage(
        content=content,
        tool_call_id="call_123",
        name=tool_name,
    )
    return cast(
        StandardStreamEvent,
        {
            "event": "on_tool_end",
            "name": tool_name,
            "data": {
                "output": tool_message,
                "input": {"query": "test"},
            },
        },
    )


async def _collect_chunks(
    manager: LangGraphStreamingManager,
    event: StandardStreamEvent,
    *,
    user_id: Optional[str] = None,
) -> list[str]:
    """Drain the _handle_on_tool_end async generator and return all yielded chunks."""
    chat_request_wrapper = _make_chat_request_wrapper()
    chunks: list[str] = []
    async for chunk in manager._handle_on_tool_end(
        event=event,
        chat_request_wrapper=chat_request_wrapper,
        request_id="test-request-id",
        tool_start_times={},
        user_id=user_id,
    ):
        chunks.append(chunk)
    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# generate_secure_filename tests
# ─────────────────────────────────────────────────────────────────────────────


class TestGenerateSecureFilename:
    def test_ends_with_txt(self) -> None:
        filename = LangGraphStreamingManager.generate_secure_filename(
            tool_name="my_tool", user_id=None
        )
        assert filename.endswith(".txt")

    def test_contains_sanitized_tool_name(self) -> None:
        filename = LangGraphStreamingManager.generate_secure_filename(
            tool_name="my_tool", user_id=None
        )
        assert "my_tool" in filename

    def test_no_path_separators(self) -> None:
        filename = LangGraphStreamingManager.generate_secure_filename(
            tool_name="path/traversal\\attack", user_id=None
        )
        assert "/" not in filename
        assert "\\" not in filename

    def test_special_chars_replaced(self) -> None:
        """Characters outside [A-Za-z0-9._-] must be replaced so the filename is filesystem-safe."""
        filename = LangGraphStreamingManager.generate_secure_filename(
            tool_name="tool name:with spaces?and:colons!", user_id=None
        )
        name_without_ext = filename[:-4]  # strip ".txt"
        assert re.match(
            r"^[A-Za-z0-9._-]+$", name_without_ext
        ), f"Filename '{name_without_ext}' contains invalid characters"

    def test_none_tool_name_uses_unknown(self) -> None:
        filename = LangGraphStreamingManager.generate_secure_filename(
            tool_name=None, user_id=None
        )
        assert filename.startswith("unknown")

    def test_empty_tool_name_uses_unknown(self) -> None:
        filename = LangGraphStreamingManager.generate_secure_filename(
            tool_name="", user_id=None
        )
        assert filename.startswith("unknown")

    def test_long_tool_name_truncated_to_50_chars(self) -> None:
        long_name = "a" * 200
        filename = LangGraphStreamingManager.generate_secure_filename(
            tool_name=long_name, user_id=None
        )
        # The safe_tool_name component is capped at 50 characters; verify it.
        name_without_ext = filename[:-4]  # e.g. "aaa...(50 a's)_<timestamp>_<token>"
        tool_name_part = name_without_ext.split("_")[0]
        assert len(tool_name_part) <= 50

    def test_uniqueness(self) -> None:
        """Each call produces a different filename thanks to the random token."""
        filenames = {
            LangGraphStreamingManager.generate_secure_filename(
                tool_name="my_tool", user_id="user123"
            )
            for _ in range(10)
        }
        # With 128-bit random tokens the probability of any collision is negligible,
        # so all 10 filenames should be distinct.
        assert len(filenames) == 10

    def test_user_id_not_embedded_in_filename(self) -> None:
        """User ID must not appear in the filename to prevent cross-file linkability."""
        user_id = "sensitive-user-12345"
        filename = LangGraphStreamingManager.generate_secure_filename(
            tool_name="my_tool", user_id=user_id
        )
        assert user_id not in filename

    def test_unicode_tool_name_sanitized(self) -> None:
        filename = LangGraphStreamingManager.generate_secure_filename(
            tool_name="tool_名前_name", user_id=None
        )
        name_without_ext = filename[:-4]
        assert re.match(
            r"^[A-Za-z0-9._-]+$", name_without_ext
        ), f"Filename '{name_without_ext}' contains non-safe characters"


# ─────────────────────────────────────────────────────────────────────────────
# _handle_on_tool_end tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHandleOnToolEnd:
    @pytest.fixture(autouse=True)
    def set_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RETURN_RAW_TOOL_OUTPUT", "1")
        monkeypatch.setenv("IMAGE_GENERATION_PATH", "/tmp/tool_outputs")
        monkeypatch.setenv("IMAGE_GENERATION_URL", "http://localhost/outputs")

    async def test_large_output_saves_to_file(self) -> None:
        """When output exceeds maximum_inline_tool_output_size, save_file_async is called."""
        file_manager = MockFileManager(return_path="/tmp/tool_outputs/test.txt")
        manager, _ = _make_streaming_manager(
            file_manager=file_manager, maximum_inline_tool_output_size=10
        )
        large_content = "x" * 1000  # well above the 10-char threshold
        event = _make_tool_end_event(tool_name="my_tool", content=large_content)

        await _collect_chunks(manager, event, user_id="user_42")

        assert len(file_manager.saved_calls) == 1

    async def test_large_output_filename_is_secure(self) -> None:
        """The filename used for oversized output must pass the secure format rules."""
        file_manager = MockFileManager(return_path="/tmp/tool_outputs/test.txt")
        manager, _ = _make_streaming_manager(
            file_manager=file_manager, maximum_inline_tool_output_size=10
        )
        event = _make_tool_end_event(tool_name="my_tool", content="x" * 1000)

        await _collect_chunks(manager, event, user_id="user_42")

        assert len(file_manager.saved_calls) == 1
        filename: str = file_manager.saved_calls[0]["filename"]

        assert filename.endswith(".txt")
        assert "my_tool" in filename
        assert "/" not in filename
        assert "\\" not in filename
        name_without_ext = filename[:-4]
        assert re.match(
            r"^[A-Za-z0-9._-]+$", name_without_ext
        ), f"Filename '{name_without_ext}' contains invalid characters"

    async def test_small_output_does_not_save_to_file(self) -> None:
        """When output is within maximum_inline_tool_output_size, no file should be written."""
        file_manager = MockFileManager()
        manager, _ = _make_streaming_manager(
            file_manager=file_manager, maximum_inline_tool_output_size=10_000
        )
        event = _make_tool_end_event(tool_name="my_tool", content="hello")

        await _collect_chunks(manager, event)

        assert len(file_manager.saved_calls) == 0

    async def test_response_contains_file_url_when_saved(self) -> None:
        """When a file is saved, the streamed response should include a download URL."""
        file_manager = MockFileManager(return_path="/tmp/tool_outputs/test_file.txt")
        manager, _ = _make_streaming_manager(
            file_manager=file_manager, maximum_inline_tool_output_size=10
        )
        event = _make_tool_end_event(tool_name="my_tool", content="x" * 1000)

        chunks = await _collect_chunks(manager, event, user_id="user_42")

        combined = "".join(chunks)
        assert "http://localhost/outputs" in combined

    async def test_tool_name_with_special_chars_sanitized_in_saved_filename(
        self,
    ) -> None:
        """Special characters in the tool name are removed from the saved filename."""
        file_manager = MockFileManager(return_path="/tmp/out.txt")
        manager, _ = _make_streaming_manager(
            file_manager=file_manager, maximum_inline_tool_output_size=10
        )
        event = _make_tool_end_event(
            tool_name="tool name:with spaces/and/slashes", content="y" * 500
        )

        await _collect_chunks(manager, event)

        assert len(file_manager.saved_calls) == 1
        filename = file_manager.saved_calls[0]["filename"]
        assert "/" not in filename
        assert "\\" not in filename
        name_without_ext = filename[:-4]
        assert re.match(r"^[A-Za-z0-9._-]+$", name_without_ext)

    async def test_file_content_matches_tool_output(self) -> None:
        """The bytes written to disk must match the original tool output content."""
        file_manager = MockFileManager(return_path="/tmp/out.txt")
        manager, _ = _make_streaming_manager(
            file_manager=file_manager, maximum_inline_tool_output_size=10
        )
        content = "detailed tool output " * 100
        event = _make_tool_end_event(tool_name="my_tool", content=content)

        await _collect_chunks(manager, event)

        assert len(file_manager.saved_calls) == 1
        saved_data: bytes = file_manager.saved_calls[0]["file_data"]
        # The saved bytes must contain the original content string.
        assert content.encode("utf-8") in saved_data

    async def test_no_image_generation_path_does_not_save(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When IMAGE_GENERATION_PATH is unset, no file should be saved."""
        monkeypatch.delenv("IMAGE_GENERATION_PATH", raising=False)

        file_manager = MockFileManager()
        manager, _ = _make_streaming_manager(
            file_manager=file_manager, maximum_inline_tool_output_size=10
        )
        event = _make_tool_end_event(tool_name="my_tool", content="x" * 1000)

        await _collect_chunks(manager, event)

        assert len(file_manager.saved_calls) == 0

    async def test_each_call_uses_unique_filename(self) -> None:
        """Consecutive calls for the same tool must produce distinct filenames."""
        file_manager = MockFileManager(return_path="/tmp/out.txt")
        manager, _ = _make_streaming_manager(
            file_manager=file_manager, maximum_inline_tool_output_size=10
        )
        event = _make_tool_end_event(tool_name="my_tool", content="x" * 1000)

        await _collect_chunks(manager, event)
        await _collect_chunks(manager, event)

        assert len(file_manager.saved_calls) == 2
        filename_1 = file_manager.saved_calls[0]["filename"]
        filename_2 = file_manager.saved_calls[1]["filename"]
        assert filename_1 != filename_2

    async def test_env_variable_for_output_path_is_used_as_folder(self) -> None:
        """The folder passed to save_file_async must equal IMAGE_GENERATION_PATH."""
        expected_folder = "/tmp/tool_outputs"
        file_manager = MockFileManager(return_path=f"{expected_folder}/test.txt")
        manager, _ = _make_streaming_manager(
            file_manager=file_manager, maximum_inline_tool_output_size=10
        )
        event = _make_tool_end_event(tool_name="my_tool", content="x" * 1000)

        await _collect_chunks(manager, event)

        assert len(file_manager.saved_calls) == 1
        assert file_manager.saved_calls[0]["folder"] == expected_folder

    async def test_return_raw_tool_output_off_does_not_save(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When RETURN_RAW_TOOL_OUTPUT is not set to 1, no file should be written."""
        monkeypatch.setenv("RETURN_RAW_TOOL_OUTPUT", "0")

        file_manager = MockFileManager()
        manager, _ = _make_streaming_manager(
            file_manager=file_manager, maximum_inline_tool_output_size=10
        )
        event = _make_tool_end_event(tool_name="my_tool", content="x" * 1000)

        await _collect_chunks(manager, event)

        assert len(file_manager.saved_calls) == 0

    async def test_os_env_image_generation_path_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Changing IMAGE_GENERATION_PATH is reflected in the folder used for saving."""
        monkeypatch.setenv("IMAGE_GENERATION_PATH", "/custom/path")
        file_manager = MockFileManager(return_path="/custom/path/test.txt")
        manager, _ = _make_streaming_manager(
            file_manager=file_manager, maximum_inline_tool_output_size=10
        )
        event = _make_tool_end_event(tool_name="my_tool", content="x" * 1000)

        await _collect_chunks(manager, event)

        assert len(file_manager.saved_calls) == 1
        assert file_manager.saved_calls[0]["folder"] == "/custom/path"
