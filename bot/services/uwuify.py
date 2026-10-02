from __future__ import annotations
import re
import random

_URL = re.compile(r'https?://\S+|<@!?\d+>|<#\d+>|<@&\d+>|`[^`]*`')
_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

class UwuifyService:
    """Real message transformer used by the optional per-member UwU mode."""
    def __init__(self, cache):
        self.cache = cache
        self._local: dict[tuple[int, int], bool] = {}

    @staticmethod
    def _transform_word(word: str, rng: random.Random) -> str:
        low = word.lower()
        # Keep short/common words readable while still sounding strongly UwU.
        out = word
        out = re.sub(r'(?i)r', 'w', out)
        out = re.sub(r'(?i)l', 'w', out)
        out = re.sub(r'(?i)ove', 'owe', out)
        out = re.sub(r'(?i)er\b', 'ew', out)
        out = re.sub(r'(?i)or\b', 'ow', out)
        out = re.sub(r'(?i)th', lambda m: 'th' if len(word) <= 3 else 'th', out)
        # Stutter mostly on the first consonant/vowel, with bounded intensity.
        if len(low) >= 3 and rng.random() < 0.34 and word[0].isalpha():
            first = out[0]
            if first.lower() not in 'aeiou':
                out = f'{first}-{first}-{out}'
            elif rng.random() < 0.45:
                out = f'{first}-{first}-{out}'
        # Stretch a vowel in a controlled way.
        if len(out) >= 4 and rng.random() < 0.28:
            vowels = [i for i, c in enumerate(out) if c.lower() in 'aeiou']
            if vowels:
                i = rng.choice(vowels)
                out = out[:i] + out[i] * rng.randint(3, 5) + out[i + 1:]
        return out

    @classmethod
    def transform(cls, text: str, seed: int | None = None, intensity: str = 'chaotic') -> str:
        if not text or not text.strip():
            return text
        rng = random.Random(seed)
        protected: list[str] = []
        def stash(match: re.Match) -> str:
            protected.append(match.group(0))
            return f'\x00{len(protected)-1}\x00'
        safe = _URL.sub(stash, text)
        safe = _WORD.sub(lambda m: cls._transform_word(m.group(0), rng), safe)
        if intensity == 'chaotic':
            if rng.random() < 0.55:
                safe = safe.rstrip() + rng.choice([' >w<', ' ;w;', ' uwu~', ' >_<'])
            safe = re.sub(r'!{2,}', '!!', safe)
            safe = re.sub(r'\?{2,}', '??', safe)
        for i, value in enumerate(protected):
            safe = safe.replace(f'\x00{i}\x00', value)
        return safe[:1990]

    async def is_enabled(self, guild_id: int, user_id: int) -> bool:
        key = f'uwuify:{guild_id}:{user_id}'
        cached = self._local.get((guild_id, user_id))
        if cached is not None:
            return cached
        value = await self.cache.client.get(key)
        enabled = value == '1'
        self._local[(guild_id, user_id)] = enabled
        return enabled

    async def set_enabled(self, guild_id: int, user_id: int, enabled: bool) -> None:
        key = f'uwuify:{guild_id}:{user_id}'
        if enabled:
            await self.cache.client.set(key, '1')
        else:
            await self.cache.delete(key)
        self._local[(guild_id, user_id)] = enabled

    async def transform_message(self, guild_id: int, user_id: int, content: str) -> str | None:
        if not await self.is_enabled(guild_id, user_id):
            return None
        return self.transform(content, seed=random.randrange(1 << 30))
