from __future__ import annotations

import logging
import time
from logging import Logger
from typing import TYPE_CHECKING, Optional

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState, StatementResponse
import pandas as pd
from pandas.core.frame import DataFrame

if TYPE_CHECKING:
    from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
        LanguageModelGatewayEnvironmentVariables,
    )


class DatabricksHelper:
    def __init__(
        self,
        *,
        catalog: str = "bronze",
        schema: str = "fhir_rpt",
        environment_variables: LanguageModelGatewayEnvironmentVariables | None = None,
    ) -> None:
        # Initialize logger as time, error level, and message
        self.logger: Logger = logging.getLogger(__name__)
        logging.basicConfig(
            format="%(asctime)s %(levelname)s %(name)s [%(filename)s:%(lineno)d] %(message)s",
            level=logging.INFO,
        )
        self.catalog = catalog
        self.schema = schema
        self._environment_variables: LanguageModelGatewayEnvironmentVariables | None = (
            environment_variables
        )

    def parse_databricks_statement_response(
        self, statement_response: StatementResponse
    ) -> Optional[pd.DataFrame]:
        """
        Simple parser to create a DataFrame from Databricks StatementResponse
        Args:
            statement_response: Databricks StatementResponse object
        Returns:
            Pandas DataFrame with query results
        """
        try:
            if not statement_response.manifest:
                raise ValueError("statement_response.manifest is required")
            if not statement_response.manifest.schema:
                raise ValueError("statement_response.manifest.schema is required")
            if not statement_response.manifest.schema.columns:
                raise ValueError(
                    "statement_response.manifest.schema.columns is required"
                )
            # Extract column names
            column_names = [
                column.name for column in statement_response.manifest.schema.columns
            ]
            if not statement_response.result:
                raise ValueError("statement_response.result is required")
            # Extract data array
            data_array = statement_response.result.data_array
            # Create DataFrame
            df = pd.DataFrame(data_array, columns=column_names)

            return df

        except Exception as e:
            self.logger.error(f"Error parsing Databricks statement response: {e}")
            return None

    def dataframe_to_markdown(self, df: DataFrame) -> str:
        """
        Convert a pandas DataFrame to a markdown-formatted table
        Args:
            df (pandas.DataFrame): Input DataFrame
        Returns:
            str: Markdown-formatted table
        """
        # Create header
        markdown_table = "| " + " | ".join(df.columns) + " |\n"
        # Create separator line
        markdown_table += "| " + " | ".join(["---"] * len(df.columns)) + " |\n"
        # Add rows
        for _, row in df.iterrows():
            markdown_table += "| " + " | ".join(str(val) for val in row) + " |\n"

        return markdown_table

    def execute_query(self, query: str, max_wait_time: int = 300) -> str:
        databricks_host: Optional[str] = (
            self._environment_variables.databricks_host
            if self._environment_variables
            else None
        )
        databricks_token: Optional[str] = (
            self._environment_variables.databricks_token
            if self._environment_variables
            else None
        )
        warehouse_id: Optional[str] = (
            self._environment_variables.databricks_sql_warehouse_id
            if self._environment_variables
            else None
        )

        if not databricks_host:
            raise ValueError("DATABRICKS_HOST environment variable not set")
        if not databricks_token:
            raise ValueError("DATABRICKS_TOKEN environment variable not set")
        if not warehouse_id:
            raise ValueError("DATABRICKS_SQL_WAREHOUSE_ID environment variable not set")

        try:
            ws_client = WorkspaceClient(
                host=databricks_host,
                token=databricks_token,
            )
            # Execute initial statement
            self.logger.debug(f"Executing Databricks query: {query}")
            self.logger.debug(f"Warehouse ID: {warehouse_id}")
            results = ws_client.statement_execution.execute_statement(
                query, warehouse_id=warehouse_id
            )
            if results.status is None:
                raise ValueError("results.status is required")
            self.logger.debug(f"Initial results status: {results.status.state}")

            # Track start time for timeout
            start_time = time.time()

            # Wait while statement is pending
            while results.status.state == StatementState.PENDING:
                # Check for timeout
                self.logger.debug("Waiting for query to complete")
                if time.time() - start_time >= max_wait_time:
                    self.logger.error(f"Query timed out after {max_wait_time} seconds")
                    raise TimeoutError("Query execution timed out")

                # Wait before checking again
                time.sleep(1)  # Wait 1 second between checks

                # Refresh the statement status
                self.logger.debug("Refreshing statement status")
                if results.statement_id is None:
                    raise ValueError("results.statement_id is required")
                results = ws_client.statement_execution.get_statement(
                    results.statement_id
                )
                if results.status is None:
                    raise ValueError("results.status is required")
                if results.status.state != StatementState.PENDING:
                    break

            if results.status is None:
                raise ValueError("results.status is required")
            # Check for failed state
            if results.status.state == StatementState.FAILED:
                error_message = (
                    results.status.error.message
                    if results.status.error
                    else "Unknown error"
                )
                self.logger.error(f"Error executing Databricks query: {error_message}")
                return f"Error executing Databricks query: {error_message}"

            # Log successful execution
            self.logger.info(f"Query executed successfully: {results}")

            # Parse and return results
            df = self.parse_databricks_statement_response(results)
            if df is not None:
                return self.dataframe_to_markdown(df)

            return "Dataframe was None. Unable to parse results"

        except Exception as e:
            self.logger.error(f"Error executing Databricks query: {e}")
            return ""
