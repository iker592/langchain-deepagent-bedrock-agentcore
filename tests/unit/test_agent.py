import pytest

AGENT_MODULE = "agents.dsp.agent"


class MockModel:
    pass


class MockSessionManager:
    def register_hooks(self, registry):
        pass


@pytest.mark.unit
class TestAgentCreation:
    def test_create_agent_without_memory(self, monkeypatch):
        monkeypatch.delenv("MEMORY_ID", raising=False)
        monkeypatch.setattr(
            f"{AGENT_MODULE}.BedrockModel", lambda **kwargs: MockModel()
        )

        from agents.dsp.agent import create_agent

        agent = create_agent()

        assert agent is not None
        print("✅ Agent created successfully without memory")

    def test_create_agent_with_custom_agent_id(self, monkeypatch):
        monkeypatch.delenv("MEMORY_ID", raising=False)
        monkeypatch.setattr(
            f"{AGENT_MODULE}.BedrockModel", lambda **kwargs: MockModel()
        )

        from agents.dsp.agent import create_agent

        agent = create_agent(agent_id="custom-agent")

        assert agent is not None
        print("✅ Agent created with custom agent_id")

    def test_create_agent_with_memory_id(self, monkeypatch):
        monkeypatch.setenv("MEMORY_ID", "test-memory")
        monkeypatch.setattr(
            f"{AGENT_MODULE}.BedrockModel", lambda **kwargs: MockModel()
        )
        monkeypatch.setattr(
            f"{AGENT_MODULE}.AgentCoreMemorySessionManager",
            lambda **kwargs: MockSessionManager(),
        )

        from agents.dsp.agent import create_agent

        agent = create_agent(session_id="sess-123", actor_id="user-456")

        assert agent is not None
        print("✅ Agent created with memory session manager")


@pytest.mark.unit
class TestAgentConfiguration:
    def test_create_agent_returns_agent_instance(self, monkeypatch):
        monkeypatch.delenv("MEMORY_ID", raising=False)
        monkeypatch.setattr(
            f"{AGENT_MODULE}.BedrockModel", lambda **kwargs: MockModel()
        )

        from agents.dsp.agent import create_agent

        agent = create_agent()

        assert agent is not None
        assert hasattr(agent, "invoke")
        print("✅ Agent has invoke method")
