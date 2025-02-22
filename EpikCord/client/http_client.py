import asyncio
import contextlib
import zlib
from importlib.util import find_spec
from logging import getLogger
from typing import Any, Dict, Optional, Union

from aiohttp import ClientSession, ClientWebSocketResponse

from ..exceptions import (
    DiscordAPIError,
    DiscordServerError5xx,
    Forbidden403,
    NotFound404,
)
from ..status_code import HTTPCodes

logger = getLogger(__name__)

_ORJSON = find_spec("orjson")


if _ORJSON:
    import orjson as json

else:
    import json  # type: ignore


class _FakeTask:
    def cancel(self):
        return True


class UnknownBucket:
    def __init__(self):
        self.event = asyncio.Event()
        self.close_task: _FakeTask = _FakeTask()


class Bucket(UnknownBucket):
    def __init__(self, *, discord_hash: str):
        super().__init__()
        self.bucket_hash = discord_hash

    def __eq__(self, other):
        return self.bucket_hash == other.bucket_hash


class DiscordWSMessage:
    def __init__(self, *, data, type, extra):
        self.data = data
        self.type = type
        self.extra = extra

    def json(self) -> Any:
        return json.loads(self.data)


class DiscordGatewayWebsocket(ClientWebSocketResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buffer: bytearray = bytearray()
        self.inflator = zlib.decompressobj()

    async def receive(self, *args, **kwargs):
        ws_message = await super().receive(*args, **kwargs)
        message = ws_message.data

        if isinstance(message, bytes):

            self.buffer.extend(message)

            if len(message) < 4 or message[-4:] != b"\x00\x00\xff\xff":
                return

            message = self.inflator.decompress(self.buffer)

            message = message.decode("utf-8")
            self.buffer: bytearray = bytearray()

        return DiscordWSMessage(
            data=message, type=ws_message.type, extra=ws_message.extra
        )


class HTTPClient(ClientSession):
    def __init__(self, *args, **kwargs):
        self.base_uri: str = kwargs.pop(
            "discord_endpoint", "https://discord.com/api/v10"
        )
        super().__init__(
            *args,
            **kwargs,
            json_serialize=lambda x, *__, **___: json.dumps(x).decode()
            if _ORJSON
            else json.dumps(x),
            ws_response_class=DiscordGatewayWebsocket,
        )
        self.global_ratelimit: asyncio.Event = asyncio.Event()
        self.global_ratelimit.set()
        self.buckets: Dict[str, Bucket] = {}

    async def request(  # type: ignore
        self,
        method,
        url,
        *args,
        attempt: int = 1,
        to_discord=True,
        guild_id: Union[str, int] = 0,
        channel_id: Union[int, str] = 0,
        **kwargs,
    ):
        if attempt > 5:
            logger.critical(f"Failed a {method} {url} 5 times.")
            return

        if url.startswith("ws") or not to_discord:
            return await super().request(method, url, *args, **kwargs)

        if url.startswith("/"):
            url = url[1:]

        if url.endswith("/"):
            url = url[:-1]

        url = f"{self.base_uri}/{url}"

        bucket_hash = f"{guild_id}:{channel_id}:{url}"
        bucket: Union[Bucket, UnknownBucket] = self.buckets.get(
            bucket_hash, UnknownBucket()
        )

        await bucket.event.wait()
        await self.global_ratelimit.wait()

        res = await super().request(method, url, *args, **kwargs)

        await self.log_request(res, kwargs.get("json", kwargs.get("data", None)))

        if isinstance(bucket, UnknownBucket) and res.headers.get("X-RateLimit-Bucket"):
            if guild_id or channel_id:
                self.buckets[bucket_hash] = Bucket(
                    discord_hash=res.headers["X-RateLimit-Bucket"]
                )

            else:
                b = Bucket(discord_hash=res.headers["X-RateLimit-Bucket"])
                if b in self.buckets.values():
                    self.buckets[bucket_hash] = {v: k for k, v in self.buckets.items()}[
                        b
                    ]  # type: ignore
                else:
                    self.buckets[bucket_hash] = b
        body: Union[Dict, str] = {}
        if res.headers["Content-Type"] == "application/json":
            body = await res.json()
        else:
            body = await res.text()

        if res.status in range(200, 299):
            bucket.event.set()
            self.global_ratelimit.set()
            return res

        if (
            int(res.headers.get("X-RateLimit-Remaining", 1)) == 0
            and res.status != HTTPCodes.TOO_MANY_REQUESTS
        ):
            logger.critical(
                f"Exhausted {res.headers['X-RateLimit-Bucket']} ({res.url}). "
                f"Reset in {res.headers['X-RateLimit-Reset-After']} seconds"
            )

            await asyncio.sleep(float(res.headers["X-RateLimit-Reset-After"]))
        if res.status == HTTPCodes.TOO_MANY_REQUESTS:
            time_to_sleep: Union[float, int] = (
                body["retry_after"]  # type: ignore
                if body["retry_after"] > res.headers["X-RateLimit-Reset-After"]  # type: ignore
                else res.headers["X-RateLimit-Reset-After"]
            )

            logger.critical(f"Rate limited. Reset in {time_to_sleep} seconds")
            if res.headers["X-RateLimit-Scope"] == "global":
                await self.global_ratelimit.clear()  # type: ignore

            await asyncio.sleep(time_to_sleep)

            await self.global_ratelimit.set()  # type: ignore

            return await self.request(method, url, *args, **kwargs, attempt=attempt + 1)

        if res.status >= HTTPCodes.SERVER_ERROR:
            raise DiscordServerError5xx(body)

        elif res.status == HTTPCodes.NOT_FOUND:
            raise NotFound404(body)

        elif res.status == HTTPCodes.FORBIDDEN:
            raise Forbidden403(body)

        elif not 300 > res.status >= 200:
            raise DiscordAPIError(body)

        if not bucket.event.is_set():
            try:
                bucket.event.set()
            except Exception as e:
                logger.exception(e)

        async def dispose():
            await asyncio.sleep(300)

            with contextlib.suppress(KeyError):
                del self.buckets[bucket_hash]

        bucket.close_task.cancel()

        bucket.close_task = asyncio.get_event_loop().create_task(dispose())  # type: ignore

        bucket.event.set()
        self.global_ratelimit.set()

        return res

    @staticmethod
    async def log_request(res, body: Optional[dict] = None):
        message = [
            f"Sent a {res.request_info.method} to {res.url} "
            f"and got a {res.status} response. ",
            f"Content-Type: {res.headers['Content-Type']} ",
        ]

        if body:
            message.append(f"Sent body: {body} ")

        if h := dict(res.request_info.headers):
            message.append(f"Sent headers: {h} ")

        if h := dict(res.headers):
            message.append(f"Received headers: {h} ")

        try:
            message.append(f"Received body: {await res.json()} ")

        finally:
            logger.debug("".join(message))

    async def get(  # type: ignore
        self,
        url,
        *args,
        to_discord: bool = True,
        **kwargs,
    ):
        if to_discord:
            return await self.request("GET", url, *args, **kwargs)
        return await super().get(url, *args, **kwargs)

    async def post(self, url, *args, to_discord: bool = True, **kwargs):  # type: ignore
        if to_discord:
            return await self.request("POST", url, *args, **kwargs)
        return await super().post(url, *args, **kwargs)

    async def patch(self, url, *args, to_discord: bool = True, **kwargs):  # type: ignore
        if to_discord:
            res = await self.request("PATCH", url, *args, **kwargs)
            return res
        return await super().patch(url, *args, **kwargs)

    async def delete(self, url, *args, to_discord: bool = True, **kwargs):  # type: ignore
        if to_discord:
            res = await self.request("DELETE", url, *args, **kwargs)
            return res
        return await super().delete(url, **kwargs)

    async def put(self, url, *args, to_discord: bool = True, **kwargs):  # type: ignore
        if to_discord:
            res = await self.request("PUT", url, *args, **kwargs)
            return res
        return await super().put(url, *args, **kwargs)


__all__ = ("HTTPClient",)
