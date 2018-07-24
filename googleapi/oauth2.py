# -*- coding: utf-8 -*-
"""
helper functions for oauth2
"""
import json

from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow


def authorize_service_account(json_credentials, scope, sub=None):
    """
    authorize to the provide scope with a service credentials json file.

    :param json_credentials: dictonary representing a service account,
        in most cases created from json.load
    :param scope: scope(s) to authorize the application for
    :param sub: User ID to authorize the application for (if needed)
    :return Credentials to be used for http object
    """
    credentials = service_account.Credentials.from_service_account_info(json_credentials)
    if scope:
        credentials = credentials.with_scopes(scope)
    if sub:
        credentials = credentials.with_subject(sub)
    return credentials


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


def authorize_application(client_secret_file,
                          scope,
                          credential_cache_file='credentials_cache.json',
                          flow_params=[],
                          local_web_server=False):
    """
    authorize an application to the requested scope by asking the user in a browser.

    :param client_secret_file: json file containing the client secret for an offline application
    :param scope: scope(s) to authorize the application for
    :param credential_cache_file: if provided or not None, the credenials will be cached in a file.
        The user does not need to be reauthenticated
    :param flow_params: oauth2 flow parameters deprecated
    :return OAuth2Credentials object
    """

    flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, scopes=scope)

    if local_web_server or '--auth_local_webserver' in flow_params:
        credentials = flow.run_local_server()
    else:
        credentials = flow.run_console()

    # session = flow.authorized_session()

    return credentials


def oauth2_authorize(client_secret_file=None,
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
