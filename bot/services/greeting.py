from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone
import asyncio
import base64
import logging
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageOps

logger = logging.getLogger('bot.greeting')


class GreetingRenderer:
    """Render customizable welcome/goodbye cards over static images or GIFs.

    `background` may be a local asset path or an http(s) URL. Animated GIFs keep
    their frames/duration so a server can use a custom animated banner.
    """
    CARD_SIZE = (1000, 350)
    AVATAR_SIZE = (190, 190)
    AVATAR_POS = (405, 35)
    TEXT_POS = (500, 270)

    def __init__(self, session=None):
        self.http = session
        self._owns_session = False

    @staticmethod
    def validate_upload(data, content_type=None):
        if not data or len(data) > 10 * 1024 * 1024:
            raise ValueError('Image/GIF must be non-empty and no larger than 10 MB.')
        if content_type and not content_type.startswith('image/'):
            raise ValueError('Please upload an image or GIF.')
        try:
            with Image.open(BytesIO(data)) as image:
                if image.format not in {'PNG', 'JPEG', 'GIF', 'WEBP'}:
                    raise ValueError('Supported formats are PNG, JPEG, GIF, and WebP.')
                if image.width * image.height > 40_000_000 or getattr(image, 'n_frames', 1) > 60:
                    raise ValueError('Image dimensions or GIF frame count are too large.')
                image.verify()
        except (Image.UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
            raise ValueError('The uploaded file is not a valid supported image.') from exc
        return data

    async def start(self):
        if self.http is None or self.http.closed:
            self.http = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15),
                headers={'User-Agent': 'FallenGreetingRenderer/1.0'},
            )
            self._owns_session = True

    async def close(self):
        if self._owns_session and self.http:
            await self.http.close()
            self.http = None
            self._owns_session = False

    async def _ensure_session(self):
        if self.http is None or self.http.closed:
            await self.start()

    async def render(self, member, kind, background, template, count, inviter_id=None, invite_uses=0):
        await self._ensure_session()
        avatar_task = asyncio.create_task(self._avatar(member.display_avatar))
        background_task = asyncio.create_task(self._background_bytes(background))
        avatar, background_bytes = await asyncio.gather(avatar_task, background_task)
        return await asyncio.to_thread(
            self._render_sync, member, background_bytes, template, count, avatar, inviter_id, invite_uses
        )

    async def _avatar(self, avatar_obj):
        fallback = Image.new('RGBA', self.AVATAR_SIZE, (114, 137, 218, 255))
        if not avatar_obj or not hasattr(avatar_obj, 'url'):
            return self._crop_circle(fallback)
        try:
            await self._ensure_session()
            async with self.http.get(str(avatar_obj.url)) as response:
                if response.status == 200:
                    with Image.open(BytesIO(await response.read())) as image:
                        return self._crop_circle(image.convert('RGBA'))
        except Exception:
            logger.warning('Failed to fetch greeting avatar', exc_info=True)
        return self._crop_circle(fallback)

    @classmethod
    def _crop_circle(cls, image):
        image = ImageOps.fit(image, cls.AVATAR_SIZE, Image.Resampling.LANCZOS)
        mask = Image.new('L', cls.AVATAR_SIZE, 0)
        ImageDraw.Draw(mask).ellipse((0, 0) + cls.AVATAR_SIZE, fill=255)
        output = Image.new('RGBA', cls.AVATAR_SIZE, (0, 0, 0, 0))
        output.paste(image, (0, 0), mask)
        return output

    async def _background_bytes(self, source):
        if not source:
            return None
        if isinstance(source, (bytes, bytearray, memoryview)):
            return bytes(source)
        if str(source).startswith('base64:'):
            try:
                return base64.b64decode(str(source)[7:], validate=True)
            except ValueError:
                return None
        if str(source).startswith(("http://", "https://")):
            try:
                await self._ensure_session()
                async with self.http.get(str(source)) as response:
                    if response.status == 200:
                        return await response.read()
            except (aiohttp.ClientError, asyncio.TimeoutError):
                logger.warning('Failed to fetch greeting background', exc_info=True)
            return None
        path = Path(str(source))
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path
        if path.exists():
            return path.read_bytes()
        return None

    @staticmethod
    def _get_font(size):
        for name in ('DejaVuSans.ttf', 'Ubuntu-R.ttf', 'arial.ttf'):
            try:
                return ImageFont.truetype(name, size=size)
            except OSError:
                continue
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()

    @staticmethod
    def _account_age(created_at):
        if created_at is None:
            return 'Unknown'
        try:
            days = max(0, (datetime.now(timezone.utc) - created_at).days)
        except (TypeError, ValueError):
            return 'Unknown'
        years, remaining = divmod(days, 365)
        months, days = divmod(remaining, 30)
        parts = []
        if years:
            parts.append(f'{years}y')
        if months:
            parts.append(f'{months}mo')
        if days or not parts:
            parts.append(f'{days}d')
        return ' '.join(parts)

    @classmethod
    def format_template(cls, member, template, count, inviter_id=None, invite_uses=0):
        guild = getattr(member, 'guild', None)
        inviter_member = guild.get_member(inviter_id) if guild and inviter_id else None
        created_at = getattr(member, 'created_at', None)
        joined_at = getattr(member, 'joined_at', None)
        created_text = created_at.strftime('%Y-%m-%d') if created_at else 'Unknown'
        joined_text = joined_at.strftime('%Y-%m-%d') if joined_at else 'Unknown'
        try:
            return (template or '').format(
                mention=getattr(member, 'mention', str(member)),
                name=getattr(member, 'display_name', str(member)),
                username=getattr(member, 'name', str(member)),
                server=getattr(guild, 'name', 'Server'),
                count=count,
                membercount=count,
                inviter=(f'<@{inviter_id}>' if inviter_id else 'Unknown'),
                inviter_name=(inviter_member.display_name if inviter_member else 'Unknown'),
                invites=invite_uses,
                account_age=cls._account_age(created_at),
                account_created=created_text,
                joined_at=joined_text,
                boosts=int(getattr(guild, 'premium_subscription_count', 0) or 0),
                server_id=getattr(guild, 'id', 0),
                user_id=getattr(member, 'id', 0),
            )
        except (KeyError, ValueError, IndexError):
            logger.warning('Invalid greeting template; sending unformatted template')
            return (template or '')[:1000]

    @classmethod
    def _composite_frame(cls, base, member, template, count, avatar, inviter_id=None, invite_uses=0):
        frame = ImageOps.fit(base.convert('RGBA'), cls.CARD_SIZE, Image.Resampling.LANCZOS)
        frame.paste(avatar, cls.AVATAR_POS, avatar)
        draw = ImageDraw.Draw(frame)
        font = cls._get_font(26)
        text = cls.format_template(member, template, count, inviter_id, invite_uses)
        x, y = cls.TEXT_POS
        shadow = (0, 0, 0, 200)
        for offset_x, offset_y in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            draw.text((x + offset_x, y + offset_y), text[:120], anchor='mm', font=font, fill=shadow)
        draw.text(cls.TEXT_POS, text[:120], anchor='mm', font=font, fill='white')
        return frame

    def _render_sync(self, member, background_bytes, template, count, avatar, inviter_id=None, invite_uses=0):
        out = BytesIO()
        source = None
        try:
            if background_bytes:
                source = Image.open(BytesIO(background_bytes))
                frame_count = getattr(source, 'n_frames', 1)
                if frame_count <= 1:
                    frame = self._composite_frame(source, member, template, count, avatar, inviter_id, invite_uses)
                    frame.save(out, format='PNG', optimize=True)
                    out.seek(0)
                    return out
                frames = []
                durations = []
                for index in range(frame_count):
                    source.seek(index)
                    frames.append(self._composite_frame(
                        source.copy(), member, template, count, avatar, inviter_id, invite_uses
                    ))
                    durations.append(source.info.get('duration', 100))
                frames[0].save(
                    out, format='GIF', save_all=True, append_images=frames[1:],
                    duration=durations, loop=0, disposal=2, optimize=False,
                )
                out.seek(0)
                return out
        except (Image.UnidentifiedImageError, OSError, EOFError):
            logger.warning('Invalid greeting background; rendering default card', exc_info=True)
        finally:
            if source:
                source.close()

        fallback = Image.new('RGBA', self.CARD_SIZE, (32, 36, 43, 255))
        frame = self._composite_frame(fallback, member, template, count, avatar, inviter_id, invite_uses)
        frame.save(out, format='PNG', optimize=True)
        out.seek(0)
        return out

    @staticmethod
    def output_extension(image_data):
        return 'gif' if image_data.getvalue().startswith((b'GIF87a', b'GIF89a')) else 'png'
