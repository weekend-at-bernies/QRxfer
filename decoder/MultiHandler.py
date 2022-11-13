import WorkerManager
#import FilePathWrapper
from WorkerManager import WorkerType
from WorkerManager import WorkerStatus
#import Utils
#import shutil
        
#################################################################################################################

class Manager(WorkerManager.WorkerManager):

    def run(self, params_list):

        for params in params_list:
            # Schedule a worker:
            worker = Worker(self, self.worker_manager, params)
            self.scheduleWorker(worker, worker.work) 
                      
        self.startWorkers()

        # All workers complete without error?
        if not self.joinWorkers():
            # FIXME:
            #raise QRCode.FatalDecodeError("fatal error raised")
            return False
        
    # IN: 
    def __init__(self, worker_type, worker_manager):
        # Invoke the super (WorkerManager.Worker) class constructor:
        super(Manager, self).__init__(worker_type)      
        # FIXME: prolly wanna do some type of input sanitisation check.
        self.worker_manager = worker_manager
        
 
#################################################################################################################


class Worker(WorkerManager.Worker):


    # IN: 
    def __init__(self, manager, worker_manager, params):
        # Invoke the super (WorkerManager.Worker) class constructor:
        super(Worker, self).__init__(manager)
        self.worker_manager = worker_manager
        self.params = params 
        


    def work(self, rtargs=None):
        self.prework()

        # FIXME: get status 
        try:
            self.worker_manager.run(self.params)
            status = WorkerStatus.completed_success
        except:
            status = WorkerStatus.completed_fatal_error
       
       
        # Finish work:   
        self.postwork(status)

