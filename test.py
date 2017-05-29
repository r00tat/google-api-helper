""" python tests """
import json
import logging

from argparse import ArgumentParser
from googleapi.api import GoogleApi

def main():
    """ tests """
    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger("test")
    parser = ArgumentParser(description="Test for GoogleApi")
    parser.add_argument("--client-secret", "-c", help="Client secret file", required=True)
    parser.add_argument("--project", "-p", help="GCE project id", required=True)
    parser.add_argument("--zone", "-z", help="GCE project zone", required=True)
    args = parser.parse_args()
    log.info("creating compute api")
    compute_api = GoogleApi.compute().with_oauth2_flow(args.client_secret)
    log.info("listing instances")
    instances = compute_api.retry(compute_api.service.instances().list(project=args.project, zone=args.zone))
    log.info("instances: %s", json.dumps(instances, indent=2))
    instances = compute_api.instances().list(project=args.project, zone=args.zone).execute()
    log.info("instances shortcut: %s", json.dumps(instances, indent=2))
    instances = compute_api.instances().list_all(project=args.project, zone=args.zone)
    log.info("list all: %s", json.dumps(instances, indent=2))


if __name__ == '__main__':
    main()
