from typing import Optional, Literal

import tiktoken

TOKEN_REDUCER_STRATEGY = Literal["end", "beginning", "smart"]


class TokenReducer:
    """
    A utility class for counting and reducing tokens in text based on a specified model's encoding.
    """

    def __init__(
        self,
        model: str = "cl100k_base",
        truncation_strategy: TOKEN_REDUCER_STRATEGY = "end",
    ):
        """
        Initialize TokenReducer with specific model and truncation strategy.

        Args:
            model: The encoding model to use (default: "gpt-3.5-turbo")
            truncation_strategy: How to reduce tokens ('end', 'beginning', 'smart')
        """
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to a default encoding if model not found
            self.encoding = tiktoken.get_encoding("cl100k_base")

        self.model = model
        self.truncation_strategy = truncation_strategy

    def reduce_tokens(
        self, text: str, max_tokens: int, preserve_start: Optional[int] = None
    ) -> str:
        """
        Reduce text to specified maximum number of tokens.

        Args:
            text: Input text to reduce
            max_tokens: Maximum number of tokens allowed
            preserve_start: Number of initial tokens to always preserve

        Returns:
            Reduced text within token limit
        """
        # Encode the text
        tokens = self.encoding.encode(text)

        # Check if already within token limit
        if len(tokens) <= max_tokens:
            return text

        # Handle different truncation strategies
        if self.truncation_strategy == "end":
            # Truncate from the end
            reduced_tokens = tokens[:max_tokens]

        elif self.truncation_strategy == "beginning":
            # Truncate from the beginning
            reduced_tokens = tokens[-max_tokens:]

        elif self.truncation_strategy == "smart":
            # Preserve start tokens if specified
            if preserve_start and preserve_start < max_tokens:
                preserved_start = tokens[:preserve_start]
                remaining_tokens = max_tokens - preserve_start
                reduced_tokens = preserved_start + tokens[-(remaining_tokens):]
            else:
                # Default to end truncation if preserve_start is not feasible
                reduced_tokens = tokens[:max_tokens]

        else:
            raise ValueError(f"Invalid truncation strategy: {self.truncation_strategy}")

        # Decode back to text
        return self.encoding.decode(reduced_tokens)

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in the given text.

        Args:
            text: Input text to count tokens for

        Returns:
            Number of tokens in the text
        """
        return len(self.encoding.encode(text))
