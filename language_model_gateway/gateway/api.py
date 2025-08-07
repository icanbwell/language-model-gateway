import logging
import os
from contextlib import asynccontextmanager
from os import makedirs, environ
from pathlib import Path
from typing import AsyncGenerator, Annotated, List, cast

from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, HTTPException
from fastapi.params import Depends
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, RedirectResponse
from starlette.staticfiles import StaticFiles

from language_model_gateway.configs.config_reader.config_reader import ConfigReader
from language_model_gateway.configs.config_schema import ChatModelConfig
from language_model_gateway.gateway.api_container import get_config_reader
from language_model_gateway.gateway.auth.oauth_cache import OAuthCache
from language_model_gateway.gateway.routers.chat_completion_router import (
    ChatCompletionsRouter,
)
from language_model_gateway.gateway.routers.image_generation_router import (
    ImageGenerationRouter,
)
from language_model_gateway.gateway.routers.images_router import ImagesRouter
from language_model_gateway.gateway.routers.models_router import ModelsRouter
from language_model_gateway.gateway.utilities.endpoint_filter import EndpointFilter

# warnings.filterwarnings("ignore", category=LangChainBetaWarning)

logger = logging.getLogger(__name__)

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# disable INFO logging for httpx because it logs every request
logging.getLogger("httpx").setLevel(logging.WARNING)

# disable logging calls to /health endpoint
uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.addFilter(EndpointFilter(path="/health"))

# OIDC PKCE setup
auth_provider_name = os.getenv("AUTH_PROVIDER_NAME")
well_known_url = os.getenv("AUTH_WELL_KNOWN_URI")
client_id = os.getenv("AUTH_CLIENT_ID")
client_secret = os.getenv("AUTH_CLIENT_SECRET")
redirect_uri = os.getenv("AUTH_REDIRECT_URI")
# session_secret = os.getenv("AUTH_SESSION_SECRET")
assert auth_provider_name is not None, (
    "AUTH_PROVIDER_NAME environment variable must be set"
)
assert well_known_url is not None, (
    "AUTH_WELL_KNOWN_URI environment variable must be set"
)
assert client_id is not None, "AUTH_CLIENT_ID environment variable must be set"
assert client_secret is not None, "AUTH_CLIENT_SECRET environment variable must be set"
assert redirect_uri is not None, "AUTH_REDIRECT_URI environment variable must be set"
# assert session_secret is not None, (
#     "AUTH_SESSION_SECRET environment variable must be set"
# )

# https://docs.authlib.org/en/latest/client/frameworks.html#frameworks-clients
cache: OAuthCache = OAuthCache()
oauth = OAuth(cache=cache)
oauth.register(
    name=auth_provider_name,
    client_id=client_id,
    client_secret=client_secret,
    server_metadata_url=well_known_url,
    client_kwargs={"scope": "openid email", "code_challenge_method": "S256"},
)


@asynccontextmanager
async def lifespan(app1: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: This runs when the first request comes in
    worker_id = id(app)
    try:
        # Configure logging
        logger.info(f"Starting application initialization for worker {worker_id}...")

        # perform any startup tasks here

        logger.info(f"Application initialization completed for worker {worker_id}")
        yield

    except Exception as e:
        logger.exception(e, stack_info=True)
        raise

    finally:
        try:
            logger.info(f"Starting application shutdown for worker {worker_id}...")
            # await container.cleanup()
            # Clean up on shutdown
            logger.info("Application shutdown completed")
        except Exception as e:
            logger.exception(e, stack_info=True)
            raise


def create_app() -> FastAPI:
    app1: FastAPI = FastAPI(title="OpenAI-compatible API", lifespan=lifespan)
    app1.include_router(ChatCompletionsRouter().get_router())
    app1.include_router(ModelsRouter().get_router())
    app1.include_router(ImageGenerationRouter().get_router())
    # Mount the static directory
    app1.mount(
        "/static",
        StaticFiles(
            directory="/usr/src/language_model_gateway/language_model_gateway/static"
        ),
        name="static",
    )

    image_generation_path: str = environ["IMAGE_GENERATION_PATH"]

    assert image_generation_path is not None, (
        "IMAGE_GENERATION_PATH environment variable must be set"
    )

    makedirs(image_generation_path, exist_ok=True)
    app1.include_router(
        ImagesRouter(image_generation_path=image_generation_path).get_router()
    )

    # Set up CORS middleware; adjust parameters as needed
    # noinspection PyTypeChecker
    allowed_origins = environ.get("ALLOWED_ORIGINS", "").split(",")
    if not allowed_origins or allowed_origins == [""]:
        allowed_origins = ["*"]  # Allow all origins if not specified
    app1.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # oidc = OIDCAuthPKCE(
    #     well_known_url=well_known_url, client_id=client_id, redirect_uri=redirect_uri
    # )
    # state_code_verifier: Dict[str, Any] = {}

    # use authlib for authentication
    # https://docs.authlib.org/en/v1.6.1/client/frameworks.html#frameworks-clients

    # app.add_middleware(SessionMiddleware, secret_key=session_secret)

    @app1.api_route("/auth/login", methods=["GET"])
    async def login(request: Request) -> RedirectResponse:
        # absolute url for callback
        # we will define it below
        redirect_uri1 = request.url_for("auth")
        client = oauth.create_client(auth_provider_name)
        return cast(
            RedirectResponse, await client.authorize_redirect(request, redirect_uri1)
        )

    @app1.api_route("/auth/callback", methods=["GET"])
    async def auth(request: Request) -> JSONResponse:
        client = oauth.create_client(auth_provider_name)
        token = await client.authorize_access_token(request)
        # user = token["access_token"]
        return JSONResponse(token)

    #
    # @app1.api_route("/login", methods=["GET"])
    # async def login() -> RedirectResponse:
    #     state: str = secrets.token_urlsafe(16)
    #     url: str
    #     code_verifier: str
    #     url, code_verifier = await oidc.get_authorization_url(state)
    #     state_code_verifier[state] = code_verifier
    #     return RedirectResponse(url)
    #
    #
    # @app1.api_route("/callback", methods=["GET"])
    # async def callback(request: Request) -> JSONResponse:
    #     code: str | None = request.query_params.get("code")
    #     state: str | None = request.query_params.get("state")
    #     assert state is not None, "State must be provided in the callback"
    #     code_verifier: str | None = state_code_verifier.pop(state, None)
    #     if not code or not code_verifier:
    #         return JSONResponse({"error": "Missing code or code_verifier"}, status_code=400)
    #     token_response: dict[str, Any] = await oidc.exchange_code(code, code_verifier)
    #     return JSONResponse(token_response)

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
    request: Request, config_reader: Annotated[ConfigReader, Depends(get_config_reader)]
) -> JSONResponse:
    assert config_reader is not None
    assert isinstance(config_reader, ConfigReader)
    await config_reader.clear_cache()
    configs: List[ChatModelConfig] = await config_reader.read_model_configs_async()
    return JSONResponse({"message": "Configuration refreshed", "data": configs})
