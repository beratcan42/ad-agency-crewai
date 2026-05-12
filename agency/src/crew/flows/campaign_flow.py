from typing import Any
from crewai.flow.flow import Flow, start, listen
from pydantic import BaseModel

class CampaignState(BaseModel):
    brief: str = ""
    persona: str = ""
    copy: str = ""
    postiz_result: dict[str, Any] = {}

class CampaignFlow(Flow[CampaignState]):
    @start()
    def analyze_brief(self):
        print("Flow Start: Analyzing Brief...")
        # Normalde Account Manager'dan gecer.
        self.state.brief = "Yaz kampanyasi icin plaj havlusu reklami"
        return self.state.brief

    @listen(analyze_brief)
    def create_persona(self, brief: str):
        print(f"Flow Step: Creating Persona for brief: {brief}")
        # Normalde Strategist cagirilir.
        self.state.persona = "18-35 yas arasi tatil tutkunlari"
        return self.state.persona

    @listen(create_persona)
    def write_copy(self, persona: str):
        print(f"Flow Step: Writing Copy for persona: {persona}")
        # Normalde Copywriter cagirilir.
        self.state.copy = "Yazin tadini cikar! Yeni plaj havlularimiz stoklarda. 🏖️"
        return self.state.copy

    @listen(write_copy)
    def publish_to_postiz(self, copy: str):
        print(f"Flow Step: Publishing to Postiz. Copy: {copy}")
        # Normalde MCP Gateway araciligiyla Social Media Agent is yapar.
        self.state.postiz_result = {"status": "drafted", "id": "mock_123"}
        return self.state.postiz_result
