from pathlib import Path
from typing import Dict, Tuple


class PromptLoader:
    def __init__(self):
        self._prompts_dir = Path(__file__).parent
        self._cache: Dict[str, Tuple[str, str]] = {}

    def load(self, prompt_name: str) -> Tuple[str, str]:
        if prompt_name in self._cache:
            return self._cache[prompt_name]

        file_path = self._prompts_dir / f"{prompt_name}.md"

        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        result = self._parse(content)
        self._cache[prompt_name] = result
        return result

    def _parse(self, content: str) -> Tuple[str, str]:
        system_prompt = ""
        user_prompt = ""
        current_section = None

        for line in content.split("\n"):
            stripped = line.strip()
            if stripped == "## System Prompt":
                current_section = "system"
            elif stripped == "## User Prompt":
                current_section = "user"
            elif stripped.startswith("#"):
                current_section = None
            elif current_section == "system":
                system_prompt += line + "\n"
            elif current_section == "user":
                user_prompt += line + "\n"

        return system_prompt.strip(), user_prompt.strip()


_loader = PromptLoader()


def get_prompt(prompt_name: str) -> Tuple[str, str]:
    return _loader.load(prompt_name)
