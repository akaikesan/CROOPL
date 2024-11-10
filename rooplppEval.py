import multiprocessing as mp
import time
import sys
import queue


class Value:
    def __init__(self, v, t):
        self.val = v
        self._type = t
        self.ref = 1

    def countUp(self):
        self.ref += 1

    def countDown(self):
        self.ref -= 1

def statementInverter(statement, invert):
    returnStatement = statement
    if not invert:
        return statement
    else:
        if (statement[0] == 'assignment'): 
            return statement
        elif (statement[0] == 'print'):
            return statement
        elif (statement[0] == 'skip'):
            return statement
        elif (statement[0] == 'new'):
            # ['new', className, varName, 'separate']
            # ['new', className, [varName]]
            returnStatement[0] = 'delete'
            return returnStatement

        elif (statement[0] == 'delete'):
            returnStatement[0] = 'new'
            return returnStatement

        elif (statement[0] == 'copy'):
            #['copy', 'Cell', ['cell'], ['cellCopy']]
            returnStatement[0] = 'uncopy'
            return returnStatement

        elif (statement[0] == 'uncopy'):
            #['copy', 'Cell', ['cell'], ['cellCopy']]
            returnStatement[0] = 'copy'
            return returnStatement

        elif (statement[0] == 'call' or statement[0] == 'uncall'):
            # ['call', 'tc', 'test', [args]]
            # ['call', 'test', [args]]
            returnStatement[0] = 'uncall'
            return returnStatement

        elif (statement[0] == 'if'):  # statement[1:4] = [e1, s1, s2, e2]
            e1 = statement[1]
            s1 = statement[2]
            s2 = statement[3]
            e2 = statement[4]
            returnStatement[1] = e2
            returnStatement[2] = s2
            returnStatement[3] = s1
            returnStatement[4] = e1

            return returnStatement


        elif (statement[0] == 'from'):  # statement[1:4] = [e1, s1, s2, e2]

            e1 = statement[1]
            s1 = statement[2]
            s2 = statement[3]
            e2 = statement[4]
            returnStatement[1] = e2
            returnStatement[2] = s2
            returnStatement[3] = s1
            returnStatement[4] = e1

            return returnStatement
        # LOCAL:0 type:1 id:2 EQ exp:3  statements:4 DELOCAL type:5 id:6 EQ exp:7
        elif (statement[0] == 'local'):

            t1 = statement[1]
            id1 = statement[2]
            exp1 = statement[3]
            t2 = statement[5]
            id2 = statement[6]
            exp2 = statement[7]
            returnStatement[1] = t2
            returnStatement[2] = id2
            returnStatement[3] = exp2
            returnStatement[5] = t1
            returnStatement[6] = id1
            returnStatement[7] = exp1
            return returnStatement

def printMU(Gamma, MU):
    print(Gamma)
    for k, v in MU.items():
        if type(v) == Value :
            print(k, ':', '(', v.val, ',', v.ref, ',', v._type, ')')
        elif type(v) == dict:
            print(k, ':', v)
        else:
            print('unexpected Type')

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
    globalMu[Gamma[var]] = Value(val, 'int')

def getType(t):
    if t[0] == 'separate':
        return t[1]
    else:
        return t[0]

def setNewedObj(classMap, objType, Gamma, globalMu, q):
    fields = classMap[getType(objType)]['fields']
    for f in fields.keys():
        l = max(globalMu.keys()) + 1
        Gamma[f] = l
        if fields[f][0] == 'int':
            v = Value(0, 'int')
            globalMu[l] = v
        elif fields[f][0] == 'list':
            pass
        else:
            globalMu[l] = Value(None, 'Address')
            objAddrValue = max(globalMu.keys()) + 1
            globalMu[l] = Value(objAddrValue, 'Address')
            globalMu[objAddrValue] = {'type':fields[f], 'status': 'nil'}


    objAddrValue = globalMu[Gamma['this']].val
    nilobj = globalMu[objAddrValue]
    nilobj['status'] = 'newed'
    nilobj['methodQ'] = q
    globalMu[objAddrValue] = nilobj

    return

def makeLocalObj(classMap,
                 globalMu,
                 addr
                 ):
    l = max(globalMu.keys()) + 1
    Gamma = {'this' : l} 
    objAddr = globalMu[addr].val
    globalMu[l] = Value(objAddr, 'Address')
    objType = globalMu[objAddr]['type']

    setNewedObj(classMap, objType, Gamma, globalMu, None)

    obj = globalMu[objAddr] 
    obj['gamma'] = Gamma
    globalMu[objAddr] = obj
 
def makeSeparatedProcess(classMap,
                         globalMu,
                         addr):
    Gamma = {'this' : addr} 
    objType = globalMu[globalMu[addr].val]['type']

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
    time.sleep(sys.float_info.min)

    return p

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

def evalExp(classMap,thisType,Gamma, globalMu, exp, invert):
    # expression doesnt care about invert???
    if isinstance(exp, list):
        if len(exp) == 1:
            # [<int>] 
            if isinstance(exp[0], list):
                pass

            else:
                pass

        else:
            if (exp[1] == '+'):
                return evalExp(classMap,thisType,Gamma, globalMu, exp[0], invert) + evalExp(classMap,thisType,Gamma, globalMu, exp[2], invert)
            elif (exp[1] == '-'):
                return evalExp(classMap,thisType,Gamma, globalMu, exp[0], invert) - evalExp(classMap,thisType,Gamma, globalMu, exp[2], invert)

            elif (exp[1] == '/'):
                return evalExp(classMap,thisType,Gamma, globalMu, exp[0], invert) / evalExp(classMap,thisType,Gamma, globalMu, exp[2], invert)
            elif (exp[1] == '*'):
                return evalExp(classMap,thisType,Gamma, globalMu, exp[0], invert) * evalExp(classMap,thisType,Gamma, globalMu, exp[2], invert)
            elif (exp[1] == '='):
                e1 = evalExp(classMap,thisType,Gamma, globalMu, exp[0], invert)
                e2 = evalExp(classMap,thisType,Gamma, globalMu, exp[2], invert)
                return e1 == e2

            elif (exp[1] == '!='):
                e1 = evalExp(classMap,thisType,Gamma, globalMu, exp[0], invert)
                e2 = evalExp(classMap,thisType,Gamma, globalMu, exp[2], invert)
                return e1 != e2

            elif (exp[1] == '%'):
                return evalExp(classMap,thisType,Gamma, globalMu, exp[0], invert) % evalExp(classMap,thisType,Gamma, globalMu, exp[2], invert)
            elif (exp[1] == '&'):
                return evalExp(classMap,thisType,Gamma, globalMu, exp[0], invert) and evalExp(classMap,thisType,Gamma, globalMu, exp[2], invert)
            elif (exp[1] == '>'):
                return evalExp(classMap,thisType,Gamma, globalMu, exp[0], invert) > evalExp(classMap,thisType,Gamma, globalMu, exp[2], invert)
            elif (exp[1] == '<='):
                return evalExp(classMap,thisType,Gamma, globalMu, exp[0], invert) <= evalExp(classMap,thisType,Gamma, globalMu, exp[2], invert)
            elif (exp[1] == '>='):
                return evalExp(classMap,thisType,Gamma, globalMu, exp[0], invert) >= evalExp(classMap,thisType,Gamma, globalMu, exp[2], invert)
            elif (exp[1] == '<'):
                return evalExp(classMap,thisType,Gamma, globalMu, exp[0], invert) < evalExp(classMap,thisType,Gamma, globalMu, exp[2], invert)

    elif exp.isdecimal():
        # int (exp[0] is string. turn it to int Here.)
        return int(exp)
    elif exp == 'nil':
        return 'nil'
    else:
        content = globalMu[Gamma[exp]]
        t = content._type
        if t == 'int':
            return content.val
        else:
            if globalMu[content.val]['status'] == 'nil':
                return 'nil'
            else:
                return content.val

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

def evalStatement(classMap, 
                  rawstatement,
                  Gamma,
                  globalMu,
                  invert):

    global ProcessRefCounter
    global ProcessObjName

    statement = statementInverter(rawstatement, invert)

    if statement is None:
        pass
    elif (statement[0] == 'assignment'): 
        # p[0] = ['assignment', p[2], p[1], p[3]]
        # ex) x += 2+1 -> ['assignment', +=, x, 2+1]

        thisType = globalMu[globalMu[Gamma['this']].val]['type']
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
                print(statement[2], 'is not defined in class', '\'' + getType(globalMu[globalMu[Gamma['this']].val]['type']) + '\'')

            right = evalExp(classMap,thisType,Gamma, globalMu, statement[3], invert)

            result = getAssignmentResult(statement[1], invert, left, right)

            # writeMu
            writeMu(Gamma, globalMu, statement[2], result)

    elif (statement[0] == 'print'):

        thisType = globalMu[globalMu[Gamma['this']].val]['type']
        if statement[1][0] == '"' and statement[1][-1] == '"':
            print(statement[1][1:-1])
            #printMU(Gamma,globalMu)
        else :
            print(evalExp(classMap, thisType, Gamma, globalMu, statement[1], invert))

    elif (statement[0] == 'skip'):
        pass
    elif (statement[0] == 'new'):

        # ['new', className, varName, 'separate']
        # ['new', className, varName]

        if isinstance(statement[1], list): 
            pass
        else: 
            # new object
            
            if (len(statement) == 4):
                objAddr =  globalMu[Gamma[statement[2]]].val
                if (globalMu[objAddr]['type'][0] != 'separate' or globalMu[objAddr]['status'] != 'nil'):
                    print('separate-type object can\'t be non-separate-newed.')
                    return 'error'
                elif (globalMu[objAddr]['type'][1] != statement[1]):
                    print('type mismatch',globalMu[objAddr]['type'][1], statement[1] )
                    return 'error'

                proc = makeSeparatedProcess(classMap, globalMu,  Gamma[statement[2]])
                global ProcDict
                ProcDict[Gamma[statement[2]]] = proc

            if (len(statement) == 3):
                objAddr =  globalMu[Gamma[statement[2]]].val

                if (globalMu[objAddr]['type'][0] == 'separate' or globalMu[objAddr]['status'] != 'nil'):
                    print('Error : separate-type object can\'t be non-separate-newed.')
                    return 'error'

                makeLocalObj(classMap, globalMu, Gamma[statement[2]])
                
                



    elif (statement[0] == 'delete'):

        if isinstance(statement[1], list): 
            # delete list
            pass

        else: 
            # delete object (not list).
            pass

    elif (statement[0] == 'copy'):
        #['copy', 'Cell', 'cell', 'cellCopy']
        copyFromVar = Gamma[statement[2]]
        copyFromVal = globalMu[copyFromVar].val ## 

        copyToVar = Gamma[statement[3]]
        targetVarVal = globalMu[copyToVar]

        if(globalMu[targetVarVal.val]['status'] != 'nil'):
            print('Error : copy target should be nil')
            return 'error'
        else:
            # remove nil-obj with no reference
            globalMu.pop(targetVarVal.val)

        targetVarVal.val = copyFromVal
        globalMu[copyToVar] = targetVarVal

    elif (statement[0] == 'uncopy'):
        pass

    elif (statement[0] == 'call' or statement[0] == 'uncall'):
        # ['call', 'tc', 'test', [args]]
        # ['call', 'test', [args]]

        if (statement[0] == 'uncall'):
            invert = not invert

        if len(statement) == 4:  # call method of object
            objAddr = globalMu[Gamma[statement[1]]].val

            if (globalMu[objAddr]['status'] == 'nil'):
                print('Error : nil object can\'t be called.')
                return 'error'

            if ('gamma' in globalMu[objAddr].keys() ):
                # call for local object

                t          = getType(globalMu[objAddr]['type'])
                statements = classMap[t]['methods'][statement[2]]['statements']
                funcArgs   = classMap[t]['methods'][statement[2]]['args']
                passedArgs = statement[3]
                localGamma = globalMu[objAddr]['gamma']

                if (len(funcArgs) != len(passedArgs)):
                    print('Error : number of arguments is not matched.')
                    return 'error'

                for i in range(len(funcArgs)):
                    localGamma[funcArgs[i]['name']] = Gamma[passedArgs[i]]

                stmts = []
                if invert :
                    stmts = reversed(statements)
                else:
                    stmts = statements 

                for s in stmts:
                    evalStatement(classMap, s, localGamma, globalMu, invert)

                for i in range(len(funcArgs)):
                    localGamma.pop(funcArgs[i]['name'])
                    
                obj = globalMu[objAddr]
                obj['gamma'] = localGamma
                globalMu[objAddr] = obj


            else:
                # call for remote object
                callerAddr    = Gamma['this']
                callOrUncall  = statement[0]
                targetObjAddr = globalMu[Gamma[statement[1]]].val
                methodName    = statement[2]

                argsAddr      = []
                for varName in statement[3]:
                    varAddr = Gamma[varName]
                    refcountUp(globalMu, varAddr)
                    argsAddr.append(varAddr)

                q = globalMu[targetObjAddr]['methodQ']
                time.sleep(sys.float_info.min)
                q.put([methodName, argsAddr, callOrUncall, callerAddr, None])


        elif len(statement) == 3:  # call method of local object

            if (statement[0] == 'uncall'):
                invert = not invert


            
            objAddr = globalMu[Gamma['this']].val
            t          = getType(globalMu[objAddr]['type'])
            statements = classMap[t]['methods'][statement[1]]['statements']
            funcArgs   = classMap[t]['methods'][statement[1]]['args']
            passedArgs = statement[2]

            for i in range(len(funcArgs)):
                Gamma[funcArgs[i]['name']] = Gamma[passedArgs[i]]


            stmts = []
            if invert :
                stmts = reversed(statements)
            else:
                stmts = statements 

            for s in stmts:
                evalStatement(classMap, s, Gamma, globalMu, invert)

            for i in range(len(funcArgs)):
                Gamma.pop(funcArgs[i]['name'])


        if (statement[0] == 'uncall'):
            invert = not invert
            


    elif (statement[0] == 'if'):  
        thisType = globalMu[globalMu[Gamma['this']].val]['type']
        e1Evaled = evalExp(classMap,thisType,Gamma, globalMu, statement[1], invert)
        assert type(e1Evaled) == bool
        if e1Evaled :# if-True
            stmts = []
            if invert :
                stmts = reversed(statement[2])
            else:
                stmts = statement[2]

            for s in stmts:
                evalStatement(classMap, s, Gamma, globalMu, invert)

            e2Evaled = evalExp(classMap,thisType,Gamma, globalMu, statement[4], invert)
            assert e2Evaled == True 
        else:       # if-False
            stmts = []
            if invert :
                stmts = reversed(statement[3])
            else:
                stmts = statement[3]

            for s in stmts:
                evalStatement(classMap, s, Gamma, globalMu, invert)

            e2Evaled = evalExp(classMap,thisType,Gamma, globalMu, statement[4], invert)
            assert e2Evaled == False






    elif (statement[0] == 'from'):  # statement[1:4] = [e1, s1, s2, e2]

        thisType = globalMu[globalMu[Gamma['this']].val]['type']
        assert evalExp(classMap,thisType,Gamma, globalMu, statement[1], invert) == True
        stmts = []
        if invert :
            stmts = reversed(statement[1])
        else:
            stmts = statement[1]

        for s in stmts:
            evalStatement(classMap, s, Gamma, globalMu, invert)

        while evalExp(classMap,thisType,Gamma, globalMu, statement[4], invert) == False:

            if invert :
                stmts = reversed(statement[3])
            else:
                stmts = statement[3]

            for s in stmts:
                evalStatement(classMap, s, Gamma, globalMu, invert)

            assert evalExp(classMap,thisType,Gamma, globalMu, statement[1], invert) == False

            if invert :
                stmts = reversed(statement[1])
            else:
                stmts = statement[1]

            for s in stmts:
                evalStatement(classMap, s, Gamma, globalMu, invert)

            



    # LOCAL:0 type:1 id:2 EQ exp:3  statements:4 DELOCAL type:5 id:6 EQ exp:7
    elif (statement[0] == 'local'):

        thisType = globalMu[globalMu[Gamma['this']].val]['type']
        if (statement[1][0] == 'separate'):

            if (evalExp(classMap,thisType,Gamma, globalMu, statement[3], invert) != 'nil'):
                print('Error : local object must be nil-initialized.')
                return 'error'

            l = max(globalMu.keys()) + 1
            Gamma[statement[2]] = l
            globalMu[l] = Value(-1, 'Address')
            objAddr = max(globalMu.keys()) + 1
            globalMu[l] = Value(objAddr, 'Address')
            globalMu[objAddr] = {'type': statement[1], 'status': 'nil' }

            stmts = []
            if invert :
                stmts = reversed(statement[4])
            else:
                stmts = statement[4]

            for s in stmts:
                evalStatement(classMap, s, Gamma, globalMu, invert)

            assertValue = evalExp(classMap,thisType,Gamma, globalMu, statement[7], invert)
            addr = Gamma[statement[6]]

            assert  assertValue == 'nil'
            assert statement[2] == statement[6]
            assert globalMu[globalMu[addr].val]['status'] == 'nil'

            Gamma.pop(statement[6])
            globalMu.pop(addr)



        elif statement[1][0] == 'int':
            l = max(globalMu.keys()) + 1
            Gamma[statement[2]] = l
            initValue = evalExp(classMap,thisType,Gamma, globalMu, statement[3], invert)
            assert type(initValue) == int
            globalMu[l] = Value(initValue, 'int')
            stmts = []
            if invert :
                stmts = reversed(statement[4])
            else:
                stmts = statement[4]

            for s in stmts:
                evalStatement(classMap, s, Gamma, globalMu, invert)

            assertValue = evalExp(classMap,thisType,Gamma, globalMu, statement[7], invert)
            addr = Gamma[statement[6]]

            assert  assertValue == globalMu[addr].val
            assert statement[2] == statement[6]

            Gamma.pop(statement[6])

            globalMu.pop(addr)

        else:
            # local object (not separate)

            if (evalExp(classMap,thisType,Gamma, globalMu, statement[3], invert) != 'nil'):
                print('Error : local object must be nil-initialized.')
                return 'error'

            l = max(globalMu.keys()) + 1
            Gamma[statement[2]] = l
            globalMu[l] = Value(-1, 'Address')
            objAddr = max(globalMu.keys()) + 1
            globalMu[l] = Value(objAddr, 'Address')
            globalMu[objAddr] = {'type': statement[1], 'status': 'nil' }


            stmts = []
            if invert :
                stmts = reversed(statement[4])
            else:
                stmts = statement[4]

            for s in stmts:
                evalStatement(classMap, s, Gamma, globalMu, invert)

            assertValue = evalExp(classMap,thisType,Gamma, globalMu, statement[7], invert)
            addr = Gamma[statement[6]]

            assert  assertValue == 'nil'
            assert statement[2] == statement[6]
            assert globalMu[globalMu[addr].val]['status'] == 'nil'


            Gamma.pop(statement[6])

            globalMu.pop(addr)



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

                procObjtype = globalMu[globalMu[Gamma['this']].val]['type']
                statements = classMap[getType(procObjtype)]['methods'][methodName]['statements']
                funcArgs = classMap[getType(procObjtype)]['methods'][methodName]['args']

                # append args to Gamma
                if (len(passedArgs) == len(funcArgs)):
                    for i in range(len(funcArgs)):
                        Gamma[funcArgs[i]['name']] = passedArgs[i]

                # check correspondency with historyTop
                if callORuncall == 'uncall':
                    if historyStack.qsize() != 0:
                        historyTop = historyStack.get()
                    else:
                        q.put(request)
                        continue

                    if ((request[0])  != historyTop[0] or request[3] != historyTop[3]) or (historyTop[2] != 'call'):
                        q.put(request)
                        continue
                    # DO NOT invert 'invert' before REQUEUE!    
                    invert = not invert

                
                # Eval Statements
                stmts = []
                if invert :
                    stmts = reversed(statements)
                else:
                    stmts = statements 

                for s in stmts:
                    result = evalStatement(classMap, s, Gamma, globalMu, invert)
                    if result == 'error':
                        print('Error :', s, 'in', methodName)
                        break

                # decrement reference Counter & remove args from Gamma
                for i in range(len(passedArgs)):
                    Gamma.pop(funcArgs[i]['name'])
                    refcountDown(globalMu, passedArgs[i])

                # historyStack after execution
                if callORuncall == 'call':
                    historyStack.put(request)
                elif callORuncall == 'uncall':
                    invert = not invert
                    historyStack.get()

                
                if (request[4] != None):
                    # attached
                    print ('main ProcDict :', ProcDict)
                    if (request[0] != 'main'):
                        request[4].send(methodName + ' method ended')
                    elif (request[0] == 'main' and len(ProcDict) == 0):
                        request[4].send(methodName + ' method ended')




