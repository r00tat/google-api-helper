""" Google compute engine API """

import logging
import json
import inspect
import os
import time

import google.auth

from googleapiclient import errors
from googleapiclient.discovery import build, DISCOVERY_URI
from googleapiclient.discovery_cache.base import Cache
from google.oauth2 import service_account
from .oauth2 import authorize_application


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
        for member in inspect.getmembers(self, lambda a: not (inspect.isroutine(a))):
            if not member[0].startswith("_"):
                arguments[member[0]] = kwargs.get(member[0], member[1])
        return GoogleApi(**arguments)

    @property
    def service(self):
        """get or create a api service"""
        if self._service is None:
            self._service = build(self.api,
                                  self.api_version,
                                  credentials=self.credentials,
                                  discoveryServiceUrl=self.discovery_url,
                                  cache=program_memory_cache)

        return self._service

    def with_service_account_file(self, service_account_file, sub=None):
        """use service account credentials"""
        credentials = service_account.Credentials.from_service_account_file(service_account_file)
        if self.scopes:
            credentials = credentials.with_scopes(self.scopes)
        if sub:
            credentials = credentials.with_subject(sub)

        self.credentials = credentials
        self._service = None
        self.sub = sub
        return self

    def with_service_account(self, service_account, sub=None):
        """use service account credentials"""
        credentials = service_account.Credentials.from_service_account_info(service_account)
        if self.scopes:
            credentials = credentials.with_scopes(self.scopes)
        if sub:
            credentials = credentials.with_subject(sub)

        self.credentials = credentials
        self.sub = sub
        self._service = None
        return self

    def with_oauth2_flow(self, client_secret_file, local_webserver=False, **kwargs):
        """try to get credentials from oauth2 flow"""
        self.credential_cache_file = kwargs.get("credential_cache_file",
                                                self.credential_cache_file)
        flow_params = kwargs.get("flow_params", [])
        if self.credential_cache_file is None:
            self.credential_cache_file = u"credential_cache_{}_{}_{}.json".format(
                self.api, self.api_version, self.sub)

        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir)

        if not local_webserver:
            flow_params.append('--noauth_local_webserver')

        self.credentials = authorize_application(client_secret_file,
                                                 self.scopes,
                                                 credential_cache_file=os.path.join(
                                                     self.cache_dir, self.credential_cache_file),
                                                 flow_params=flow_params)
        self._service = None
        return self

    def clear_cache(self):
        """
        remove cache file

        @returns GoogleApi self
        """
        if self.credential_cache_file is None:
            self.credential_cache_file = u"credential_cache_{}_{}_{}.json".format(
                self.api, self.api_version, self.sub)
        cache_file = os.path.join(self.cache_dir, self.credential_cache_file)
        if os.path.isfile(cache_file):
            os.remove(cache_file)
        return self

    def with_application_credentials(self):
        """ use GCE or GAE default credentials"""
        credentials, _ = google.auth.default()

        self.credentials = credentials
        self._service = None
        return self

    def delegate(self, sub):
        """ create a credential delegation"""
        if not hasattr(self.credentials, 'create_delegated'):
            raise RuntimeError(("I do not know how to delegate the credentials, ",
                                "create_delegated method is missing on credentials"))

        credentials = self.credentials.create_delegated(sub)
        return self.clone(credentials=credentials)

    def scoped(self, scopes):
        """
        update scopes of GoogleApi
        this also invalidates the service and credentials

        @param scopes scopes used to fetch credentials
        """
        self.scopes = scopes
        self.credentials = None
        self.service = None
        return self

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
            except:  # noqa
                pass

            if code == 403 and "rate limit exceeded" in message.lower():
                self.log.info("rate limit reached, sleeping for %s seconds", 2**retry_count)
                time.sleep(2**retry_count)
                ret = self.retry(service_method, retry_count + 1)
            else:
                self.log.warn("got http error {} ({}): {}".format(code, reason, message))
                raise
        except KeyboardInterrupt:
            raise
        except:  # noqa
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
    def compute(cls, version="v1"):
        """compute v1 api"""
        return GoogleApi("compute", version, ["https://www.googleapis.com/auth/compute"])

    @classmethod
    def drive(cls, version="v3"):
        """drive v3 api"""
        return GoogleApi("drive", version, ["https://www.googleapis.com/auth/drive"])

    @classmethod
    def admin_sdk(cls):
        """Admin SDK v1"""
        return GoogleApi("admin", "directory_v1",
                         ["https://www.googleapis.com/auth/admin.directory.user"])

    @classmethod
    def gmail(cls, version="v1"):
        """Gmail v1"""
        return GoogleApi("gmail", version, ["https://mail.google.com/"])

    @classmethod
    def calendar(cls, version="v3"):
        """calendar v3"""
        return GoogleApi("calendar", version, ["https://www.googleapis.com/auth/calendar"])

    @classmethod
    def reseller(cls, version="v1"):
        """reseller v1"""
        return GoogleApi("reseller", version, ["https://www.googleapis.com/auth/apps.order"])

    @classmethod
    def licensing(cls, version="v1"):
        """license v1"""
        return GoogleApi("licensing", version, ["https://www.googleapis.com/auth/apps.licensing"])

    @classmethod
    def appengine(cls, version="v1"):
        """analytics v3"""
        return GoogleApi("appengine", version, ["https://www.googleapis.com/auth/cloud-platform"])

    @classmethod
    def scripts(cls, version="v1"):
        """scripts v1"""
        return GoogleApi("scripts", version, ["https://www.googleapis.com/auth/userinfo.email"])

    @classmethod
    def cloudbilling(cls, version="v1"):
        """cloudbilling v1"""
        return GoogleApi("cloudbilling", version,
                         ["https://www.googleapis.com/auth/cloud-billing"])

    @classmethod
    def cloudbuild(cls, version="v1"):
        """cloudbuild v1"""
        return GoogleApi("cloudbuild", version, ["https://www.googleapis.com/auth/cloud-platform"])

    @classmethod
    def dns(cls, version="v1"):
        """dns v1"""
        return GoogleApi("dns", version,
                         ["https://www.googleapis.com/auth/ndev.clouddns.readwrite"])

    @classmethod
    def deploymentmanager(cls, version="v2"):
        """deploymentmanager v2"""
        return GoogleApi("deploymentmanager", version,
                         ["https://www.googleapis.com/auth/cloud-platform"])

    @classmethod
    def cloudfunctions(cls, version="v1beta2"):
        """cloudfunctions v1beta2"""
        return GoogleApi("cloudfunctions", version,
                         ["https://www.googleapis.com/auth/cloudfunctions"])

    @classmethod
    def cloudkms(cls, version="v1"):
        """cloudkms v1"""
        return GoogleApi("cloudkms", version, ["https://www.googleapis.com/auth/cloudkms"])

    @classmethod
    def ml(cls, version="v1"):
        """ml v1"""
        return GoogleApi("ml", version, ["https://www.googleapis.com/auth/cloud-platform"])

    @classmethod
    def container(cls, version="v1"):
        """container v1"""
        return GoogleApi("container", version, ["https://www.googleapis.com/auth/cloud-platform"])

    @classmethod
    def iam(cls, version="v1"):
        """iam v1"""
        return GoogleApi("iam", version, ["https://www.googleapis.com/auth/iam"])

    @classmethod
    def oauth(cls, version="v2"):
        """oauth v2"""
        return GoogleApi("oauth", version, [
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile"
        ])

    @classmethod
    def people(cls, version="v1"):
        """people v1"""
        return GoogleApi("people", version,
                         ["email", "profile", "https://www.googleapis.com/auth/contacts"])

    @classmethod
    def sheets(cls, version="v4"):
        """sheets v4"""
        return GoogleApi("sheets", version, ["https://www.googleapis.com/auth/spreadsheets"])

    @classmethod
    def slides(cls, version="v1"):
        """slides v1"""
        return GoogleApi("slides", version, ["https://www.googleapis.com/auth/presentations"])

    @classmethod
    def plus(cls, version="v1"):
        """plus v1"""
        return GoogleApi("plus", version, ["email", "profile"])

    @classmethod
    def groupssettings(cls, version="v1"):
        """groupssettings v1"""
        return GoogleApi("groupssettings", version,
                         ["https://www.googleapis.com/auth/apps.groups.settings"])

    @classmethod
    def tasks(cls, version="v1"):
        """tasks v1"""
        return GoogleApi("tasks", version, ["https://www.googleapis.com/auth/tasks"])

    @classmethod
    def urlshortener(cls, version="v1"):
        """urlshortener v1"""
        return GoogleApi("urlshortener", version, ["https://www.googleapis.com/auth/urlshortener"])

    @classmethod
    def youtube(cls, version="v3"):
        """youtube v3"""
        return GoogleApi("youtube", version, ["https://www.googleapis.com/auth/youtube"])


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
        i.e. for compute v1 api GoogleApi.service.instances() can be used as Google.instances()
        and will return a MethodHelper instance
        """
        # self.log.info("call %s", self.name)
        return MethodHelper(self.google_api, getattr(self.service, self.name)(*args, **kwargs))

    def list_all(self, return_element="items", *args, **kwargs):
        """
        list all elements of a type
        make sure you got enough memory to receive all elements
        pagination (https://developers.google.com/api-client-library/python/guide/pagination)
        should always be preferred over this helper

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
            err_msg = u"API method {} unknown on {} {}".format(u".".join(self.path + [name]),
                                                               self.google_api.api,
                                                               self.google_api.api_version)
            raise RuntimeError(err_msg)
        return MethodHelper(self.google_api, self.service, name, self.path).call
