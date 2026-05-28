import csv
from io import StringIO
from typing import Union, Optional


class CsvToMarkdownConverter:
    @staticmethod
    def csv_to_markdown_table(
        *,
        csv_string: str,
        delimiter: str = ",",
        quote_char: str = '"',
        has_header: bool = True,
        max_column_width: Optional[int] = None,
    ) -> str:
        """
        Convert a CSV string to a Markdown table, handling quoted fields.

        Args:
            csv_string (str): The input CSV string
            delimiter (str, optional): CSV delimiter. Defaults to ','.
            quote_char (str, optional): Quote character. Defaults to '"'.
            has_header (bool, optional): Whether the first row is a header. Defaults to True.
            max_column_width (Optional[int], optional): Maximum column width before truncation. Defaults to None.

        Returns:
            str: Markdown formatted table
        """
        # Normalize input string and strip whitespace
        csv_string = csv_string.strip()

        # Use StringIO to make the CSV string file-like
        csv_file = StringIO(csv_string)

        # Use csv reader with quote handling
        csv_reader = csv.reader(
            csv_file,
            delimiter=delimiter,
            quotechar=quote_char,
            skipinitialspace=True,  # Ignore spaces after delimiter
        )

        # Convert rows to list for processing
        try:
            rows = list(csv_reader)
        except csv.Error as e:
            return f"Error parsing CSV: {str(e)}"

        if not rows:
            return "| No Data |"

        # Separate headers and data rows
        headers = (
            rows[0] if has_header else [f"Column {i + 1}" for i in range(len(rows[0]))]
        )
        data_rows = rows[1:] if has_header else rows

        def escape_markdown_chars(text: str) -> str:
            """
            Comprehensively escape characters for Markdown table safety.

            Args:
                text (str): Input text to escape

            Returns:
                str: Escaped text safe for Markdown tables
            """
            # Escape Markdown special characters
            escape_map = {
                "|": "\\|",  # Pipe character (table separator)
                "_": "\\_",  # Italic/underline marker
                "*": "\\*",  # Bold/italic marker
                "[": "\\[",  # Link start
                "]": "\\]",  # Link end
                "`": "\\`",  # Code marker
            }

            # Escape special characters
            escaped_text = "".join(escape_map.get(char, char) for char in text)

            # Handle escape sequences
            escaped_text = (
                escaped_text.replace("\n", "\\n")  # Newline
                .replace("\t", "\\t")  # Tab
                .replace("\r", "\\r")  # Carriage return
            )

            return escaped_text

        def sanitize_cell_content(cell: Union[str, object]) -> str:
            """
            Sanitize cell content for Markdown table display.

            Args:
                cell (Union[str, object]): Cell content to sanitize

            Returns:
                str: Sanitized string representation
            """
            # Convert to string and handle None/empty values
            if cell is None:
                return ""

            # Convert to string and escape
            cell_str = str(cell).strip()

            # Escape Markdown and special characters
            return escape_markdown_chars(cell_str)

        # Truncate content if max_column_width is specified
        def truncate_cell(cell: str) -> str:
            if max_column_width and len(cell) > max_column_width:
                return cell[: max_column_width - 3] + "..."
            return cell

        # Create Markdown table
        # noinspection PyListCreation
        markdown_lines = []

        # Header row with sanitization and optional truncation
        markdown_lines.append(
            "| "
            + " | ".join(
                truncate_cell(sanitize_cell_content(header)) for header in headers
            )
            + " |"
        )

        # Separator row with alignment
        markdown_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # Data rows with sanitization and optional truncation
        for row in data_rows:
            markdown_lines.append(
                "| "
                + " | ".join(truncate_cell(sanitize_cell_content(cell)) for cell in row)
                + " |"
            )

        return "\n".join(markdown_lines)
