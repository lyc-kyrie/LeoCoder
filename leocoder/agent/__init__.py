"""agent 主循环与会话编排层。"""

__all__ = ["AgentLoop", "AgentSession"]


def __getattr__(name: str):
    if name == "AgentLoop":
        from leocoder.agent.loop import AgentLoop

        return AgentLoop
    if name == "AgentSession":
        from leocoder.agent.session import AgentSession

        return AgentSession
    raise AttributeError(name)
