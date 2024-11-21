import multiprocessing as mp
from rooplppEval import evalExp 
import time
import sys


def storeCycle(q, globalMu):
    global m
    m = mp.Manager()


    while(True):
        
        if q.qsize() != 0:
            request = q.get()
            if(len(request) == 4):
                Gamma      = request[0]
                var        = request[1]
                val        = request[2]
                child_conn = request[3]

                if isinstance(var, list):
                    listAddress = globalMu[Gamma[var[0]]].val
                    writtenList = globalMu[listAddress]
                    index = evalExp(Gamma, globalMu, var[1])
                    v = writtenList[index]
                    v.val = val
                    writtenList[index] = v 
                    globalMu[listAddress] = writtenList
                else:
                    v =  globalMu[Gamma[var]]
                    v.val =  val
                    globalMu[Gamma[var]] = v

                child_conn.send('wrote')



def makeMuManager(globalMu, m):

    # print("making Store")
    q = m.Queue()

    globalMu[-2] = q
    print(globalMu)
    p = mp.Process(target =  storeCycle, args = (q, globalMu))

    time.sleep(sys.float_info.min)
    p.start()
    
    return p
