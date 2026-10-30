import os
import sys
import re
import argparse
from typing import Optional, List, Tuple
from openai import OpenAI

# Add parent directory to sys.path to allow importing from backend
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from backend.app_db import get_user_api_key_model, get_db_connection, _get_sqlite_connection
    from backend.app_logging import get_logger
    logger = get_logger("translate")
except ImportError:
    # Fallback if run directly and path setup fails
    import logging

    logger = logging.getLogger("geniview.translate")
    logger.warning("Could not import backend modules. Database access might fail.")

# Configuration
# Kimi API key (Moonshot AI) - Placeholder, should be provided via environment variable or argument
# However, user mentioned "kimi 2.5 flash", which implies Moonshot AI's API.
# I will assume the user might provide the key or I should look for it in env.
# Based on previous context, user provided other keys but not Kimi key in the prompt.
# I will check if there is an existing Kimi/Moonshot key in the project or ask/assume one.
# For now, I will use a placeholder or try to read from env MOONSHOT_API_KEY.
MOONSHOT_API_KEY = os.environ.get("MOONSHOT_API_KEY", "")
TRANSLATION_MODEL = os.environ.get("MOONSHOT_MODEL", "moonshot-v1-8k")
TRANSLATION_CHUNK_SIZE = int(os.environ.get("MOONSHOT_CHUNK_SIZE", "3500"))

def get_api_key_from_db(username: str = "admin") -> Optional[str]:
    """Retrieve API key from database for a specific user (default: admin)"""
    try:
        # Try to get key for admin or first available user
        api_key, _ = get_user_api_key_model(username)
        if api_key:
            return api_key
            
        # If no admin key, maybe check env again or return None
        return None
    except Exception as e:
        logger.error("Error retrieving API key from DB: %s", e)
        return None

def _protect_code_blocks(content: str) -> Tuple[str, List[str]]:
    blocks: List[str] = []
    def repl(match: re.Match) -> str:
        blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(blocks) - 1}__"
    safe = re.sub(r"```[\s\S]*?```", repl, content)
    return safe, blocks


def _restore_code_blocks(content: str, blocks: List[str]) -> str:
    out = content
    for i, block in enumerate(blocks):
        out = out.replace(f"__CODE_BLOCK_{i}__", block)
    return out


def _split_markdown_sections(content: str) -> List[str]:
    parts = re.split(r"(?m)(^##\s.*$)", content)
    if len(parts) <= 1:
        return [content] if content.strip() else []
    chunks: List[str] = []
    pre = parts[0]
    if pre.strip():
        chunks.append(pre)
    i = 1
    while i < len(parts):
        header = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        chunks.append(f"{header}\n{body}".rstrip())
        i += 2
    return [c for c in chunks if c.strip()]


def _lines_len(lines: List[str]) -> int:
    if not lines:
        return 0
    return sum(len(line) for line in lines) + max(0, len(lines) - 1)


def _split_section_by_size(section: str, max_chars: int) -> List[str]:
    lines = section.splitlines()
    if _lines_len(lines) <= max_chars:
        return [section.strip()]

    header_line = None
    if lines and re.match(r"^##\s", lines[0]):
        header_line = lines[0]
        lines = lines[1:]

    blocks: List[Tuple[bool, List[str]]] = []
    current: List[str] = []
    current_is_table: Optional[bool] = None
    for line in lines:
        is_table = line.strip().startswith("|")
        if current_is_table is None:
            current_is_table = is_table
        if is_table != current_is_table:
            blocks.append((current_is_table, current))
            current = [line]
            current_is_table = is_table
        else:
            current.append(line)
    if current:
        blocks.append((current_is_table or False, current))

    chunks: List[str] = []
    current_lines: List[str] = []
    if header_line:
        current_lines.append(header_line)

    for is_table, block_lines in blocks:
        if not is_table:
            for line in block_lines:
                if _lines_len(current_lines + [line]) > max_chars and current_lines:
                    chunks.append("\n".join(current_lines).rstrip())
                    current_lines = []
                current_lines.append(line)
            continue

        header = block_lines[0] if len(block_lines) >= 1 else ""
        sep = block_lines[1] if len(block_lines) >= 2 else ""
        rows = block_lines[2:] if len(block_lines) > 2 else []

        if _lines_len(current_lines) + len(header) + len(sep) + 2 > max_chars and current_lines:
            chunks.append("\n".join(current_lines).rstrip())
            current_lines = []

        if header:
            current_lines.append(header)
        if sep:
            current_lines.append(sep)

        for row in rows:
            if _lines_len(current_lines + [row]) > max_chars and (header or sep):
                chunks.append("\n".join(current_lines).rstrip())
                current_lines = []
                if header:
                    current_lines.append(header)
                if sep:
                    current_lines.append(sep)
            current_lines.append(row)

    if current_lines:
        chunks.append("\n".join(current_lines).rstrip())

    return [c for c in chunks if c.strip()]


def _translate_chunk(client: OpenAI, chunk: str) -> str:
    completion = client.chat.completions.create(
        model=TRANSLATION_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Translate Chinese technical markdown into English. Keep all markdown structure, tables, and line breaks. Do not omit any content. If text is already English, keep it unchanged. Output only the translated markdown.",
            },
            {"role": "user", "content": chunk},
        ],
        temperature=0.2,
        max_tokens=4096,
    )
    return completion.choices[0].message.content or ""


def translate_file(input_path: str, api_key: Optional[str] = None):
    if not os.path.exists(input_path):
        logger.error("Input file not found: %s", input_path)
        return

    # Determine which API key to use
    key_to_use = api_key
    if not key_to_use:
        key_to_use = os.environ.get("MOONSHOT_API_KEY", "")

    if not key_to_use:
        # Try to get from DB (admin)
        logger.info("No API Key provided. Attempting to retrieve from database (admin user)...")
        key_to_use = get_api_key_from_db("admin")

    if not key_to_use:
        logger.error("No API Key available for translation (checked args, env, and admin DB).")
        return

    # Prepare output path
    dir_name = os.path.dirname(input_path)
    base_name = os.path.basename(input_path)
    output_filename = f"en_{base_name}"
    output_path = os.path.join(dir_name, output_filename)

    logger.info("Reading input file: %s", input_path)
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    logger.info("Initializing Kimi client...")
    client = OpenAI(
        api_key=key_to_use,
        base_url="https://api.moonshot.cn/v1",
    )

    logger.info("Sending translation request to Kimi 2.5 Flash...")
    try:
        safe_content, code_blocks = _protect_code_blocks(content)
        base_sections = _split_markdown_sections(safe_content)
        chunks: List[str] = []
        for section in base_sections:
            chunks.extend(_split_section_by_size(section, TRANSLATION_CHUNK_SIZE))
        translated_parts: List[str] = []
        total = max(1, len(chunks))
        for i, chunk in enumerate(chunks, start=1):
            logger.info("Translating section %d/%d...", i, total)
            translated = _translate_chunk(client, chunk)
            translated_parts.append(translated if translated.strip() else chunk)
        translated_content = "\n\n".join([p.strip() for p in translated_parts if p.strip()])
        translated_content = _restore_code_blocks(translated_content, code_blocks)

        logger.info("Writing translated content to: %s", output_path)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(translated_content)

        logger.info("Translation complete.")

    except Exception as e:
        logger.error("Translation failed: %s", e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Translate markdown file using Kimi 2.5 Flash")
    parser.add_argument("input_path", help="Path to the input markdown file")
    parser.add_argument("--api_key", help="Kimi API Key", default=MOONSHOT_API_KEY)
    
    args = parser.parse_args()
    
    api_key = args.api_key
    
    if not api_key:
        logger.info("No API Key provided in args or env. Attempting to retrieve from database (admin user)...")
        # Ensure we are in the project root context for DB access if possible
        # (Assuming script is run from project root or backend folder)
        try:
            db_key = get_api_key_from_db("admin")
            if db_key:
                logger.info("Found API key for user 'admin' in database.")
                api_key = db_key
        except Exception as e:
            logger.error("Failed to retrieve key from DB: %s", e)

    if not api_key:
        logger.error("API Key is required. Set MOONSHOT_API_KEY env var, pass --api_key, or configure 'admin' user with key in DB.")
        sys.exit(1)
        
    translate_file(args.input_path, api_key)
