"""
Client module for communicating with the WalletWallet API.
"""
import requests
from typing import Dict, Any, Optional

API_BASE_URL = "https://api.walletwallet.dev"

class WalletWalletClient:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip()
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "GitHub-CAWallet/1.0 (Python/requests)"
        }

    def get_usage(self) -> Dict[str, Any]:
        """Check monthly quota, plan status, and remaining operations."""
        url = f"{API_BASE_URL}/api/auth/usage"
        resp = requests.get(url, headers=self.headers, timeout=15)
        if not resp.ok:
            raise RuntimeError(f"Failed to check usage ({resp.status_code}): {resp.text}")
        return resp.json()

    def create_pass(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /api/passes
        Returns { serialNumber, googleSaveUrl, applePass, shareUrl }
        """
        url = f"{API_BASE_URL}/api/passes"
        resp = requests.post(url, json=payload, headers=self.headers, timeout=30)
        if not resp.ok:
            raise RuntimeError(f"WalletWallet create failed ({resp.status_code}): {resp.text}")
        return resp.json()

    def update_pass(self, serial_number: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        PUT /api/passes/<serial>
        Returns { serialNumber, lastUpdated, notifiedDevices, unchanged }
        """
        url = f"{API_BASE_URL}/api/passes/{serial_number}"
        resp = requests.put(url, json=payload, headers=self.headers, timeout=30)
        if not resp.ok:
            raise RuntimeError(f"WalletWallet update failed ({resp.status_code}): {resp.text}")
        return resp.json()

    def list_passes(self) -> Dict[str, Any]:
        """GET /api/passes: list all active passes on the account."""
        url = f"{API_BASE_URL}/api/passes"
        resp = requests.get(url, headers=self.headers, timeout=15)
        if not resp.ok:
            raise RuntimeError(f"WalletWallet list passes failed ({resp.status_code}): {resp.text}")
        return resp.json()

    def delete_pass(self, serial_number: str) -> Dict[str, Any]:
        """DELETE /api/passes/<serial>"""
        url = f"{API_BASE_URL}/api/passes/{serial_number}"
        resp = requests.delete(url, headers=self.headers, timeout=15)
        if not resp.ok:
            raise RuntimeError(f"WalletWallet delete failed ({resp.status_code}): {resp.text}")
        return resp.json()

