"""
Telegram notification module for sending alerts
"""
import requests
from typing import Optional
import config


class TelegramNotifier:
    """Handles sending notifications via Telegram bot"""
    
    def __init__(self):
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """
        Send a message to Telegram
        
        Args:
            message: Message text to send
            parse_mode: Message parse mode (Markdown or HTML)
            
        Returns:
            True if message sent successfully, False otherwise
        """
        endpoint = f"{self.base_url}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode
        }
        
        try:
            response = requests.post(endpoint, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"❌ Failed to send Telegram message: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test Telegram bot connection
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            endpoint = f"{self.base_url}/getMe"
            response = requests.get(endpoint, timeout=10)
            response.raise_for_status()
            bot_info = response.json()
            if bot_info.get("ok"):
                print(f"✅ Telegram bot connected: @{bot_info['result']['username']}")
                return True
            return False
        except Exception as e:
            print(f"❌ Telegram connection failed: {e}")
            return False
