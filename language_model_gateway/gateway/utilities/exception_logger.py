import logging
import os
import traceback
from typing import List, Optional

import sys

from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["ERRORS"])


class ExceptionLogger:
    @staticmethod
    def extract_error_details(error: Exception | ExceptionGroup) -> str | None:
        """
        Extract comprehensive error details from an Exception or ExceptionGroup.

        Args:
            error (Union[Exception, ExceptionGroup]): The exception to extract details from

        Returns:
            str: A formatted string containing error details
        """

        def get_short_traceback(
            exception: Optional[BaseException] = None, max_depth: int = 3
        ) -> List[str]:
            """
            Generate a short, readable stack trace.

            :param exception: Exception to trace (uses current exception if None)
            :param max_depth: Maximum number of stack frames to include
            :return: List of simplified stack trace entries
            """
            # If no exception provided, get the current exception
            if exception is None:
                exception = sys.exc_info()[1]

            if exception is None:
                return []

            # Get the traceback
            tb = exception.__traceback__

            # Collect stack frames
            stack_frames = []
            current_frame = tb
            depth = 0

            while current_frame and depth < max_depth:
                # Get filename and line number
                filename: str = os.path.basename(
                    current_frame.tb_frame.f_code.co_filename
                )
                lineno: int | None = current_frame.tb_lineno
                func_name: str = current_frame.tb_frame.f_code.co_name

                # Create a readable stack frame entry
                stack_entry = f"{filename}:{lineno} in {func_name}"
                stack_frames.append(stack_entry)

                # Move to next frame
                current_frame = current_frame.tb_next
                depth += 1

            # If the exception has a __cause__ or __context__, include their tracebacks as well
            cause = getattr(exception, "__cause__", None)
            context = getattr(exception, "__context__", None)
            if (cause or context) and depth < max_depth:
                related = cause or context
                stack_frames.append("Caused by:")
                stack_frames.extend(
                    get_short_traceback(
                        related, max_depth=max_depth - len(stack_frames)
                    )
                )

            return stack_frames

        def extract_exception_messages(
            exception: Exception | BaseException,
        ) -> List[str]:
            """
            Extract messages from a nested exception chain.

            :param exception: The root exception
            :return: List of exception messages from the exception chain
            """
            messages = []
            current_exception: Optional[BaseException] = exception

            while current_exception is not None:
                # Extract message or str representation
                message = str(current_exception)
                messages.append(message)

                # Move to the cause/context of the exception
                current_exception = (
                    current_exception.__cause__ or current_exception.__context__
                )

            return messages

        def format_single_exception(exc: Exception) -> str:
            """
            Format details for a single exception.

            Args:
                exc (Exception): The exception to format

            Returns:
                str: Formatted exception details
            """
            # Extract full traceback
            tb_details = traceback.extract_tb(exc.__traceback__)

            # Construct error message with type, value, and traceback
            messages = extract_exception_messages(exc)
            # error_lines = [
            #     f"Type: {type(exc).__name__}",
            #     f"Message:",
            # ]
            error_lines: List[str] = []
            error_lines.extend(messages)
            # error_lines.append("Stack trace:")
            # short_trace_lines: List[str] = get_short_traceback(exc)
            # error_lines.extend(short_trace_lines)
            if logger.isEnabledFor(logging.DEBUG):
                error_lines.append("Traceback:")
                # # Add traceback details
                for frame in tb_details:
                    error_lines.append(
                        f"  File {frame.filename}, line {frame.lineno}, in {frame.name}"
                    )
                    if frame.line:
                        error_lines.append(f"    {frame.line.strip()}")

            return "\n".join(error_lines)

        # Handle single Exception
        if isinstance(error, Exception) and not isinstance(error, ExceptionGroup):
            return format_single_exception(error)

        # Handle ExceptionGroup
        if isinstance(error, ExceptionGroup):
            error_details: List[str] = []

            # Recursively extract details from nested exceptions
            def extract_nested_exceptions(exc_group: ExceptionGroup) -> None:
                for exc in exc_group.exceptions:
                    if isinstance(exc, ExceptionGroup):
                        extract_nested_exceptions(exc)
                    else:
                        error_details.append(format_single_exception(exc))

            # Start extraction
            error_details.append(f"Exception Group: {error.message}")
            extract_nested_exceptions(error)

            return "\n\n".join(error_details)
