import logging


class ErrorFilter(logging.Filter):
    # This filters for only log messages that count as errors or critical
    def filter(self, thingy):
        return thingy.levelno in [logging.ERROR, logging.CRITICAL]


def get_logging_config(
    level="INFO", json=False, disable_existing=True, json_access=False
):
    if not json:
        return {
            "version": 1,
            "disable_existing_loggers": disable_existing,
            "filters": {"errorfilter": {"()": ErrorFilter}},
            "formatters": {
                "default": {
                    "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
                },
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
    else:
        base = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "format": "%(asctime)s %(levelname)s %(module)s %(name)s %(message)s",
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                },
            },
            "handlers": {
                "stdout_all": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "json",
                },
            },
            "loggers": {
                "root": {
                    "level": level,
                    "handlers": ["stdout_all"],
                    "propagate": True,
                },
            },
        }
        if json_access is True:
            base["formatters"]["accessjson"] = {
                "format": "%(h)s %(l)s %(u)s %(t)s %(r)s %(s)s %(b)s %(f)s %(a)s %(D)s",
                "()": "flaskapp.GunicornLogFormatter",
            }
            base["handlers"]["accesslog_stdout_all"] = {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "accessjson",
            }
            base["loggers"]["gunicorn.access"] = {
                "level": level,
                "handlers": ["accesslog_stdout_all"],
                "propagate": 0,
            }

        return base
