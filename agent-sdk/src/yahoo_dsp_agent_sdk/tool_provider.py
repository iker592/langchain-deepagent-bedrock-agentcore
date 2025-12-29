from abc import ABC, abstractmethod


class ToolProvider(ABC):
    """
    Abstract base class defining the interface for tool providers.
    This interface ensures that all tool provider implementations follow
    a consistent pattern for initialization and tool retrieval.
    """

    @abstractmethod
    def __init__(self) -> None:
        """
        Initialize the tool provider.
        """
        pass

    @abstractmethod
    def get_tools(self) -> list:
        """
        Retrieve the list of tools available from the provider.
        Returns:
            List of tools available from the provider
        """
        pass
