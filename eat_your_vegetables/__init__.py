""" Organizational tool for celery """
import os
import six
import re

import importlib
import logging.config
import yaml
from celery import Celery, Task
from celery.datastructures import ExceptionInfo
from celery.states import SUCCESS, FAILURE
import pkg_resources

from . import locks

__version__ = '0.0.0'


class ImportWarningClass(object):

    """ Dummy class that raises exceptions if called before replaced """

    def __call__(self, *_, **__):
        raise ValueError("You must set up eat_your_vegetables before "
                         "importing any files that contain tasks")

    def __getattribute__(self, name):
        return self

# pylint: disable=C0103

lock = ImportWarningClass()
celery = ImportWarningClass()


def walk(data, callback):
    """ Walk a dictionary and replace values """
    for key, value in data.items():
        if isinstance(value, dict):
            walk(value, callback)
        else:
            data[key] = callback(value)


def read_config(conf_file):
    """ Read conf file and return a :class:`TaskConfigurator` """
    if isinstance(conf_file, dict):
        settings = conf_file
    else:
        with open(conf_file, 'r') as infile:
            settings = yaml.safe_load(infile)
        here = os.path.dirname(os.path.abspath(conf_file))

        def add_vars(value):
            """ Inject string formatted variables into config """
            if isinstance(value, six.string_types):
                return value.format(here=here)
            else:
                return value
        walk(settings, add_vars)

    return TaskConfigurator(settings)


class BaseTaskShell(Task):  # pylint: disable=W0223

    """ Base class for tasks """
    abstract = True
    config = None
    callbacks = []

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        for callback in self.callbacks:
            callback(self, status, retval, task_id, args, kwargs, einfo)

    def __call__(self, *args, **kwargs):
        einfo = None
        status = SUCCESS
        try:
            retval = super(BaseTaskShell, self).__call__(*args, **kwargs)
            self.after_return(status, retval, 0, args, kwargs, einfo)
            return retval
        except Exception as e:
            retval = e
            import sys
            status = FAILURE
            einfo = ExceptionInfo(sys.exc_info())
            self.after_return(status, retval, 0, args, kwargs, einfo)
            raise


class BaseTask(BaseTaskShell):  # pylint: disable=W0223

    """
    Dummy class that will be replaced by a class with additional mixed-in
    methods

    """


class Registry(object):

    """ Simple container object for getting/setting attributes """

    def __init__(self, settings):
        self.settings = settings


class TaskConfigurator(object):

    """
    Config object that wraps all configuration data

    Parameters
    ----------
    settings : dict
        Settings from the config.yaml file

    Attributes
    ----------
    settings : dict
    mixins : list
        List of objects that will be mixed-in to the base BaseTask object.
    registry : object
        Mostly-empty object that exists to get/set attributes onto.
    after_setup : list
        List of callbacks that will be called after celery is set up

    """

    def __init__(self, settings):
        self.settings = settings
        self.settings.setdefault('celery', {})
        self.mixins = []
        self.registry = Registry(settings)
        self.after_setup = []

    def add_scheduled_task(self, name, config_dict):
        """
        Add a task for periodic execution

        Parameters
        ----------
        name : str
            Unique name of the periodic task
        config_dict : dict
            Same format as the Celery CELERYBEAT_SCHEDULE entries

        """
        self.settings['celery'].setdefault('CELERYBEAT_SCHEDULE',
                                           {})[name] = config_dict

    def finish(self):
        """ Called after all global celery objects have been created """
        for callback in self.after_setup:
            callback()


def init_celery(conf_file):
    """ Initialize the global celery app objects """
    # pylint: disable=W0603
    global celery
    global BaseTask  # pylint: disable=W0601
    global lock

    config = read_config(conf_file)

    # configure logging
    log_config = config.settings.get('logging', None)
    if log_config is not None:
        logging.config.dictConfig(log_config)

    for package in config.settings.get('include', []):
        mod = importlib.import_module(package)
        mod.include_tasks(config)

    BaseTask = type('BaseTask', tuple(config.mixins + [BaseTaskShell]),
                    {'abstract': True, 'config': config})

    factory_name = config.settings.get('lock_factory', 'none')
    if factory_name == 'none':
        factory_name = 'eat_your_vegetables.locks:DummyLockFactory'
    elif factory_name == 'proc':
        factory_name = 'eat_your_vegetables.locks:ProcessLockFactory'
    elif factory_name == 'file':
        factory_name = 'eat_your_vegetables.locks:FileLockFactory'
    factory = pkg_resources.EntryPoint.parse(
        'x=' + factory_name).load(False)(config.settings)
    lock = locks.LockAnnotation(factory)

    celery = Celery(__package__, config_source=config.settings['celery'])

    config.finish()
    return config


def worker():
    """ Start running the celery worker """
    import sys
    if len(sys.argv) < 2:
        print "usage: %s config.yaml [celery opts]" % sys.argv[0]
        sys.exit(1)

    init_celery(sys.argv.pop(1))

    celery.worker_main()


def beat():
    """ Start running celerybeat """
    import sys
    from celery.utils.imports import instantiate
    if len(sys.argv) < 2:
        print "usage: %s config.yaml [celery opts]" % sys.argv[0]
        sys.exit(1)

    init_celery(sys.argv.pop(1))

    try:
        instantiate(
            'celery.bin.celerybeat:BeatCommand',
            app=celery).execute_from_commandline(sys.argv)
    except ImportError:
        instantiate(
            'celery.bin.beat:beat',
            app=celery).execute_from_commandline(sys.argv)


def flower():
    """ Start running flower """
    import sys
    from flower.command import FlowerCommand
    if len(sys.argv) < 2:
        print "usage: %s config.yaml [flower opts]" % sys.argv[0]
        sys.exit(1)

    init_celery(sys.argv.pop(1))

    cmd = FlowerCommand(celery)
    cmd.run_from_argv([sys.argv[0]], sys.argv[1:])
