import argparse
import logging
import os

import uvicorn

logging.basicConfig(level=logging.INFO)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the FastAPI application with Uvicorn.")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on.")
    parser.add_argument("--port", type=int, default=11111, help="Port to run the server on.")
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Configuration file name (default: config.yaml).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Enable auto-reload for development.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    logging.info(
        f"Starting uvicorn server on {args.host}:{args.port}"
        + (" with auto-reload." if args.reload else ".")
    )
    os.environ["ASTRA_SIMULATORS_CONFIG"] = args.config

    uvicorn.run(
        "observatory_simulator.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
