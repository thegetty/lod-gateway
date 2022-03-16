import logging


class ErrorFilter(logging.Filter):
    # This filters for only log messages that count as errors or critical
    def filter(self, thingy):
        return thingy.levelno in [logging.ERROR, logging.CRITICAL]


def get_logging_config(level="INFO", disable_existing=True):
    return {
        "version": 1,
        "disable_existing_loggers": disable_existing,
        "filters": {"errorfilter": {"()": ErrorFilter}},
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
            }
        },
        "handlers": {
            "stderr_error_only": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
                "formatter": "default",
                "filters": ["errorfilter"],
            },
            "stdout_all": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "default",
            },
        },
        "root": {
            "level": level,
            "handlers": ["stderr_error_only", "stdout_all"],
            "propagate": True,
        },
    }
