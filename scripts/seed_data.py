import structlog
logger = structlog.get_logger(__name__)


def main() -> None:
    logger.info("Seed-data scaffold. Add sample session generation here.")


if __name__ == "__main__":
    main()
