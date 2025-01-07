import multiprocessing as mp
from rooplppEval import evalExp ,getAssignmentResult, printMU
import time
import sys


def storeCycle(q, globalMu):
    global m
    m = mp.Manager()


    while(True):
        if q.qsize() != 0:
            request = q.get()
            if(len(request) == 4):
                # assignment request
                Gamma      = request[0]
                statement  = request[1]
                invert     = request[2]
                child_conn = request[3]


                if (statement[1] == '<=>'):
                    if (type(statement[2]) != list and type(statement[3]) != list):

                        leftAddr = Gamma[statement[2]] #x
                        rightAddr = Gamma[statement[3]] #y
                        leftContent = globalMu[leftAddr]
                        rightContent = globalMu[rightAddr]

                        leftContentVal = leftContent.val
                        rightContentVal = rightContent.val
                        leftContent.val = rightContentVal
                        rightContent.val = leftContentVal

                        globalMu[leftAddr] = leftContent
                        globalMu[rightAddr] = rightContent

                    if (type(statement[2]) == list and type(statement[3]) != list):


                        listAddr = globalMu[Gamma[statement[2][0]]].val
                        leftList = globalMu[listAddr]
                        listIndex= evalExp(Gamma, globalMu, statement[2][1])
                        leftContentVal = leftList[listIndex].val

                        rightAddr = Gamma[statement[3]]
                        rightContentVal = evalExp(Gamma, globalMu, statement[3])

                        leftList[listIndex].val = rightContentVal
                        globalMu[listAddr] = leftList

                        rightContent = globalMu[rightAddr]
                        rightContent.val = leftContentVal
                        globalMu[rightAddr] = rightContent

                    if (type(statement[2]) != list and type(statement[3]) == list):

                        listAddr = globalMu[Gamma[statement[3][0]]].val
                        rightList = globalMu[listAddr]
                        listIndex= evalExp(Gamma, globalMu, statement[3][1])
                        rightContentVal = rightList[listIndex].val

                        leftAddr = Gamma[statement[2]]
                        leftContentVal = evalExp(Gamma, globalMu, statement[2])

                        rightList[listIndex].val = leftContentVal
                        globalMu[listAddr] = rightList

                        leftContent = globalMu[leftAddr]
                        leftContent.val = rightContentVal
                        globalMu[leftAddr] = leftContent

                    if (type(statement[2]) == list and type(statement[3]) == list):


                        RlistAddr = globalMu[Gamma[statement[3][0]]].val
                        rightList = globalMu[RlistAddr]
                        RlistIndex= evalExp(Gamma, globalMu, statement[3][1])
                        rightContentVal = rightList[RlistIndex].val

                        LlistAddr = globalMu[Gamma[statement[2][0]]].val
                        leftList = globalMu[LlistAddr]
                        LlistIndex= evalExp(Gamma, globalMu, statement[2][1])
                        leftContentVal = leftList[LlistIndex].val
                        
                        if(RlistAddr != LlistAddr):
                            leftList[LlistIndex].val = rightContentVal
                            rightList[RlistIndex].val = leftContentVal

                            globalMu[LlistAddr] = leftList
                            globalMu[RlistAddr] = rightList
                        else:
                            leftList[LlistIndex].val = rightContentVal
                            leftList[RlistIndex].val = leftContentVal

                            globalMu[LlistAddr] = leftList

                else:
                    if isinstance(statement[2], list):
                        # left is list
                        var = statement[2]
                        index = evalExp(Gamma,globalMu,statement[2][1])
                        addr = Gamma[var[0]]
                        left = globalMu[globalMu[addr].val][index].val
                    else:
                        var = statement[2]
                        addr = Gamma[var]
                        left = globalMu[addr].val

                    if isinstance(statement[3], list):
                        if len(statement[3]) == 3 or len(statement[3]) == 1:
                            right = evalExp(Gamma,globalMu,statement[3])
                        elif len(statement[3]) == 2:
                            index = evalExp(Gamma,globalMu,statement[3][1])
                            addr = Gamma[statement[3][0]]
                            right = globalMu[globalMu[addr].val][index].val
                        else:
                            raise Exception("Invalid assignment right expression")
                    else:
                        right = evalExp(Gamma, globalMu, statement[3])

                    val = getAssignmentResult(statement[1], invert, left, right)

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

            elif(len(request) == 2):
                request[1].send('ready_delete')
                break
    #print('store loop has exited')



def makeMuManager(globalMu, m):

    # print("making Store")
    q = m.Queue()

    globalMu[-2] = q
    p = mp.Process(target =  storeCycle, args = (q, globalMu))

    time.sleep(sys.float_info.min)
    p.start()
    
    return p
