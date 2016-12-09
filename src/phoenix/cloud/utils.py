import logging
import threading
import time
from functools import wraps

import phoenix.config as cfg
from phoenix.common import importutils
from phoenix.common import excutils
from phoenix.cloud import exception


LOG = logging.getLogger(__name__)


class wrap_cloud_retry(object):
    """
    Retry cloud api methods
    """

    def __init__(self, retry_interval=0, max_retries=0, inc_retry_interval=0,
                 max_retry_interval=0, retry_on_disconnect=False, retry_on_request=False,
                 exception_checker=lambda exc: False):
        super(wrap_cloud_retry, self).__init__()

        self.cloud_error = ()
        self.exception_checker = exception_checker
        if retry_on_disconnect:
            self.cloud_error += (exception.CloudConnectionError, )
        if retry_on_request:
            self.cloud_error += (exception.RetryRequest, )
        self.retry_interval = retry_interval
        self.max_retries = max_retries
        self.inc_retry_interval = inc_retry_interval
        self.max_retry_interval = max_retry_interval

    def __call__(self, f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            next_interval = self.retry_interval
            remaining = self.max_retries

            while True:
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    with excutils.save_and_reraise_exception() as ectxt:
                        if remaining > 0:
                            ectxt.reraise = not self._is_exception_expected(e)
                            if ectxt.reraise:
                                LOG.exception('Cloud error.')
                        else:
                            LOG.exception('Cloud exceeded retry limit.')
                            if isinstance(e, exception.RetryRequest):
                                ectxt.type_ = type(e.inner_exc)
                                ectxt.value = e.inner_exc
                    LOG.debug("Performing cloud retry for function %s", f)
                    time.sleep(next_interval)
                    if self.inc_retry_interval:
                        next_interval = min(
                            next_interval * 2,
                            self.max_retry_interval
                        )
                    remaining -= 1

        return wrapper

    def _is_exception_expected(self, exc):
        if isinstance(exc, self.cloud_error):
            if not isinstance(exc, exception.RetryRequest):
                LOG.debug('Cloud error: %s', exc)
            return True
        return self.exception_checker(exc)


class CLOUDAPI(object):
    """
    Initialize the chosen cloud API backend.
    """

    def __init__(self, backend_name, backend_mapping=None, lazy=False, **kwargs):

        self._backend = None
        self._backend_name = backend_name
        self._backend_mapping = backend_mapping or {}
        self._lock = threading.Lock()

        if not lazy:
            self._load_backend()

        self.use_cloud_reconnect = kwargs.get('use_cloud_reconnect', False)
        self.retry_interval = kwargs.get('retry_interval', 1)
        self.inc_retry_interval = kwargs.get('inc_retry_interval', True)
        self.max_retry_interval = kwargs.get('max_retry_interval', 10)
        self.max_retries = kwargs.get('max_retries', 20)

    def _load_backend(self):
        with self._lock:
            if not self._backend:
                backend_path = self._backend_mapping.get(self._backend_name, self._backend_name)
                LOG.debug('Loading backend %(name)r from %(path)r', {'name': self._backend_name, 'path': backend_path})
                backend_mod = importutils.import_module(backend_path)
                self._backend = backend_mod.get_backend()

    def __getattr__(self, key):
        if not self._backend:
            self._load_backend()

        attr = getattr(self._backend, key)
        if not hasattr(attr, '__call__'):
            return attr
        retry_on_disconnect = self.use_cloud_reconnect and attr.__dict__.get('enable_retry_on_disconnect', False)
        retry_on_deadlock = attr.__dict__.get('enable_retry_on_deadlock', False)
        retry_on_request = attr.__dict__.get('enable_retry_on_request', False)

        if retry_on_disconnect or retry_on_deadlock or retry_on_request:
            attr = wrap_cloud_retry(
                retry_interval=self.retry_interval,
                max_retries=self.max_retries,
                inc_retry_interval=self.inc_retry_interval,
                max_retry_interval=self.max_retry_interval,
                retry_on_disconnect=retry_on_disconnect,
                retry_on_request=retry_on_request)(attr)

        return attr

    @classmethod
    def from_config(cls, conf, backend_mapping=None, lazy=False):
        """
        Initialize CLOUDAPI instance given a config instance.
        """
        return cls(backend_name=conf.cloud.backend,
                   backend_mapping=backend_mapping,
                   lazy=lazy)
