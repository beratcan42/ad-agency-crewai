import asyncio
from typing import Any
from crewai.flow.flow import Flow, start, listen
from pydantic import BaseModel

from ..builder import run_agent

class CampaignState(BaseModel):
    client_id: str = "demo-client"
    brief_title: str = "Yaz Kampanyasi"
    brief_content: str = "Plaj havlusu satislari icin yaz kampanyasi"
    sector: str = "E-ticaret"
    
    account_manager_output: str = ""
    strategist_output: str = ""
    copywriter_output: str = ""
    postiz_result: dict[str, Any] = {}

class CampaignFlow(Flow[CampaignState]):
    def __init__(self, client_id: str, brief_title: str, brief_content: str, sector: str):
        super().__init__()
        self.state.client_id = client_id
        self.state.brief_title = brief_title
        self.state.brief_content = brief_content
        self.state.sector = sector

    @start()
    def analyze_brief(self):
        print("Flow Start: Analyzing Brief via Account Manager...")
        result = asyncio.run(run_agent(
            agent_id="account_manager",
            client_id=self.state.client_id,
            brief_title=self.state.brief_title,
            brief_content=self.state.brief_content,
            sector=self.state.sector,
        ))
        self.state.account_manager_output = result.content
        return self.state.account_manager_output

    @listen(analyze_brief)
    def create_persona(self, am_output: str):
        print("Flow Step: Creating Persona via Strategist...")
        result = asyncio.run(run_agent(
            agent_id="strategist",
            client_id=self.state.client_id,
            brief_title=self.state.brief_title,
            brief_content=self.state.brief_content,
            sector=self.state.sector,
            extra_context=f"Account Manager Analizi:\n{am_output}",
        ))
        self.state.strategist_output = result.content
        return self.state.strategist_output

    @listen(create_persona)
    def write_copy(self, strategist_output: str):
        print("Flow Step: Writing Copy via Copywriter...")
        result = asyncio.run(run_agent(
            agent_id="copywriter",
            client_id=self.state.client_id,
            brief_title=self.state.brief_title,
            brief_content=self.state.brief_content,
            sector=self.state.sector,
            extra_context=f"Stratejist Hedef Kitle ve Yonlendirmesi:\n{strategist_output}",
        ))
        self.state.copywriter_output = result.content
        return self.state.copywriter_output

    @listen(write_copy)
    def publish_to_postiz(self, copywriter_output: str):
        print("Flow Step: Publishing to Postiz via Social Media Agent...")
        # Normalde gercek MCP/Tool entegrasyonu cagirilir (Asama 6.2).
        # Simdilik social media ajani calistiriliyor.
        result = asyncio.run(run_agent(
            agent_id="social_media",
            client_id=self.state.client_id,
            brief_title=self.state.brief_title,
            brief_content=self.state.brief_content,
            sector=self.state.sector,
            extra_context=f"Uretilen Metinler:\n{copywriter_output}\n\nBu metinleri kullanarak 2 haftalik postiz paylasim stratejisi cikar.",
        ))
        self.state.postiz_result = {"status": "success", "content": result.content}
        return self.state.postiz_result
