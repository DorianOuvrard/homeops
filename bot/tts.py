import logging
import re
import subprocess
import tempfile
from pathlib import Path

import httpx

from bot.config import BotConfig

logger = logging.getLogger(__name__)

_ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech"


def _mp3_to_ogg_opus(mp3_data: bytes) -> bytes | None:
    """Convert MP3 bytes to OGG/OPUS for proper Telegram voice rendering."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mp3_path = Path(tmpdir) / "input.mp3"
        ogg_path = Path(tmpdir) / "output.ogg"
        mp3_path.write_bytes(mp3_data)

        result = subprocess.run(
            ["ffmpeg", "-i", str(mp3_path), "-c:a", "libopus", "-b:a", "64k", str(ogg_path)],
            capture_output=True,
        )
        if result.returncode != 0:
            logger.warning("ffmpeg MP3→OGG failed: %s", result.stderr[:200])
            return None

        return ogg_path.read_bytes()


def _clean_for_speech(text: str) -> str:
    """Strip URLs and markdown that sound awkward when read aloud."""
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[*_`#\[\]]", "", text)  # markdown formatting
    text = re.sub(r"\(\s*\)", "", text)  # empty parens left after URL removal
    text = re.sub(r"  +", " ", text)
    text = re.sub(r" *\n{2,}", "\n", text)
    return text.strip()


async def text_to_speech(text: str, config: BotConfig) -> bytes | None:
    """Convert text to speech via ElevenLabs. Returns OGG/OPUS bytes or None on failure."""
    if not config.elevenlabs_api_key:
        return None

    speech_text = _clean_for_speech(text)
    if not speech_text:
        return None

    url = f"{_ELEVENLABS_TTS_URL}/{config.elevenlabs_voice_id}"
    headers = {"xi-api-key": config.elevenlabs_api_key, "Content-Type": "application/json"}
    payload = {"text": speech_text, "model_id": "eleven_multilingual_v2"}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                return _mp3_to_ogg_opus(resp.content) or resp.content
            logger.warning("ElevenLabs returned %d: %s", resp.status_code, resp.text[:200])
        except httpx.HTTPError as exc:
            logger.warning("ElevenLabs request failed: %s", exc)

    return None
