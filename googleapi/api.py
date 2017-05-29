""" Google compute engine API """

import logging
import json
import inspect
import os

import httplib2
from googleapiclient import errors
from googleapiclient.discovery import build, DISCOVERY_URI
from googleapiclient.discovery_cache.base import Cache
from oauth2client.client import GoogleCredentials
from oauth2client.service_account import ServiceAccountCredentials
from .oauth2 import authorize_service_account, authorize_service_account_file, authorize_application

class MemoryCache(Cache):
    """ in meory cache """

    def __init__(self):
        """ init cache """
        self.cache = {}

    def get(self, url):
        """ get from caceh """
        self.cache.get(url, None)

    def set(self, url, content):
        """ set cache """
        self.cache[url] = content

program_memory_cache = MemoryCache()


class GoogleApi(object):
    """Google API helper object"""

    def __init__(self, api="oauth2", api_version="v2", scopes=['email'], *args, **kwargs):
        """constructor"""
        self.api = api
        self.api_version = api_version
        self.scopes = scopes
        self.credentials = kwargs.get('credentials')
        self.sub = kwargs.get('sub')
        self._service = None
        self.discovery_url = kwargs.get('discovery_url', DISCOVERY_URI)
        self.retries = kwargs.get('retries', 3)
        self.credential_cache_file = kwargs.get('credential_cache_file')
        self.log = logging.getLogger("GoogleApi")
        self.cache_dir = kwargs.get('cache_dir', ".cache")

    def clone(self, **kwargs):
        """clone this object and overwrite some properties"""
        arguments = {}
        for member in inspect.getmembers(self, lambda a: not(inspect.isroutine(a))):
            if not member[0].startswith("_"):
                arguments[member[0]] = kwargs.get(member[0], member[1])
        return GoogleApi(**arguments)

    @property
    def service(self):
        """get or create a api service"""
        if self._service is None:
            self._service = build(
                self.api, self.api_version,
                credentials=self.credentials,
                discoveryServiceUrl=self.discovery_url,
                cache=program_memory_cache)

        return self._service

    def with_service_account_file(self, service_account_file, sub=None):
        """use service account credentials"""
        self.credentials = authorize_service_account_file(service_account_file, self.scopes, sub)
        return self

    def with_service_account(self, service_account, sub=None):
        """use service account credentials"""
        self.credentials = authorize_service_account(service_account, self.scopes, sub)
        self.sub = sub
        return self

    def with_oauth2_flow(self, client_secret_file, local_webserver=False, **kwargs):
        """try to get credentials from oauth2 flow"""
        self.credential_cache_file = kwargs.get("credential_cache_file", self.credential_cache_file)
        flow_params = kwargs.get("flow_params", [])
        if self.credential_cache_file is None:
            self.credential_cache_file = u"credential_cache_{}_{}_{}.json".format(self.api, self.api_version, self.sub)

        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir)

        if not local_webserver:
            flow_params.append('--noauth_local_webserver')

        self.credentials = authorize_application(
            client_secret_file, self.scopes,
            credential_cache_file=(self.cache_dir + os.path.sep + self.credential_cache_file),
            flow_params=flow_params)
        return self

    def with_application_credentials(self):
        """ use GCE or GAE default credentials"""
        self.credentials = GoogleCredentials.get_application_default()
        return self

    def delegate(self, sub):
        """ create a credential delegation"""
        if not hasattr(self.credentials, 'create_delegated'):
            raise RuntimeError("I do not know how to delegate the credentials, create_delegated method is missing on credentials")

        credentials = self.credentials.create_delegated(sub)
        return self.clone(credentials=credentials)

    def retry(self, service_method, retry_count=0):
        """
        retry a google api call and check for rate limits
        """
        try:
            ret = service_method.execute(num_retries=retry_count)
        except errors.HttpError as error:
            code = error.resp.get('code')

            reason = ''
            message = ''
            try:
                data = json.loads(error.content.decode('utf-8'))
                code = data['error']["code"]
                message = data['error']['message']
                reason = data['error']['errors'][0]['reason']
            except:
                pass

            if code == 403 and message == "Rate Limit Exceeded":
                self.log.info("rate limit reached, sleeping for %s seconds", 2**retry_count)
                time.sleep(2**retry_count)
                ret = self.retry(service_method, retry_count+1)
            else:
                self.log.warn("got http error {} ({}): {}".format(code, reason, message))
                raise
        except KeyboardInterrupt:
            raise
        except:
            self.log.exception("Failed to execute api method")
            raise
        return ret

    def __getattr__(self, name):
        """ get attribute or service wrapper
        :param name: attribute / service name
        :return:
        """
        return getattr(MethodHelper(self, self.service), name)

    @classmethod
    def compute(cls):
        """compute v1 api"""
        return GoogleApi("compute", "v1", scopes=["https://www.googleapis.com/auth/compute"])

    @classmethod
    def drive(cls):
        """drive v1 api"""
        return GoogleApi("drive", "v3", scopes=["https://www.googleapis.com/auth/drive"])

    @classmethod
    def admin_sdk(cls):
        """Admin SDK v1"""
        return GoogleApi("admin", "directory_v1", scopes=["https://www.googleapis.com/auth/admin.directory.user"])


class MethodHelper(object):
    """ helper to streamline api calls"""

    def __init__(self, google_api, service, name=None, path=None):
        """
        create a method helper
        :param google_api GoogleApi instance of api
        :param service Google API service (GoogleApi.service) or method of it
        :param name method name
        :param path API path i.e. for compute: instances.list
        """
        self.google_api = google_api
        self.service = service
        self.name = name
        self.path = path if path is not None else []
        if name is not None:
            self.path.append(name)
        # self.log = logging.getLogger("MethodHelper")
        # self.log.info("constructor %s", name)

    def execute(self, *args, **kwargs):
        """execute service api"""
        # self.log.info("execute %s", self.name)
        return self.google_api.retry(self.service)

    def call(self, *args, **kwargs):
        """
        wrapper for service methods
        this wraps an GoogleApi.service call so the next level can also use helpers
        i.e. for compute v1 api GoogleApi.service.instances() can be used as Google.instances() and will return a MethodHelper instance
        """
        # self.log.info("call %s", self.name)
        return MethodHelper(self.google_api, getattr(self.service, self.name)(*args, **kwargs))

    def list_all(self, return_element="items", *args, **kwargs):
        """
        list all elements of a type
        make sure you got enough memory to receive all elements
        pagination (https://developers.google.com/api-client-library/python/guide/pagination) should always be preferred over this helper

        :param return_element name of the element containing a list of items
        """
        request = self.service.list(**kwargs)
        all_elements = []
        while request is not None:
            elements = self.google_api.retry(request)
            all_elements.extend(elements.get(return_element, []))
            request = self.service.list_next(request, elements)

        return all_elements

    def __getattr__(self, name):
        """ get service method """
        # self.log.info("getattr %s", name)
        if not hasattr(self.service, name):
            err_msg = u"API method {} unknown on {} {}".format(u".".join(self.path + [name]), self.google_api.api, self.google_api.api_version)
            raise RuntimeError(err_msg)
        return MethodHelper(self.google_api, self.service, name, self.path).call
