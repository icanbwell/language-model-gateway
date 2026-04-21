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
from oidcauthlib.auth.middleware.request_scope_middleware import RequestScopeMiddleware
from oidcauthlib.auth.routers.auth_router import AuthRouter
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles

from langchain_ai_skills_framework.loaders.skill_sync import SkillSync
from langchain_ai_skills_framework.loaders.user_skill_store import UserSkillStore
from langchain_ai_skills_framework.startup import initialize_skills
from languagemodelcommon.configs.config_reader.config_reader import ConfigReader
from languagemodelcommon.configs.config_reader.github_config_repo_manager import (
    GithubConfigRepoManager,
)
from key_value.aio.stores.base import BaseStore
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


@asynccontextmanager
async def lifespan(app1: FastAPI) -> AsyncGenerator[None, None]:
    worker_id = id(app1)
    container = ContainerRegistry.get_current()
    env_vars = container.resolve(LanguageModelGatewayEnvironmentVariables)
    repo_manager = container.resolve(GithubConfigRepoManager)
    snapshot_cache = container.resolve(BaseStore)
    try:
        logger.info(f"Starting application initialization for worker {worker_id}...")

        # Open the snapshot cache store (connects to MongoDB if configured,
        # falls back to in-memory silently on connection failure)
        await snapshot_cache.__aenter__()

        # Download GitHub config repo if configured (before first request)
        await repo_manager.start()

        # Ensure the skills directory exists before skill initialization
        # validates it.  The directory lives inside the GitHub config cache
        # which may not contain a configs/skills/ folder yet.
        skills_dir = env_vars.skills_directory
        if skills_dir:
            makedirs(skills_dir, exist_ok=True)

        # Sync shared skills from GitHub/filesystem into MongoDB
        await initialize_skills(
            user_store=container.resolve(UserSkillStore),
            skill_sync=container.resolve(SkillSync),
        )

        logger.info(f"Application initialization completed for worker {worker_id}")
        yield

    except Exception:
        logger.exception("Application initialization failed for worker %s", worker_id)
        raise

    finally:
        try:
            logger.info(f"Starting application shutdown for worker {worker_id}...")
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
