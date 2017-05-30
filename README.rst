==========================================
google-api-helper Python Google API helper
==========================================

google-api-helper helps streamline access to google apis including authentication using oauth2 and factory methods to create an API service. I.e. creating a compute API service is not to bad but still needs some code:

.. code-block:: python

  import googleapiclient.discovery
  from oauth2client.service_account import ServiceAccountCredentials
  
  credentials = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", ["https://www.googleapis.com/auth/compute"])
  compute = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)

With google-api-helper that's a oneliner:

.. code-block:: python

  from googleapi import GoogleApi
  compute = GoogleApi.compute().with_service_account_file("service_account.json")

also using the OAUTH2 flow is simple

.. code-block:: python

  from googleapi import GoogleApi
  compute = GoogleApi.compute().with_oauth2_flow("client_secret.json")

python-google-api-client also got retries for server errors included, but not for rate limiting. Therefore every API call you make needs to implement an exponential backoff. This is automatically done by using google-api-helper.

.. code-block:: python

  from googleapi import GoogleApi
  compute = GoogleApi.compute().with_oauth2_flow("client_secret.json")
  # directly using the api service without retries
  compute.service.instances().list(project="my-gcp-project", zone="europe-west1-d").execute()
  # wrapper including retries for rate limiting and server side errors 
  compute.instances().list(project="my-gcp-project", zone="europe-west1-d").execute()

Installation
------------

Add `google-api-helper` to your requirements.txt or your module requirements or install via pip:

.. code-block:: bash

  pip install google-api-helper


Quickstart
----------

Import GoogleApi in your python code

.. code-block:: python

  from googleapi import GoogleApi
  
Create the api from a factory method or specify it by yourself:

.. code-block:: python

  compute = GoogleApi.compute()
  drive = GoogleApi.drive()
  gmail = GoogleApi("gmail", "v1", ["https://mail.google.com/"])

Authenticate with oauth2

.. code-block:: python

  # use Compute Engine or App Engine default credentials
  compute.with_application_credentials()
  # use a service account to access a users drive
  drive.with_service_account_file("service_account.json", "test@example.com")
  # or run a oauth2 flow to ask the user for credentials
  gmail.with_oauth2_flow("client_secret.json")


And call the api

.. code-block:: python

  instances = compute.instances().list(project="project-id", zone="europe-west1-d").execute()
  drive_files = drive.files().list(q="name='test'").execute()
  messages = gmail.users().messages().list(userId="me").execute()


Building and publishing
-----------------------

.. code-block:: bash

  python setup.py bdist_wheel --universal
  python -m twine upload dist/*
