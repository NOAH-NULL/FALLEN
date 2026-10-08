from __future__ import annotations

import asyncio
import logging
import os
import random
import time
from typing import Dict, List, Optional, Set

import aiohttp

log = logging.getLogger('bot.reactions')


class ReactionGifService:
    """Fast, reliable reaction GIF resolver with parallel fetches, circuit breaking, 
    and prioritises newly discovered GIFs before cycling used ones."""

    GIPHY_URL = 'https://api.giphy.com/v1/gifs/search'
    TENOR_URL = 'https://tenor.googleapis.com/v2/search'
    OTAKU_GIFS_URL = 'https://api.otakugifs.xyz/gif'

    ALIASES: Dict[str, str] = {
        'highfive': 'wave',
        'pat': 'pat',
        'bonk': 'punch',
        'poke': 'poke',
        'hug': 'hug',
        'wave': 'wave',
        'dance': 'dance',
        'smile': 'smile',
        'happy': 'smile',
        'cry': 'cry',
        'sleep': 'sleep',
        'shrug': 'shrug',
        'boop': 'poke',
        'punch': 'punch',
        'slap': 'slap',
        'bite': 'bite',
        'tickle': 'tickle',
        'hold': 'hug',
        'pout': 'pout',
        'blush': 'blush',
        'uwu': 'smile',
        'fuck': 'fuck',
        'kiss': 'kiss',
        'flirt': 'flirt',
        'attack': 'punch',
        'shoot': 'punch',
        'wreck': 'punch',
        'kill': 'punch',
    }

    def __init__(
        self,
        giphy_api_key: Optional[str] = None,
        tenor_api_key: Optional[str] = None,
        failure_ttl: float = 10.0,
        provider_cooldown: float = 60.0,
        max_pool_per_action: int = 50,
    ):
        self.giphy_api_key = giphy_api_key or os.getenv('GIPHY_API_KEY')
        self.tenor_api_key = tenor_api_key or os.getenv('TENOR_API_KEY')

        self._session: Optional[aiohttp.ClientSession] = None
        self._locks: Dict[str, asyncio.Lock] = {}

        # Caching and pools
        self._failure_cache: Dict[str, float] = {}       # action -> failed_at timestamp
        self._gif_pool: Dict[str, Dict[str, None]] = {}  # action -> insertion-ordered dict (ordered set)
        self._gif_used: Dict[str, Set[str]] = {}          # action -> set of used URLs

        # Provider health tracking (Circuit Breaker)
        self._provider_backoff: Dict[str, float] = {}   # provider_name -> block_until_timestamp

        # Configuration
        self._failure_ttl = failure_ttl
        self._provider_cooldown = provider_cooldown
        self._max_pool_per_action = max_pool_per_action

    async def start(self) -> None:
        """Initialize HTTP Client Session with connection limits and timeouts."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)
            timeout = aiohttp.ClientTimeout(total=3.0, connect=1.0)
            self._session = aiohttp.ClientSession(connector=connector, timeout=timeout)

    async def close(self) -> None:
        """Clean up HTTP session and reset state."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        self._failure_cache.clear()
        self._locks.clear()
        self._gif_pool.clear()
        self._gif_used.clear()
        self._provider_backoff.clear()

    def _is_provider_healthy(self, provider_name: str, now: float) -> bool:
        """Check if a provider is out of backoff status."""
        until = self._provider_backoff.get(provider_name, 0.0)
        return now >= until

    def _mark_provider_failed(self, provider_name: str, now: float) -> None:
        """Temporarily suspend querying a failing API endpoint."""
        self._provider_backoff[provider_name] = now + self._provider_cooldown
        log.warning("Provider %s suspended for %ss due to errors/timeouts", provider_name, self._provider_cooldown)

    async def _from_giphy(self, action: str) -> List[str]:
        if not self.giphy_api_key or not self._session:
            return []
        try:
            params = {
                'api_key': self.giphy_api_key,
                'q': f'anime {action} reaction',
                'limit': 15,
                'rating': 'pg',
            }
            async with self._session.get(self.GIPHY_URL, params=params) as response:
                if response.status != 200:
                    return []
                data = await response.json()
                return [
                    item['images']['original']['url']
                    for item in data.get('data', [])
                    if item.get('images', {}).get('original', {}).get('url')
                ]
        except Exception as exc:
            log.debug("Giphy fetch failed for action %s: %s", action, exc)
            raise

    async def _from_tenor(self, action: str) -> List[str]:
        if not self.tenor_api_key or not self._session:
            return []
        try:
            params = {
                'key': self.tenor_api_key,
                'q': f'anime {action} reaction',
                'limit': 15,
                'media_filter': 'gif',
                'contentfilter': 'low',
            }
            async with self._session.get(self.TENOR_URL, params=params) as response:
                if response.status != 200:
                    return []
                data = await response.json()
                return [
                    result['media_formats']['gif']['url']
                    for result in data.get('results', [])
                    if result.get('media_formats', {}).get('gif', {}).get('url')
                ]
        except Exception as exc:
            log.debug("Tenor fetch failed for action %s: %s", action, exc)
            raise

    async def _from_otakugifs(self, action: str) -> List[str]:
        if not self._session:
            return []
        try:
            async with self._session.get(self.OTAKU_GIFS_URL, params={'reaction': action}) as response:
                if response.status != 200:
                    return []
                data = await response.json()
                url = data.get('url')
                return [url] if url else []
        except Exception as exc:
            log.debug("OtakuGIFs fetch failed for action %s: %s", action, exc)
            raise

    async def _fetch_all_providers(self, action_key: str, now: float) -> List[str]:
        """Fetch candidates in parallel from all healthy providers."""
        providers = [
            ('otakugifs', self._from_otakugifs),
            ('tenor', self._from_tenor),
            ('giphy', self._from_giphy),
        ]

        active_tasks = []
        task_providers = []

        for name, fetch_fn in providers:
            if self._is_provider_healthy(name, now):
                active_tasks.append(asyncio.create_task(fetch_fn(action_key)))
                task_providers.append(name)

        if not active_tasks:
            return []

        results = await asyncio.gather(*active_tasks, return_exceptions=True)
        combined_urls: List[str] = []

        for name, res in zip(task_providers, results):
            if isinstance(res, Exception):
                self._mark_provider_failed(name, now)
            elif isinstance(res, list):
                combined_urls.extend(res)

        return combined_urls

    async def get(self, action: str) -> Optional[str]:
        """Resolve a high-quality reaction GIF URL prioritizing newly fetched results."""
        action_key = self.ALIASES.get(action.lower(), action.lower())
        now = time.monotonic()

        # Fast-path check for negative cache
        failed_at = self._failure_cache.get(action_key)
        if failed_at and (now - failed_at) < self._failure_ttl:
            return None

        lock = self._locks.setdefault(action_key, asyncio.Lock())
        async with lock:
            now = time.monotonic()
            failed_at = self._failure_cache.get(action_key)
            if failed_at and (now - failed_at) < self._failure_ttl:
                return None

            await self.start()

            # Pools are dicts operating as ordered sets (preserving insertion order)
            pool = self._gif_pool.setdefault(action_key, {})
            used = self._gif_used.setdefault(action_key, set())

            # 1. If pool is exhausted of unused URLs -> Fetch fresh provider results
            if not [url for url in pool if url not in used]:
                fetched_urls = await self._fetch_all_providers(action_key, now)

                # Filter for genuinely new URLs not yet known to the pool
                new_urls = [url for url in fetched_urls if url and url not in pool]

                if new_urls:
                    for url in new_urls:
                        pool[url] = None  # Add to end of insertion-ordered dict
                else:
                    # 2. No new URLs discovered -> Reset used pool fallback
                    used.clear()

            # Trim pool from FRONT (oldest URLs) if max size exceeded, keeping fresh URLs safe
            while len(pool) > self._max_pool_per_action:
                oldest_url = next(iter(pool))
                del pool[oldest_url]
                used.discard(oldest_url)

            # Recalculate available pool directly from the finalized trimmed pool state
            available = [url for url in pool if url not in used]

            if not available:
                self._failure_cache[action_key] = time.monotonic()
                return None

            url = random.choice(available)
            used.add(url)
            self._failure_cache.pop(action_key, None)
            return url
