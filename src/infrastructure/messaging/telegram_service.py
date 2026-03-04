"""Telegram notification service for Aetos."""

import logging
import os

import httpx

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


class TelegramService:
    """Sends notifications to a Telegram chat via the Bot API."""

    def __init__(
        self,
        bot_token: str = TELEGRAM_BOT_TOKEN,
        chat_id: str = TELEGRAM_CHAT_ID,
    ) -> None:
        self._bot_token = bot_token
        self._api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        try:
            self._chat_id: int | str = int(chat_id)
        except (ValueError, TypeError):
            self._chat_id = chat_id  # channel usernames like @mychannel stay as strings

    async def send(self, message: str) -> None:
        """Send a plain-text message. Truncates to Telegram's 4096-char limit."""
        if not self._bot_token or not self._chat_id:
            logging.warning(
                "TelegramService: credentials not set — skipping notification"
            )
            return

        if len(message) > 4096:
            logging.warning(
                f"TelegramService: message exceeds 4096 chars ({len(message)}) — truncating"
            )
            message = message[:4090] + "\n[…]"

        logging.info(
            f"TelegramService: sending message — "
            f"chat_id={self._chat_id!r}, length={len(message)}"
        )
        logging.debug(f"TelegramService: message body:\n{message}")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self._api_url,
                    json={
                        "chat_id": self._chat_id,
                        "text": message,
                        # No parse_mode — explicit plain text to prevent Telegram
                        # misreading special characters in URLs/titles as Markdown
                    },
                )

            logging.info(
                f"TelegramService: response — "
                f"status={response.status_code}, body={response.text}"
            )

            if response.status_code != 200:
                logging.error(
                    f"TelegramService: API error {response.status_code} — {response.text}"
                )

        except httpx.TimeoutException:
            logging.error(
                f"TelegramService: request timed out after 10s — "
                f"chat_id={self._chat_id!r}"
            )
        except httpx.RequestError as exc:
            logging.error(f"TelegramService: connection failed — {exc!r}")

    async def send_error(self, context: str, error: Exception | str) -> None:
        """Convenience method for error notifications with a standard format."""
        await self.send(f"❌ Aetos Error\n{context}\n\n{error}")

    async def send_scrape_results(self, brands: list, matches: list) -> None:
        """Format and send a scrape results summary."""
        brand_str = ", ".join(str(b) for b in brands) if brands else "Unknown"
        lines = [
            "📷 ScraperV2 Session Results",
            f"Brand: {brand_str}",
            f"Matches: {len(matches)} found",
        ]
        for match in matches:
            listing = match.get("listing", {})
            product = match.get("product", {})

            price = round(listing.get("price", 0))
            profit = round(match.get("potential_profit", 0))
            short_url = listing.get("url", "").split("?")[0].rstrip("/")

            lines += [
                "",
                f"{product.get('brand', '')} {product.get('model', '')}".strip()
                or "Unknown product",
                f"\u00a3{price}  \u2022  Est. Profit \u00a3{profit}",
                short_url,
            ]

        await self.send("\n".join(lines))
