Eat Your Vegetables
===================
This is a wrapper framework that makes it easier to organize your celery tasks.
The include system is heavily influenced by `Pyramid
<http://www.pylonsproject.org/>`_.

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
Eat Your Vegetables can load extensions.  It imports every module in the
``include`` list and runs the ``include_tasks`` function from that module. The
function should accept a ``eat_your_vegetables.TaskConfigurator`` as the only
argument.

You can use this to add mixins (providing more methods to the tasks), schedule
periodic tasks, or mutate the celery configuration. For example, to schedule a
periodic callback::

    def include_tasks(config):
        config.add_scheduled_task('constant_greeting', {
            'task': 'yourextension.tasks.say_hello',
            'schedule': timedelta(minutes=1),
            'args': ['Monty'],
        })

You can also add mixins during the configure step. Mixins will provide
additional methods to the tasks. Here is a mixin that provides a method to
render jinja2 templates. Note that you would have to set
``config.registry.jinja2_env`` in the ``include_tasks`` function::

    class JinjaRenderMixin(object):

        def render(self, template, **kwargs):
            """ Render a jinja2 template """
            env = self.config.registry.jinja2_env
            tmpl = env.get_template(template)
            return tmpl.render(**kwargs)

And another mixin that provides a SQLAlchemy session::

    from sqlalchemy import engine_from_config

    class DatabaseTaskMixin(object):
        _sessionmaker = None
        _db = None

        @property
        def db(self):
            # Lazily create the sessionmaker and the session
            if self._sessionmaker is None:
                engine = engine_from_config(self.config.settings,
                                            prefix='sqlalchemy.')
                self._sessionmaker = sessionmaker(bind=engine)
            if self._db is None:
                self._db = self._sessionmaker()

                def cleanup(task, status, retval, task_id, args, kwargs, einfo):
                    if einfo is None:
                        task.db.commit()
                    else:
                        task.db.rollback()
                self.callbacks.append(cleanup)
            return self._db

Configuration
=============
::

    # Dict for configuring logging (required; see logging.dictConfig)
    logging:
      version: 1
      formatters:
        simple:
          format: '%(levelname)s %(asctime)s [%(name)s] %(message)s'
      root:
        handlers:
          - console
        level: INFO
      loggers:
        eat_your_vegetables:
          handlers:
            - console
          level: INFO
          propagate: false
      handlers:
        console
          class: StreamHandler
          formatter: simple

    # Dict with the celery configuration (required)
    celery:
      CELERY_TASK_SERIALIZER: json
      CELERY_ACCEPT_CONTENT:
        - json
      CELERY_RESULT_SERIALIZER: json
      CELERY_RESULT_BACKEND: database
      CELERY_RESULT_DBURI: sqlite:///{here}/celery_results.sqlite
      BROKER_URL: sqla+sqlite:///{here}/celery_broker.sqlite
      CELERY_IMPORTS: []

    # Dotted path to a lock factory implementation. (See eat_your_vegetables.locks)
    lock_factory = none

    # Modules that include an 'include_tasks' function
    include:
      - mypackage.tasks
      - mypackage2.tasks

Running
=======
Eat Your Vegetables provides CLI commands that wrap celery. Just specify the
config file as the first argument, and the rest of the arguments will be passed
on to the celery commands as per usual. There are three commands:

* **nom-worker** - Starts a celery worker
* **nom-beat** - Starts celerybeat 
* **nom-flower** - Starts celery flower (you must ``pip install flower`` first)

From your webserver or anywhere else, call
``eat_your_vegetables.init_celery(yaml_file, configure_log=False)``. You will
need to do this before you import any modules with tasks in them.
