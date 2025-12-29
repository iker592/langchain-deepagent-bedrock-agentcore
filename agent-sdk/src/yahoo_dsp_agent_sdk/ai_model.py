from enum import Enum


class AIModel(Enum):
    """
    Enum representing the different AI models available for use in the application.

    These model constants correspond to the model IDs configured in the application properties.

    Example usage:
        model = AIModel.CLAUDE_3_7_SONNET
        model_id = model.model_id  # Gets the actual model ID string
        client = model.client  # Gets the client name to use
    """

    CLAUDE_3_7_SONNET = ("us.anthropic.claude-3-7-sonnet-20250219-v1:0", "sonnet_client")
    CLAUDE_3_5_HAIKU = ("us.anthropic.claude-3-5-haiku-20241022-v1:0", "haiku_3_5_client")
    CLAUDE_4_5_HAIKU = ("us.anthropic.claude-haiku-4-5-20251001-v1:0", "haiku_4_5_client")

    @property
    def model_id(self):
        """Get the model ID string."""
        return self.value[0]

    @property
    def client(self):
        """Get the client name for this model."""
        return self.value[1]

    @classmethod
    def get_model_by_name(cls, name):
        """Retrieve the enum member that corresponds to the given model name string."""
        for model in cls:
            if model.name == name:
                return model
        return None
