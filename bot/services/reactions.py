from __future__ import annotations
import asyncio
import logging
import os
import time
import random
from typing import Optional
import aiohttp

log = logging.getLogger('bot.reactions')

class ReactionGifService:
    """Fast reaction GIF resolver with TTL caching and per-action coalescing."""
    GIPHY_URL = 'https://api.giphy.com/v1/gifs/search'
    TENOR_URL = 'https://tenor.googleapis.com/v2/search'
    OTAKU_GIFS_URL = 'https://api.otakugifs.xyz/gif'
    ALIASES = {
        'highfive': 'wave', 'pat': 'pat', 'bonk': 'punch', 'poke': 'poke',
        'hug': 'hug',
        'wave': 'wave', 'dance': 'dance', 'smile': 'smile', 'happy': 'smile',
        'cry': 'cry', 'sleep': 'sleep', 'shrug': 'shrug', 'boop': 'poke',
        'punch': 'punch', 'slap': 'slap', 'bite': 'bite', 'tickle': 'tickle',
        'hold': 'hug', 'pout': 'pout', 'blush': 'blush', 'uwu': 'smile',
    }
    def __init__(self, giphy_api_key: Optional[str] = None, tenor_api_key: Optional[str] = None):
        self.giphy_api_key = giphy_api_key or os.getenv('GIPHY_API_KEY')
        self.tenor_api_key = tenor_api_key or os.getenv('TENOR_API_KEY')
        self._session: Optional[aiohttp.ClientSession] = None
        self._locks: dict[str, asyncio.Lock] = {}
        self._cache: dict[str, tuple[float, Optional[str]]] = {}
        self._inflight: dict[str, asyncio.Task] = {}
        self._cache_ttl = 900.0
        self._failure_ttl = 8.0
        self._max_cache = 256

    async def start(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3.0))

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
        self._cache.clear()
        self._locks.clear()

    async def _from_giphy(self, action: str) -> Optional[str]:
        if not self.giphy_api_key:
            return None
        async with self._session.get(self.GIPHY_URL, params={
            'api_key': self.giphy_api_key,
            'q': f'anime {action} reaction',
            'limit': 10,
            'rating': 'pg',
        }) as response:
            if response.status != 200:
                return None
            data = await response.json()
            results = [
                item.get('images', {}).get('original', {}).get('url')
                for item in data.get('data', [])
                if item.get('images', {}).get('original', {}).get('url')
            ]
            return random.choice(results) if results else None

    async def _from_tenor(self, action: str) -> Optional[str]:
        if not self.tenor_api_key:
            return None
        async with self._session.get(self.TENOR_URL, params={
            'key': self.tenor_api_key,
            'q': f'anime {action} reaction',
            'limit': 10,
            'media_filter': 'gif',
            'contentfilter': 'low',
        }) as response:
            if response.status != 200:
                return None
            data = await response.json()
            results = [
                result.get('media_formats', {}).get('gif', {}).get('url')
                for result in data.get('results', [])
                if result.get('media_formats', {}).get('gif', {}).get('url')
            ]
            return random.choice(results) if results else None

    async def _from_otakugifs(self, action: str) -> Optional[str]:
        async with self._session.get(self.OTAKU_GIFS_URL, params={'reaction': action}) as response:
            if response.status != 200:
                return None
            data = await response.json()
            return data.get('url')

    async def get(self, action: str) -> Optional[str]:
        action = self.ALIASES.get(action, action)
        now = time.monotonic()
        # Positive GIFs are deliberately not cached: every action invocation
        # should be able to receive a different result.
        cached = self._cache.get(action)
        if cached and not cached[1] and now - cached[0] < self._failure_ttl:
            return None
        lock = self._locks.setdefault(action, asyncio.Lock())
        async with lock:
            now = time.monotonic()
            cached = self._cache.get(action)
            if cached and now - cached[0] < (self._cache_ttl if cached[1] else self._failure_ttl):
                return cached[1]
            await self.start()
            url: Optional[str] = None
            providers = (
                ('giphy', self._from_giphy),
                ('tenor', self._from_tenor),
                ('otakugifs', self._from_otakugifs),
            )
            for provider_name, provider in providers:
                try:
                    url = await asyncio.wait_for(provider(action), timeout=0.9)
                except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
                    log.warning('reaction GIF provider unavailable provider=%s action=%s', provider_name, action)
                if url:
                    break
            # Cache only failures briefly. Successful GIF URLs are never cached,
            # so repeated commands do not keep serving the same animation.
            if url is None:
                self._cache[action] = (time.monotonic(), None)
            else:
                self._cache.pop(action, None)
            if len(self._cache) > self._max_cache:
                oldest = min(self._cache, key=lambda k: self._cache[k][0])
                self._cache.pop(oldest, None)
            return url
