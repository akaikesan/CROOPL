import multiprocessing as mp
import time
import sys
import queue

# Storeはfオブジェクトを使いたい場合、{, f:{}, ...} の形でevalStatementに渡す。

class Value:
    val = 0
    ref = 0

    def __init__(self, a, b):
        self.val = a
        self.ref = b

    def countUp(self):
        self.ref += 1

    def countDown(self):
        self.ref -= 1


def printMU(Gamma, MU):
    print(Gamma)
    for k, v in MU.items():
        if type(v) == Value :
            print(k, ':', '(', v.val, ',', v.ref, ')')
        else:
            print(k, ':', v)


def refcountUp(globalMu, addr):
    v = globalMu[addr]
    v.countUp()
    globalMu[addr] = v

def refcountDown(globalMu, addr):
    v = globalMu[addr]
    v.countDown()
    globalMu[addr] = v

def writeMu(Gamma, globalMu, var, val):
    v =  globalMu[Gamma[var]]
    globalMu[Gamma[var]] = Value(val, v.ref)


def getType(t):
    if t[0] == 'separate':
        return t[1]
    else:
        return t[0]


def setNewedObj(classMap, objType, Gamma, globalMu, q):
    fields = classMap[getType(objType)]['fields']
    for f in fields.keys():
        l = len(globalMu.keys())
        Gamma[f] = l
        if fields[f][0] == 'int':
            v = Value(0,1)
            globalMu[l] = v
        elif fields[f][0] == 'list':
            pass
        else:
            print(fields[f])
            globalMu[l] = {'type':fields[f], 'status': 'nil'}

    globalMu[Gamma['this']] = {'methodQ':q, 'type': objType, 'status': 'newed'}
    time.sleep(0.1)

    return



def makeLocalObj(classMap,
                 globalMu,
                 addr
                 ):
    Gamma = {'this' : addr} 
    objType = globalMu[addr]['type']

    setNewedObj(classMap, objType, Gamma, globalMu, None)

    obj = globalMu[addr] 
    obj['gamma'] = Gamma
    globalMu[addr] = obj


 
def makeSeparatedProcess(classMap,
                         globalMu,
                         addr):
    Gamma = {'this' : addr} 
    objType = globalMu[addr]['type']

    global m
    if addr == 0:
        m = mp.Manager()
        q = m.Queue()
    else:
        q = m.Queue()


    setNewedObj(classMap, objType, Gamma, globalMu, q)
   
    p = mp.Process(target = interpreter,
                   args=(classMap,
                         objType,
                         q,
                         Gamma,
                         globalMu))


    p.start()
    time.sleep(0.1)

    return p





def checkVarIsSeparated(globalStore, varName ):
    for v in globalStore.keys():
        if v == varName:
            return True
    return False





def checkObjIsDeletable(varList, env):
    env['type'] = 0
    for k in varList :
        if k == '#q':
            continue
        if  not (env[k] == {} or env[k] == 0):
            raise Exception("you can invert-new or delete only nil-initialized object")





def checkListIsDeletable(list):
    for i in list:
        if i != 0:
            raise Exception("you can invert-new only 0-initialized array")


# this is why Here use proxy ↓
# https://stackoverflow.com/questions/26562287/value-update-in-manager-dict-not-reflected
def updateGlobalStore(globalStore, objName, varName, value):

    q = globalStore['#Store']

    parent_conn, child_conn = mp.Pipe()
    q.put(['update', objName, varName, value, child_conn])

    parent_conn.recv()
    # print('store updated')





def checkNil(object):
    if isinstance(object, int):
        return object
    if len(object) == 0:
        return {}
    elif len(object) == 1:
        if 'type' in object:
            return {}
    else:
        return object





def evalExp(Gamma, globalMu, exp):

    if isinstance(exp, list):
        if len(exp) == 1:
            # [<int>] 
            if isinstance(exp[0], list):
                pass

            else:
                pass

        else:
            if (exp[1] == '+'):
                return evalExp(Gamma, globalMu, exp[0]) + evalExp(Gamma, globalMu, exp[2])
            elif (exp[1] == '-'):
                return evalExp(Gamma, globalMu, exp[0]) - evalExp(Gamma, globalMu, exp[2])

            elif (exp[1] == '/'):
                return evalExp(Gamma, globalMu, exp[0]) / evalExp(Gamma, globalMu, exp[2])
            elif (exp[1] == '*'):
                return evalExp(Gamma, globalMu, exp[0]) * evalExp(Gamma, globalMu, exp[2])
            elif (exp[1] == '='):
                e1 = checkNil(evalExp(thisStore, exp[0]))
                e2 = checkNil(evalExp(thisStore, exp[2]))
                return e1 == e2

            elif (exp[1] == '!='):
                e1 = checkNil(evalExp(thisStore, exp[0]))
                e2 = checkNil(evalExp(thisStore, exp[2]))
                return e1 != e2

            elif (exp[1] == '%'):
                return evalExp(Gamma, globalMu, exp[0]) % evalExp(Gamma, globalMu, exp[2])
            elif (exp[1] == '&'):
                return evalExp(Gamma, globalMu, exp[0]) and evalExp(Gamma, globalMu, exp[2])
            elif (exp[1] == '>'):
                return evalExp(Gamma, globalMu, exp[0]) > evalExp(Gamma, globalMu, exp[2])
            elif (exp[1] == '<='):
                return evalExp(Gamma, globalMu, exp[0]) <= evalExp(Gamma, globalMu, exp[2])
            elif (exp[1] == '>='):
                return evalExp(Gamma, globalMu, exp[0]) >= evalExp(Gamma, globalMu, exp[2])
            elif (exp[1] == '<'):
                return evalExp(Gamma, globalMu, exp[0]) < evalExp(Gamma, globalMu, exp[2])

    elif exp.isdecimal():
        # int (exp[0] is string. turn it to int Here.)
        return int(exp)
    else:
        content = globalMu[Gamma[exp]]
        if type(content) == int:
            return int(content)
        elif type(content) == Value:
            return content.val
        else:
            print(content, 'is not int or Value')
        





def getAssignmentResult(assignment, invert, left, right):
    if (assignment == '^='):
        return left ^ right
    if invert:
        if assignment == '+=':
            return  left - right
        elif assignment == '-=':
            return left + right
    else:
        if assignment == '+=':
            return left + right
        elif assignment == '-=':
            return left - right





def evalStatement(classMap, statement,
                  Gamma,
                  globalMu,
                  invert):

    global ProcessRefCounter
    global ProcessObjName


    if statement is None:
        return
    if (statement[0] == 'assignment'): 
        # p[0] = ['assignment', p[2], p[1], p[3]]
        # ex) x += 2+1 -> ['assignment', +=, x, 2+1]
        if (statement[1] == '<=>'):
            leftAddr = Gamma[statement[2]]
            rightAddr = Gamma[statement[3]]
            leftContent = globalMu[leftAddr]
            rightContent = globalMu[rightAddr]

            leftContentVal = leftContent.val
            rightContentVal = rightContent.val
            leftContent.val = rightContentVal
            rightContent.val = leftContentVal

            globalMu[leftAddr] = leftContent
            globalMu[rightAddr] = rightContent

        else:
            # readMu
            left = 0
            try:
                addr = Gamma[statement[2]]
                left = globalMu[addr].val
            except:
                print(statement[2], 'is not defined in class', '\'' + globalMu[Gamma['this']]['type'] + '\'')

            right = evalExp(Gamma, globalMu, statement[3])

            result = getAssignmentResult(statement[1], invert, left, right)

            # writeMu
            writeMu(Gamma, globalMu, statement[2], result)

    elif (statement[0] == 'print'):
        if statement[1][0] == '"':
            if statement[1] == '""':
                print(statement[1][1:-1])
            return


    elif (statement[0] == 'skip'):
        pass
    elif (statement[0] == 'new'):

        # ['new', className, varName, 'separate']
        # ['new', className, [varName]]

        if isinstance(statement[1], list): 
            pass
        else: 
            # new object
            if (len(statement) == 4):
                if (globalMu[Gamma[statement[2]]]['type'][0] != 'separate' or globalMu[Gamma[statement[2]]]['status'] != 'nil'):
                    print('seprate-type object can\'t be non-separate-newed.')
                    return 'error'

                proc = makeSeparatedProcess(classMap, globalMu,  Gamma[statement[2]])
                global ProcDict
                ProcDict[Gamma[statement[2]]] = proc

            if (len(statement) == 3):

                if (globalMu[Gamma[statement[2]]]['type'][0] == 'separate' or globalMu[Gamma[statement[2]]]['status'] != 'nil'):
                    print('Error : seprate-type object can\'t be non-separate-newed.')
                    return 'error'
                objAddr = makeLocalObj(classMap, globalMu, Gamma[statement[2]])
                Gamma[statement[2]] = objAddr
                
                



    elif (statement[0] == 'delete'):

        if isinstance(statement[1], list): 
            # delete list
            pass

        else: 
            # delete object (not list).
            pass

    elif (statement[0] == 'copy'):
        #['copy', 'Cell', ['cell'], ['cellCopy']]

        pass

    elif (statement[0] == 'call' or statement[0] == 'uncall'):
        # ['call', 'tc', 'test', [args]]
        # ['call', 'test', [args]]

        if len(statement) == 4:  # call method of object
            objAddr       = Gamma['this']
            callOrUncall  = statement[0]
            targetObjAddr = Gamma[statement[1]]
            methodName    = statement[2]

            argsAddr = []

            for varName in statement[3]:
                varAddr = Gamma[varName]
                refcountUp(globalMu, varAddr)
                argsAddr.append(varAddr)

            q = globalMu[targetObjAddr]['methodQ']
            time.sleep(sys.float_info.min)
            q.put([methodName, argsAddr, callOrUncall, objAddr, None])


        elif len(statement) == 3:  # call method of local object

            thisType = globalMu[Gamma['this']]['type']
            statements = classMap[thisType]['methods'][statement[1]]['statements']
            for s in statements:
                evalStatement(classMap, s, Gamma, globalMu, invert)

            


    elif (statement[0] == 'if'):  # statement[1:4] = [e1, s1, s2, e2]
        pass


    elif (statement[0] == 'from'):  # statement[1:4] = [e1, s1, s2, e2]
        pass

    # LOCAL:0 type:1 id:2 EQ exp:3  statements:4 DELOCAL type:5 id:6 EQ exp:7
    elif (statement[0] == 'local'):
        pass

    return 'success'





def interpreter(classMap,
                className,
                q, 
                Gamma,
                globalMu):

    invert = False
    # print("interpreter of " + className + ":"+objName + " start")

    global m
    m = mp.Manager()
    global ProcessObjName
    global ProcessRefCounter
    ProcessRefCounter = 0

    global ProcDict
    ProcDict = {}

    global historyStack
    historyStack = queue.LifoQueue()


    while(True):

        if q.qsize() != 0:
            request = q.get()
            lenReq = len(request)

            if lenReq == 5:

                methodName   = request[0]
                passedArgs   = request[1]
                callORuncall = request[2]
                # if objAddr is 0, this intrprtr is running main func
                objAddr      = request[3] 

                procObjtype = globalMu[Gamma['this']]['type']
                statements = classMap[getType(procObjtype)]['methods'][methodName]['statements']
                funcArgs = classMap[getType(procObjtype)]['methods'][methodName]['args']

                # append args to Gamma

                if (len(passedArgs) == len(funcArgs)):
                    for i in range(len(funcArgs)):
                        Gamma[funcArgs[i]['name']] = passedArgs[i]

                if callORuncall == 'uncall':
                    #check Stack-Emptiness
                    if historyStack.qsize() != 0:
                        historyTop = historyStack.get()
                    else:
                        q.put(request)
                        continue

                    # check correspondency with historyTop
                    if ((request[0])  != historyTop[0] or request[3] != historyTop[3]) or (historyTop[2] != 'call'):
                        q.put(request)
                        continue

                    invert = not invert
                
                # Eval Statements
                for s in statements:
                    result = evalStatement(classMap,
                              s,
                              Gamma,
                              globalMu,
                              invert)
                    if result == 'error':
                        print('Error :',s, 'in', methodName)
                        break

                # decrement reference Counter
                for i in range(len(passedArgs)):
                    Gamma.pop(funcArgs[i]['name'])
                    refcountDown(globalMu, passedArgs[i])

                printMU(Gamma, globalMu)


                if callORuncall == 'call':
                    historyStack.put(request)
                elif callORuncall == 'uncall':
                    invert = not invert
                    historyStack.get()
                
                if (request[4] != None):
                    # attached
                    print ('main ProcDict :',ProcDict)
                    if (request[0] != 'main' ):
                        request[4].send(methodName + ' method ended')
                    elif (request[0] == 'main' and len(ProcDict) == 0):
                        request[4].send(methodName + ' method ended')




