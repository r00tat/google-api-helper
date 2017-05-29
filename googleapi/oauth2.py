# -*- coding: utf-8 -*-
"""
helper functions for oauth2

@author: Paul Woelfel <paul.woelfel@zirrus.eu>
"""
import json

from oauth2client import tools
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
import logging


def authorize_service_account(json_credentials, scope, sub=None):
    """
    authorize to the provide scope with a service credentials json file.

    :param json_credentials: dictonary representing a service account, in most cases created from json.load
    :param scope: scope(s) to authorize the application for
    :param sub: User ID to authorize the application for (if needed)
    :return Credentials to be used for http object
    """
    try:
        from oauth2client.service_account import ServiceAccountCredentials
    except ImportError:
        ServiceAccountCredentials = None

    if ServiceAccountCredentials is not None and hasattr(ServiceAccountCredentials, "from_json_keyfile_dict"):
        # running oauth2client version 2.0
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json_credentials, scope)
        if sub is not None:
            creds = creds.create_delegated(sub)
    else:
        try:
            from oauth2client.client import SignedJwtAssertionCredentials
        except ImportError:
            raise EnvironmentError("Service account can not be used because PyCrypto is not available. Please install PyCrypto.")

        if not isinstance(scope, (list, tuple)):
            scope = [scope]

        creds = SignedJwtAssertionCredentials(
            service_account_name=json_credentials['client_email'],
            private_key=json_credentials['private_key'],
            scope=scope,
            sub=sub)

    return creds


def authorize_service_account_file(json_file_name, scope, sub=None):
    """
    authorize to the provide scope with a service credentials json file.

    :param json_file_name: name of file containing the service account and its private key
    :param scope: scope(s) to authorize the application for
    :param sub: User ID to authorize the application for (if needed)
    :return Credentials to be used for http object
    """
    with open(json_file_name) as json_file:
        json_credentials = json.load(json_file)
    return authorize_service_account(json_credentials, scope, sub)


def authorize_application(client_secret_file, scope, credential_cache_file='credentials_cache.json', flow_params=[]):
    """
    authorize an application to the requested scope by asking the user in a browser.

    :param client_secret_file: json file containing the client secret for an offline application
    :param scope: scope(s) to authorize the application for
    :param credential_cache_file: if provided or not None, the credenials will be cached in a file.
        The user does not need to be reauthenticated
    :param flow_params: oauth2 flow parameters
    :return OAuth2Credentials object
    """
    FLOW = flow_from_clientsecrets(client_secret_file,
                                   scope=scope)

    storage = Storage(credential_cache_file)
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        # Run oauth2 flow with default arguments.
        level = logging.getLogger().level
        credentials = tools.run_flow(FLOW, storage, tools.argparser.parse_args(flow_params))
        logging.getLogger().setLevel(level)

    return credentials


def oauth2_authorize(
        client_secret_file=None,
        service_account_file=None,
        scope=['https://www.googleapis.com/auth/userinfo.email'],
        credential_cache_file='credentials_cache.json',
        sub=None,
        flow_params=[]):
    """
    combine client and service account auth

    :param client_secret_file: json file containing the client secret for an offline application
    :param service_account_file: name of file containing the service account and its private key
    :param scope: scope(s) to authorize the application for
    :param credential_cache_file: if provided or not None, the credenials will be cached in a file.
        The user does not need to be reauthenticated
    :param sub: User ID to authorize the application for (if needed)
    :param flow_params: oauth2 flow parameters
    :return OAuth2Credentials object
    """
    if service_account_file:
        return authorize_service_account_file(service_account_file, scope, sub)
    elif client_secret_file:
        return authorize_application(client_secret_file, scope, credential_cache_file, flow_params)
    else:
        raise RuntimeError("Neither service account file or client secret passed.")
