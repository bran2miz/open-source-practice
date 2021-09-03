from django.conf import settings
from concurrent import futures
import grpc
import logging
from .proto import tira_host_pb2, tira_host_pb2_grpc
from .transitions import TransitionLog, EvaluationLog, TransactionLog
from uuid import uuid4

grpc_port = settings.APPLICATION_GRPC_PORT

logger = logging.getLogger("tira")


class TiraApplicationService(tira_host_pb2_grpc.TiraApplicationService):
    def set_state(self, request, context):
        print(f" Application Server received vm-state {request.state} for {request.vmId}")
        # TODO add transition if available
        t = TransitionLog(vm_id=request.vmId, vm_state=request.state)
        t.save()
        response = tira_host_pb2.Transaction()
        response.status = tira_host_pb2.Status.SUCCESS
        t = TransitionLog.objects.get(vm_id=request.vmId)
        print(t.vm_id, t.vm_state)
        return response

    def complete_transaction(self, request, context):
        """ Marks a transaction as completed if the
        This is basically the final stage of a a TIRA message exchange.
        """
        print(f" Application Server received complete_transaction for {request.transactionId}")
        t = TransactionLog.objects.get(transaction_id=request.transactionId)
        t.completed = True
        t.last_status = str(request.status)
        t.last_message = request.message
        t.save()
        response = tira_host_pb2.Transaction()
        response.status = tira_host_pb2.Status.SUCCESS
        response.transactionId = request.transactionId
        return response

    def confirm_vm_create(self, request, context):
        """ This gets called if a vm was successfully created. Right now it just says 'yes' when called.
        See tira_host.proto for request specification.
        TODO this should add the new VM to the model in the future.
        """
        print(f" Application Server received vm-create confirmation with \n"
              f"{request.vmID}, {request.userName}, {request.initialUserPw}, {request.ip}, {request.sshPort}, "
              f"{request.rdpPort}")
        response = tira_host_pb2.Transaction()
        response.status = tira_host_pb2.Status.SUCCESS
        response.transactionId = request.transactionId
        return response

    def confirm_vm_delete(self, request, context):
        """ This gets called if a run_eval finishes and receives the EvaluationResults.
        Right now it just says 'yes' when called. See tira_host.proto for request specification.
        TODO this should remove the deleted vm from.
        """
        print(f" Application Server received vm_delete confirmation with: \n"
              f"{request.vmId.vmId} measures.")

        response = tira_host_pb2.Transaction()
        response.status = tira_host_pb2.Status.SUCCESS
        response.transactionId = request.transactionId
        return response

    def confirm_run_eval(self, request, context):
        """ This gets called if a run_eval finishes and receives the EvaluationResults.
        Right now it just says 'yes' when called. See tira_host.proto for request specification.
        TODO implement
        """
        print(f" Application Server received run-eval confirmation with: \n"
              f"{request.runId.runId} and {len(request.measures)} measures.")
        t = EvaluationLog.objects.get(vm_id=request.runId.vmId, run_id=request.runId.runId)
        t.delete()
        t = TransactionLog.objects.get(transaction_id=request.transaction.transactionId)
        t.completed = False
        t.last_status = str(request.transaction.status)
        t.last_message = request.transaction.message
        t.save()

        response = tira_host_pb2.Transaction()
        response.status = tira_host_pb2.Status.SUCCESS
        response.transactionId = request.transaction.transactionId
        return response


def serve(port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    tira_host_pb2_grpc.add_TiraApplicationServiceServicer_to_server(TiraApplicationService(), server)
    listen_addr = f'[::]:{port}'
    server.add_insecure_port(listen_addr)
    server.start()
    logger.info("Starting tira-application server on %s", listen_addr)
    print("Starting tira-application server on ", listen_addr)
    return server


s = serve(grpc_port)
