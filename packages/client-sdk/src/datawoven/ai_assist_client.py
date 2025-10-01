# packages/client-sdk/src/datawoven/ai_assist_client.py
import requests
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class AssistMode(Enum):
    CLOUD = "cloud"
    LOCAL = "local"


@dataclass
class AssistRequest:
    query: str
    context: str = ""
    section: str = "general"


@dataclass
class AssistResponse:
    response: str
    confidence: float
    sources: list = None


class AIAssistClient:
    def __init__(self,
                 mode: AssistMode = AssistMode.CLOUD,
                 api_endpoint: str = None,
                 client_id: str = None,
                 api_key: str = None):
        self.mode = mode
        self.api_endpoint = api_endpoint or "https://api.datawoven.com"
        self.client_id = client_id
        self.api_key = api_key
        self.session = requests.Session()

        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def query(self, request: AssistRequest) -> AssistResponse:
        """Synchronous query to AI Assist service"""
        if self.mode == AssistMode.LOCAL:
            return self._query_local(request)
        else:
            return self._query_cloud(request)

    async def query_async(self, request: AssistRequest) -> AssistResponse:
        """Async version for web applications"""
        # Implementation for async HTTP calls
        pass

    def _query_cloud(self, request: AssistRequest) -> AssistResponse:
        """Query the cloud-based AI service"""
        try:
            response = self.session.post(
                f"{self.api_endpoint}/api/v1/clients/{self.client_id}/assist",
                json={
                    "query": request.query,
                    "context": request.context,
                    "section": request.section
                },
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            return AssistResponse(
                response=data["response"],
                confidence=data.get("confidence", 0.8),
                sources=data.get("sources", [])
            )

        except requests.RequestException as e:
            return AssistResponse(
                response=f"Sorry, I'm having trouble connecting. Please try again later.",
                confidence=0.0,
                sources=[]
            )

    def _query_local(self, request: AssistRequest) -> AssistResponse:
        """Query a local AI service (for admin installations)"""
        try:
            response = self.session.post(
                "http://localhost:8000/assist",
                json={
                    "query": request.query,
                    "context": request.context,
                    "section": request.section
                },
                timeout=30
            )
            # Similar processing...

        except Exception as e:
            return AssistResponse(
                response="Local AI service unavailable",
                confidence=0.0
            )

    def health_check(self) -> bool:
        """Check if the AI service is available"""
        try:
            if self.mode == AssistMode.LOCAL:
                response = self.session.get("http://localhost:8000/health")
            else:
                response = self.session.get(f"{self.api_endpoint}/health")
            return response.status_code == 200
        except:
            return False


# Convenience functions for common use cases
def create_cloud_client(client_id: str, api_key: str) -> AIAssistClient:
    """Factory function for cloud clients"""
    return AIAssistClient(
        mode=AssistMode.CLOUD,
        client_id=client_id,
        api_key=api_key
    )


def create_local_client() -> AIAssistClient:
    """Factory function for local admin clients"""
    return AIAssistClient(mode=AssistMode.LOCAL)
