from __future__ import division, absolute_import, print_function, unicode_literals

import atexit
import datetime
import functools
import logging
import os
import sys
from dataclasses import dataclass
from typing import Dict


def int_env_var(s: str, i: int) -> int:
    try:
        return int(os.environ[s])
    except (ValueError, TypeError, KeyError) as e:
        if s in os.environ:
            print(f'Error parsing environment variable {s}, which its value is {os.environ[s]}')
            print(e)
        return i


def str_int_dict_env_var(s: str) -> Dict[str, int]:
    try:
        return {eq.split('=')[0]: int(eq.split('=')[1]) for eq in os.environ[s].split(',')}
    except Exception as e:
        if s in os.environ:
            print(f'Error parsing environment variable {s}, which its value is {os.environ[s]}')
            print(e)
        return {}


ULTRA_VERBOSE = 'METIS_LOGGER_ULTRA_VERBOSE' in os.environ
MAX_ARG_LEN = int_env_var('METIS_LOGGER_MAX_ARG_LEN', 256)
MAX_CALLS = str_int_dict_env_var('METIS_LOGGER_MAX_CALLS')
MAX_LOGGING_SIZE = int_env_var('METIS_LOGGER_MAX_LOGGING_SIZE', -1)  # If -1 ignore log limit
LOGGING_LEVEL = getattr(logging,
                        os.environ.get('METIS_LOGGER_LEVEL', 'debug').upper(),
                        logging.DEBUG)
SKIP_PARAMS = 'METIS_LOGGER_SKIP_PARAMS' in os.environ
SKIP_RETURN_VALUE = 'METIS_LOGGER_SKIP_RETURN_VALUE' in os.environ
FILENAME = os.environ.get('METIS_LOGGER_FILENAME', None)

logger = logging.getLogger(__name__)

if ULTRA_VERBOSE:
    if FILENAME:
        logging.basicConfig(
            level=LOGGING_LEVEL,
            format="[%(asctime)s.%(msecs)03d] %(levelname)s %(message)s",
            datefmt="%d/%b/%Y %H:%M:%S",
            filename=FILENAME)
    else:
        logging.basicConfig(
            level=LOGGING_LEVEL,
            format="[%(asctime)s.%(msecs)03d] %(levelname)s %(message)s",
            datefmt="%d/%b/%Y %H:%M:%S",
            stream=sys.stdout)


@dataclass
class MethodStats:
    calls: int
    exceptions: int
    total_time: float


method_stats = {}
logging_size = 0


def now() -> float:
    return datetime.datetime.now().timestamp()


def ms_string(ms: float) -> str:
    return f'{int(ms * 1000000) / 1000}ms'


def log(should_throw: bool = False):
    if callable(should_throw):
        return log()(should_throw)

    def _log(func):
        if not ULTRA_VERBOSE:
            return func

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            def _to_string(obj):
                try:
                    return repr(obj)
                except Exception:
                    try:
                        return str(obj)
                    except Exception:
                        return f'{obj.__name__}'

            def to_string(obj):
                res = _to_string(obj)
                return res if len(res) <= MAX_ARG_LEN else f'{res[:MAX_ARG_LEN]}...'

            global logging_size, method_stats

            try:
                skip_logging = False
                func_name = f'{func.__module__}.{func.__name__}'
                if -1 < MAX_LOGGING_SIZE < logging_size:
                    skip_logging = True
                else:
                    if (func_name in MAX_CALLS and
                            func_name in method_stats and
                            method_stats[func_name].calls > MAX_CALLS[func_name]):
                        skip_logging = True

                if func_name not in method_stats:
                    method_stats[func_name] = MethodStats(calls=0, exceptions=0, total_time=0)
                method_stats[func_name].calls += 1
                if not skip_logging:
                    sig = ''
                    if not SKIP_PARAMS:
                        args_repr = [to_string(a) for a in args]
                        kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
                        sig = ", ".join(args_repr + kwargs_repr)
                    call_string = f'{func_name}({sig}) (call #{method_stats[func_name].calls})'
                    message = f'START {call_string}'
                    message_len = len(message) + 1
                    logger.debug(message)
                    logging_size += message_len
                else:
                    call_string = None
                    message_len = 0
                start_time = now()
                value = None
                try:
                    value = func(*args, **kwargs)
                    return value
                except Exception as e:
                    method_stats[func_name].exceptions += 1
                    exception_string = f'Exception raised in {func_name}. Exception: {str(e)}'
                    logger.exception(exception_string)
                    logging_size += len(exception_string) + 1
                    if should_throw:
                        raise e
                finally:
                    if call_string is not None:
                        return_string = (''
                                         if SKIP_RETURN_VALUE or value is None
                                         else f' returned {to_string(value)}')
                        logging_size += message_len + len(return_string)
                        diff = now() - start_time
                        method_stats[func_name].total_time += diff
                        ms = f' [{ms_string(diff)}]' if start_time else ''
                        logger.debug(f'END   {call_string}{return_string}{ms}')
            except Exception as e:
                try:
                    logger.exception(e)
                except Exception as ee:
                    try:
                        print(ee)
                    except Exception:
                        pass

        return wrapper

    return _log


@atexit.register
def log_summary() -> None:
    if not ULTRA_VERBOSE:
        return

    def stats_rank(pair):
        st: MethodStats = pair[1]
        return st.exceptions * 1e9 + st.total_time

    title = f'\n\n   # Calls   | # Exceptions | # Total Time | Method (pid={os.getpid()})\n'
    underline = '-------------+--------------+--------------+'
    max_line = 0
    content = ''
    base = '{:^11}  | {:^11}  | {:^11}  | {}\n'
    pairs = list(method_stats.items())
    for method, stats in sorted(pairs, key=stats_rank, reverse=True):
        line = base.format(stats.calls, stats.exceptions, ms_string(stats.total_time), method)
        max_line = len(line) if len(line) > max_line else max_line
        content += line
    logger.info(title + underline + ('-' * (max_line - len(underline)) + '\n') + content)
