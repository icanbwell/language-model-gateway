import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from os import makedirs
from pathlib import Path
from typing import AsyncGenerator, Annotated, List

from fastapi import FastAPI, HTTPException
from fastapi.params import Depends
from fastapi.responses import JSONResponse
from langchain_ai_skills_framework.loaders.skill_loader_protocol import (
    SkillLoaderProtocol,
)
from oidcauthlib.auth.middleware.request_scope_middleware import RequestScopeMiddleware
from oidcauthlib.auth.routers.auth_router import AuthRouter
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles

from langchain_ai_skills_framework.loaders.skill_sync import SkillSync
from langchain_ai_skills_framework.loaders.plugin_skill_store import PluginSkillStore
from langchain_ai_skills_framework.startup import initialize_skills
from languagemodelcommon.configs.config_reader.config_reader import ConfigReader
from languagemodelcommon.configs.config_reader.github_config_repo_manager import (
    GithubConfigRepoManager,
)
from key_value.aio.stores.base import BaseContextManagerStore, BaseStore
from languagemodelcommon.configs.schemas.config_schema import ChatModelConfig
from language_model_gateway.container.container_factory import (
    LanguageModelGatewayContainerFactory,
)
from language_model_gateway.gateway.middleware.fastapi_logging_middleware import (
    FastApiLoggingMiddleware,
)
from language_model_gateway.gateway.routers.chat_completion_router import (
    ChatCompletionsRouter,
)
from language_model_gateway.gateway.routers.image_generation_router import (
    ImageGenerationRouter,
)
from language_model_gateway.gateway.routers.images_router import ImagesRouter
from language_model_gateway.gateway.routers.models_router import ModelsRouter
from language_model_gateway.gateway.routers.app_login_router import (
    AppLoginRouter,
)
from language_model_gateway.gateway.routers.token_submission_router import (
    TokenSubmissionRouter,
)
from language_model_gateway.gateway.utilities.endpoint_filter import EndpointFilter
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

from simple_container.container.container_registry import ContainerRegistry
from simple_container.container.inject import Inject

from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)

# warnings.filterwarnings("ignore", category=LangChainBetaWarning)

logger = logging.getLogger(__name__)

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s [%(filename)s:%(lineno)d] %(message)s",
    level=getattr(logging, log_level),
)

# disable INFO logging for httpx because it logs every request
# logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore.http11").setLevel(SRC_LOG_LEVELS["HTTP"])
logging.getLogger("httpcore.connection").setLevel(SRC_LOG_LEVELS["HTTP"])

logging.getLogger("authlib").setLevel(SRC_LOG_LEVELS["AUTH"])

# disable logging calls to /health endpoint
uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.addFilter(EndpointFilter(path="/health"))

# register our container
ContainerRegistry.set_default(
    LanguageModelGatewayContainerFactory.create_container(
        source=f"{__name__}[{uuid.uuid4().hex}]"
    )
)


async def _load_all_configs(
    *,
    config_reader: ConfigReader,
    skill_loader: SkillLoaderProtocol,
) -> None:
    """Eagerly load model configs (incl. MCP JSON), skills, and plugins.

    Uses the async path for skills/plugins so that the snapshot cache
    is populated (the sync ``refresh()`` only updates in-memory state).
    """
    configs = await config_reader.read_model_configs_async()
    logger.info("Loaded %d model configs (includes MCP JSON resolution)", len(configs))

    instructions = await skill_loader.get_instructions()
    logger.info(
        "Loaded skills and plugins (%d chars of instructions)",
        len(instructions),
    )


async def _config_refresh_loop(
    *,
    config_reader: ConfigReader,
    skill_loader: SkillLoaderProtocol,
    interval_minutes: int,
) -> None:
    """Periodically reload all configs in the background."""
    interval_seconds = interval_minutes * 60
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await config_reader.clear_cache()
            # Rebuild skills/plugins from disk and persist to MongoDB.
            await skill_loader.refresh_async()
            await _load_all_configs(
                config_reader=config_reader,
                skill_loader=skill_loader,
            )
            logger.info("Background config refresh completed")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Background config refresh failed", exc_info=True)


@asynccontextmanager
async def lifespan(app1: FastAPI) -> AsyncGenerator[None, None]:
    worker_id = id(app1)
    container = ContainerRegistry.get_current()
    env_vars = container.resolve(LanguageModelGatewayEnvironmentVariables)
    repo_manager = container.resolve(GithubConfigRepoManager)
    snapshot_cache: BaseContextManagerStore = container.resolve(BaseStore)
    config_reader = container.resolve(ConfigReader)
    skill_loader: SkillLoaderProtocol = container.resolve(SkillLoaderProtocol)
    refresh_task: asyncio.Task[None] | None = None
    try:
        logger.info(f"Starting application initialization for worker {worker_id}...")

        # Open the snapshot cache store (MongoDB if configured, memory otherwise)
        await snapshot_cache.__aenter__()

        # Download GitHub config repo if configured (before first request)
        await repo_manager.start()

        # Sync shared skills from plugins marketplace into MongoDB
        await initialize_skills(
            user_store=container.resolve(PluginSkillStore),
            skill_sync=container.resolve(SkillSync),
        )

        # Eagerly load all configs at startup
        await _load_all_configs(
            config_reader=config_reader,
            skill_loader=skill_loader,
        )

        # Start background refresh loop
        interval = env_vars.config_refresh_interval_minutes
        refresh_task = asyncio.create_task(
            _config_refresh_loop(
                config_reader=config_reader,
                skill_loader=skill_loader,
                interval_minutes=interval,
            )
        )
        logger.info("Background config refresh scheduled every %d minutes", interval)

        logger.info(f"Application initialization completed for worker {worker_id}")
        yield

    except Exception:
        logger.exception("Application initialization failed for worker %s", worker_id)
        raise

    finally:
        try:
            logger.info(f"Starting application shutdown for worker {worker_id}...")
            if refresh_task is not None and not refresh_task.done():
                refresh_task.cancel()
                try:
                    await refresh_task
                except asyncio.CancelledError:
                    pass
            await snapshot_cache.__aexit__(None, None, None)
            await repo_manager.stop()
            logger.info("Application shutdown completed")
        except Exception:
            logger.exception("Application shutdown failed for worker %s", worker_id)


def create_app() -> FastAPI:
    app1: FastAPI = FastAPI(title="OpenAI-compatible API", lifespan=lifespan)

    container = ContainerRegistry.get_current()
    env_vars = container.resolve(LanguageModelGatewayEnvironmentVariables)

    app1.include_router(ChatCompletionsRouter().get_router())
    app1.include_router(ModelsRouter().get_router())
    app1.include_router(ImageGenerationRouter().get_router())
    app1.include_router(AuthRouter(prefix="/auth").get_router())
    app1.include_router(AppLoginRouter(prefix="/app").get_router())
    app1.include_router(TokenSubmissionRouter(prefix="/app").get_router())
    # Mount the static directory
    app1.mount(
        "/static",
        StaticFiles(
            directory="/usr/src/language_model_gateway/language_model_gateway/static"
        ),
        name="static",
    )

    image_generation_path: str | None = env_vars.image_generation_path
    if not image_generation_path:
        raise ValueError("IMAGE_GENERATION_PATH environment variable must be set")

    makedirs(image_generation_path, exist_ok=True)
    app1.include_router(
        ImagesRouter(image_generation_path=image_generation_path).get_router()
    )

    # Set up CORS middleware; adjust parameters as needed
    # noinspection PyTypeChecker
    allowed_origins = env_vars.allowed_origins
    app1.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app1.add_middleware(FastApiLoggingMiddleware)

    app1.add_middleware(RequestScopeMiddleware)

    return app1


# Create the FastAPI app instance
app = create_app()


@app.api_route("/health", methods=["GET", "POST"])
async def health() -> str:
    return "OK"


@app.get("/favicon.png", include_in_schema=False)
async def favicon() -> FileResponse:
    # Get absolute path
    file_path = Path("language_model_gateway/static/bwell-web.png")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    return FileResponse(file_path)


@app.get("/refresh")
async def refresh_data(
    request: Request,
    config_reader: Annotated[ConfigReader, Depends(Inject(ConfigReader))],
) -> JSONResponse:
    if config_reader is None:
        raise ValueError("config_reader must not be None")
    if not isinstance(config_reader, ConfigReader):
        raise TypeError(
            f"config_reader must be ConfigReader, got {type(config_reader)}"
        )
    await config_reader.clear_cache()
    configs: List[ChatModelConfig] = await config_reader.read_model_configs_async()
    return JSONResponse({"message": "Configuration refreshed", "data": configs})
