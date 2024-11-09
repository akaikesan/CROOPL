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




def passArgs(globalStore, argsInfo, passedArgs,storePath, envObjName):

    for i, a in enumerate(argsInfo):
        separatedObjName = getValueByPath(globalStore, storePath, envObjName)
        if a['name'] in globalStore[separatedObjName].keys():
            raise Exception('arg name is already defined')

        value = getValueByPath(globalStore, storePath, passedArgs[i])
        updateGlobalStoreByPath(globalStore, separatedObjName, a['name'], value)



def assignVarAndGetDictByAddress(dic, p, varName, value, sep="/"):
    lis = p.split(sep)
    def _(dic, lis, sep):
        if len(lis) == 0:
            return 
        if len(lis) == 1:
            if isinstance(varName, list):
                index = int(varName[1][0])
                dic[lis[0]][varName[0]][index] = value
            else:
                dic[lis[0]][varName] = value 
        else:
            _(dic.get(lis[0], {}), lis[1:], sep)
    _(dic, lis, sep=sep)


def waitUntilStackIsEmpty(globalStore,topLevelName):
    global historyStack
    parent_conn, child_conn = mp.Pipe()
    globalStore[topLevelName]['#q'].put( [child_conn] )

    historyNumber = parent_conn.recv()

    while True:
        if historyNumber == 0:
            break




def reflectArgsPassedSeparated(globalStore, callerObjName, objName, argsInfo, args, dictAddress):

    q = globalStore['#Store']

    parent_conn, child_conn = mp.Pipe()
    q.put(['reflectArgsPassedSeparated', callerObjName, objName, argsInfo, args, dictAddress, child_conn])

    parent_conn.recv()
    # print('args reflected by path')





def reflectArgsPassed(globalStore, envObjName, calledObjName, argsInfo, passedArgs):


    q = globalStore['#Store']

    parent_conn, child_conn = mp.Pipe()

    q.put(['reflectArgsPassed', envObjName, calledObjName, argsInfo, passedArgs, child_conn])


    parent_conn.recv()
    # print('args reflected')





def updateGlobalStoreByPath(globalStore, storePath, varName, value):
    

    q = globalStore['#Store']

    parent_conn, child_conn = mp.Pipe()
    q.put(['updatePath', storePath, varName, value, child_conn])

    parent_conn.recv()
    # print('store updated by path')





def deleteVarGlobalStoreByPath(globalStore, storePath, varName):

    q = globalStore['#Store']

    parent_conn, child_conn = mp.Pipe()
    q.put(['deletePath', storePath, varName, child_conn])

    parent_conn.recv()
    # print('store deleted by path')





def deleteVarGlobalStore(globalStore, envObjName, id1):

    q = globalStore['#Store']

    parent_conn, child_conn = mp.Pipe()
    q.put(['delete', envObjName, id1, child_conn])

    parent_conn.recv()
    # print('store deleted')





def getValueByPath(dic, p, varName, sep="/"):
    lis = p.split(sep)
    def _(dic, lis, sep):
        if len(lis) == 0:
            return 
        if len(lis) == 1:
            if isinstance(varName, list):
                index = int(varName[1][0])
                return dic[lis[0]][varName[0]][index] 
            else:
                return dic[lis[0]][varName]
        else:
            return _(dic.get(lis[0], {}), lis[1:], sep)
    return _(dic, lis, sep=sep)





def getLocalStore(dic, p, sep="/"):
    lis = p.split(sep)
    def _(dic, lis, sep):
        if len(lis) == 0:
            return 
        if len(lis) == 1:
            return dic[lis[0]].copy()
        else:
            return _(dic.get(lis[0], {}), lis[1:], sep)
    return _(dic, lis, sep=sep)





def makeStore(globalStore, storePath, classMap, className):

    st = {}

    if isinstance(className, list):  # Array


        index = evalExp(getLocalStore(globalStore, storePath), className[0][1])
        assert isinstance(index, int)
        
        if className[0][0] == 'int':

            st = [0] * int(index)
        else:
            st = [{}] * int(index)

    else:
        for f in classMap[className]['fields'].keys():

            if classMap[className]['fields'][f] == 'int':
                # 0 initialized
                st[f] = 0
            else:
                # TODO: ex) AクラスのfieldをAクラス内で宣言したら、エラーを出す。
                #          現在は無限再帰のpython側のエラーとなっている。
                # st[f] = makeStore(classMap, classMap[className]['fields'][f])
                st[f] = {}
        st['type'] = className

    return st





def callOrUncall(invert, callUncall):
    # callOrUncall is must be called when call separated object's method
    if callUncall == 'call':
        if invert:
            return 'uncall'
        else:
            return 'call'
    elif callUncall == 'uncall':
        if invert:
            return 'call'
        else:
            return 'uncall'
    else:
        raise Exception("callUncall must be call or uncall")



    





def setMuGamma(classMap, ProcType, Gamma, globalMu, q):
    fields = classMap[ProcType]['fields']
    for f in fields.keys():
        l = len(globalMu.keys()) + 1
        Gamma[f] = l
        if fields[f][0] == 'int':
            v = Value(0,1)
            globalMu[l] = v
        elif fields[f][0] == 'list':
            pass
        else:
            globalMu[l] = {'type':fields[f], 'status': 'nil'}

    l = len(globalMu.keys()) + 1
    Gamma['this'] = l
    globalMu[l] = {'methodQ':q, 'type': ProcType}

    return l



 
def makeSeparatedProcess(classMap,
                         ObjType,
                         globalMu):
    global m
    Gamma = {} 

    if globalMu.keys() == []:
        m = mp.Manager()
        q = m.Queue()
    else:
        q = m.Queue()


    objAddr = setMuGamma(classMap, ObjType, Gamma, globalMu, q)
   
    p = mp.Process(target = interpreter,
                   args=(classMap,
                         ObjType,
                         q,
                         Gamma,
                         globalMu))





    p.start()
    time.sleep(0.1)

    return p, objAddr 





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





def getType(classMap, thisType, varName):
    return classMap[thisType]['fields'][varName]
    




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

        '''
        for k in globalStore.keys():
            if k != '#Store':
                print('$ ' + k + ' $')
                print(globalStore[k])
        '''

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
                    raise Exception('non-seprate-type object can\'t be separate-newed.')

                proc, objAddr = makeSeparatedProcess(classMap, statement[1], globalMu)
                global ProcDict
                ProcDict[objAddr] = proc
                Gamma[statement[2]] = objAddr
            if (len(statement) == 3):
                pass


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

            print(request)

            print(ProcDict)
            if lenReq == 5:

                methodName   = request[0]
                passedArgs   = request[1]
                callORuncall = request[2]
                # if objAddr is 0, this intrprtr is running main func
                objAddr      = request[3] 


                print(Gamma['this'])
                procObjtype = globalMu[Gamma['this']]['type']
                statements = classMap[procObjtype]['methods'][methodName]['statements']
                funcArgs = classMap[procObjtype]['methods'][methodName]['args']

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
                    evalStatement(classMap,
                              s,
                              Gamma,
                              globalMu,
                              invert)

                # decrement reference Counter
                for argAddr in passedArgs:
                    refcountDown(globalMu, argAddr)

                printMU(Gamma,globalMu)

                if callORuncall == 'call':
                    historyStack.put(request)
                elif callORuncall == 'uncall':
                    invert = not invert
                    historyStack.get()
                
                if (request[4] != None):
                    # attached
                    request[4].send(methodName + ' method ended')




