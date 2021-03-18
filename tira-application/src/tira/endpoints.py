import asyncio
import grpc
from grpc import aio
from google.protobuf.empty_pb2 import Empty
from google.protobuf.json_format import MessageToDict
from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404, JsonResponse
from itertools import groupby
from django.conf import settings
import uuid
from http import HTTPStatus

from .grpc_client import GrpcClient
from .tira_model import FileDatabase
from .authentication import Authentication
from .forms import LoginForm
from django import forms
from django.core.exceptions import PermissionDenied

from .proto import tira_host_pb2
from .proto import tira_host_pb2_grpc


model = FileDatabase()
include_navigation = True if settings.DEPLOYMENT == "legacy" else False
auth = Authentication(authentication_source=settings.DEPLOYMENT,
                      users_file=settings.LEGACY_USER_FILE)

def bulk_vm_create(request, vm_list):
    """
    1. generate bulkCommandId
    1. iterate over the list of vms to be created
    2. for each vm execute grpc_client.vm-create
    3. return response bulkCommandId
    """

    bulk_id = uuid.uuid4().hex
    for host, vm_id, ova_id in vm_list:
        vm_create(request, host, vm_id, ova_id, bulk_id=bulk_id)

    return JsonResponse({'status': 'Accepted', 'message': {'bulkCommandId': bulk_id}}, status=HTTPStatus.ACCEPTED)


def get_bulk_command_status(bulk_id):
    commands = model.get_commands_bulk(bulk_id)
    return JsonResponse({'status': 'OK', 'message': {'commands': commands}}, status=HTTPStatus.OK)


def command_status(request, command_id):
    command = model.get_command(command_id)
    if not command:
        return JsonResponse({"status": 'NOT_FOUND'}, status=HTTPStatus.NOT_FOUND)

    return JsonResponse({"status": 'OK', 'message': {'command': MessageToDict(command)}}, status=HTTPStatus.OK)


def vm_create(request, hostname, user_id, ova_file, bulk_id=None):
    grpc_client = GrpcClient(hostname)
    response = grpc_client.vm_create(ova_file, user_id, bulk_id)
    return JsonResponse({'status': 'Accepted', 'message': response}, status=HTTPStatus.ACCEPTED)


def vm_start(request, user_id, vm_id):
    vm = model.get_vm_by_id(user_id)
    grpc_client = GrpcClient(vm.host)
    response = grpc_client.vm_start(vm.vmName)
    return JsonResponse({'status': 'Accepted', 'message': response}, status=HTTPStatus.ACCEPTED)


def vm_stop(request, user_id, vm_id):
    vm = model.get_vm_by_id(user_id)
    grpc_client = GrpcClient(vm.host)
    response = grpc_client.vm_stop(vm.vmName)
    return JsonResponse({'status': 'Accepted', 'message': response}, status=HTTPStatus.ACCEPTED)


def run_execute(request, user_id, vm_id):
    vm = model.get_vm_by_id(user_id)
    grpc_client = GrpcClient(vm.host)
    response = grpc_client.run_execute(submission_file="",
                                       input_dataset_name="",
                                       input_run_path="",
                                       output_dir_name="",
                                       sandboxed="",
                                       optional_parameters="")
    return JsonResponse({'status': 'Accepted', 'message': response}, status=HTTPStatus.ACCEPTED)


def run_eval(request, user_id, vm_id):
    vm = model.get_vm_by_id(user_id)
    grpc_client = GrpcClient(vm.host)
    response = grpc_client.run_execute(submission_file="",
                                       input_dataset_name="",
                                       input_run_path="",
                                       output_dir_name="",
                                       sandboxed="",
                                       optional_parameters="")
    return JsonResponse({'status': 'Accepted', 'message': response}, status=HTTPStatus.ACCEPTED)