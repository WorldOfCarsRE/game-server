import os
from multiprocessing import Pool

import sys

def runProcess(process):
    os.system(f'{sys.executable} {process}')

def main():
    pool = Pool(processes = 5)
    pool.map(runProcess, ('-m otp.messagedirector', '-m otp.dbserver', '-m otp.stateserver', '-m otp.clientagent', '-m otp.eventlogger'))

if __name__ == '__main__':
    main()
