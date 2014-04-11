Eat Your Vegetables
===================
This is essentially a wrapper framework that makes it easier to organize your
celery tasks.

Adding Tasks
============
Inside your package, create a ``tasks.py`` file (the name isn't important) with
the following::

    from eat_your_vegetables import celery, BaseTask

    @celery.task(base=BaseTask)
    def say_hello(name):
        return "Hello %s!" % name

Then add ``yourextension.tasks`` to the ``CELERY_IMPORTS`` section of the
config.yaml file (see the Configuration section below)

Extensions
==========
Eat Your Vegetables can load extensions.  It imports every module in `include`
list and runs the ``include_tasks`` function from that module. The function
should accept a ``eat_your_vegetables.TaskConfigurator`` as the only argument.

You can use this to add mixins (providing more methods to the tasks), schedule
periodic tasks, or mutate the celery configuration. For example, to schedule a
periodic callback::

    def include_tasks(config):
        config.add_scheduled_task('constant_greeting', {
            'task': 'yourextension.tasks.say_hello',
            'schedule': timedelta(minutes=1),
            'args': ['Monty'],
        })


Configuration
=============
::

    # YAML file for configuring logging (required; see logging.dictConfig)
    logging: <log config dict>

    # YAML file with the celery configuration (required)
    celery = <celery settings>

    # Dotted path to a lock factory implementation. (See eat_your_vegetables.locks)
    lock_factory = none

    # Modules that include an 'include_tasks' function
    include: [list, of, modules]

Running
=======
Eat Your Vegetables provides CLI commands that wrap celery. Just specify the
config file as the first argument, and the rest of the arguments will be passed
on to the celery commands as per usual. There are three commands::

* **nom-worker** - Starts a celery worker
* **nom-beat** - Starts celerybeat 
* **nom-flower** - Starts celery flower (you must ``pip install flower`` first)
