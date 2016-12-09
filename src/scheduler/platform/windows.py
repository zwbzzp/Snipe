# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Windows service based worker
#
# 2016/2/17 fengyc : Init

import win32serviceutil
import win32service
import win32event


class WindowsService(win32serviceutil.ServiceFramework):

    _svc_name_ = "VinzorService"
    _svc_display_name_ = "VinzorService"
    _svc_description_ = "Vinzor Service for Python Apps"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        # Create an event which we will use to wait on.
        # The "service stop" request will set this event.
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        # Before we do anything, tell the SCM we are starting the stop process.
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

        # And set my event.
        win32event.SetEvent(self.hWaitStop)

        # Now stop the app
        self.stop()

    def SvcDoRun(self):
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

    def run(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(WindowsService)


