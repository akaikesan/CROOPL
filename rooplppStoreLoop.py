import multiprocessing as mp
import time
import sys




def storeCycle(q, globalMu):
    global m
    m = mp.Manager()


    while(True):
        
        print('konnnitiha===')
        if q.qsize() != 0:
            request = q.get()


            if(len(request) == 7):
                pass

        time.sleep(sys.float_info.min)

def makeMuManager(globalMu, m):

    # print("making Store")
    q = m.Queue()

    globalMu[-2] = q
    print(globalMu)
    p = mp.Process(target =  storeCycle, args = (q, globalMu))

    time.sleep(sys.float_info.min)
    p.start()
    
    return p
