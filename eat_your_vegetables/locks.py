""" Tools for synchronizing requests and blocks """
import contextlib
import functools
from collections import defaultdict
from multiprocessing import RLock

import os


class LockAnnotation(object):
    """
    Lock provider

    ::

        @celery.task(base=BaseTask)
        @lock('mytask', expires=300, timeout=500)
        def mytask():
            # do something locked

    Inline locks::

        @celery.task(base=BaseTask)
        def say_hello(name):
            with lock.inline('hello_%s' % name):
                return "Hello %s!" % name

    """
    def __init__(self, factory):
        self._factory = factory

    def __call__(self, key, expires=120, timeout=60):
        """ Decorator for synchronizing a request """
        def wrapper(fxn):
            """ Wrapper for the synchronized request handler """
            @functools.wraps(fxn)
            def wrapped(*args, **kwargs):
                """ Acquire lock and call a function """
                with self._factory(key, expires=expires, timeout=timeout):
                    return fxn(*args, **kwargs)
            return wrapped
        return wrapper

    def inline(self, key, expires=120, timeout=60):
        """ Get a lock instance from the factory """
        return self._factory(key, expires=expires, timeout=timeout)


@contextlib.contextmanager
def noop():
    """ A no-op lock """
    yield


@contextlib.contextmanager
def file_lock(filename):
    """ Acquire a lock on a file using ``flock`` """
    import fcntl
    with open(filename, "w") as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_EX)
        yield


class ILockFactory(object):
    """
    Interface for generating locks

    Extend this class to use a different kind of lock for all of the
    synchronization

    Parameters
    ----------
    settings : dict
        The application's settings

    """
    def __init__(self, settings):
        self._settings = settings

    def __call__(self, key, expires, timeout):
        """
        Create a lock unique to the key

        Parameters
        ----------
        key : str
            Unique key to identify the lock to return
        expires : float
            Maximum amount of time the lock may be held
        timeout : float
            Maximum amount of time to wait to acquire the lock before raising
            an exception

        Notes
        -----
        Not all ILockFactory implementations will respect the ``expires``
        and/or ``timeout`` options. Please refer to the implementation for
        details.

        """
        raise NotImplementedError


class DummyLockFactory(ILockFactory):
    """ No locking will occur """
    def __call__(self, key, expires, timeout):
        return noop()


class ProcessLockFactory(ILockFactory):
    """ Generate multiprocessing RLocks """
    def __init__(self, settings):
        super(ProcessLockFactory, self).__init__(settings)
        self._lock = RLock()
        self._locks = defaultdict(RLock)

    def __call__(self, key, expires, timeout):
        with self._lock:
            return self._locks[key]


class FileLockFactory(ILockFactory):
    """
    Generate file-level locks that use ``flock``

    Notes
    =====
    You may specify ``lock_dir`` in the settings file. This directory will
    contain all the files used for locking. It defaults to '/var/run/celery/'

    """
    def __init__(self, settings):
        super(FileLockFactory, self).__init__(settings)
        self._lockdir = self._settings.get('lock_dir',
                                           '/var/run/celery/')
        if not os.path.exists(self._lockdir):
            os.makedirs(self._lockdir)

    def __call__(self, key, expires, timeout):
        return file_lock(os.path.join(self._lockdir, key))


class RedisLockFactory(ILockFactory):
    """
    Use Redis for locking

    Notes
    =====
    Requires ``redis`` and ``retools`` to be installed.

    You must provide ``redis_url`` in the config file. This should be a
    redis connection url. For example::

        redis://username:password@localhost:6379/0

    """
    def __init__(self, settings):
        super(RedisLockFactory, self).__init__(settings)
        from redis import StrictRedis
        url = settings['redis_url']
        self.redis = StrictRedis.from_url(url)

    def __call__(self, key, expires, timeout):
        from retools.lock import Lock
        return Lock(key, expires=expires, timeout=timeout, redis=self.redis)
