import multiprocessing as mp
import time
import sys
import queue


## type is always List. 


class Value:
    def __init__(self, v, t):
        self.val = v
        self._type = t
        self.ref = 1

    def countUp(self):
        self.ref += 1

    def countDown(self):
        self.ref -= 1

def runBlockStatement(classMap, block, Gamma, globalMu, invert):
        stmts = []
        result = 'success'
        if invert :
            stmts = reversed(block)
        else:
            stmts = block 
        for s in stmts:
            result = evalStatement(classMap, s, Gamma, globalMu, invert)
            if result != 'success' :
                break

        return result

def waitForVarRefIsOne(globalMu, varAddr):
    while globalMu[varAddr].ref != 1:
        pass

def statementInverter(statement, invert):
    returnStatement = statement[:]
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

        elif (statement[0] == 'call') :
            # ['call', 'tc', 'test', [args]]
            # ['call', 'test', [args]]
            returnStatement[0] = 'uncall'
            return returnStatement
        elif (statement[0] == 'uncall') :
            # ['call', 'tc', 'test', [args]]
            # ['call', 'test', [args]]
            returnStatement[0] = 'call'
            return returnStatement

        elif (statement[0] == 'if'):  # statement[1:4] = [e1, s1, s2, e2]
            e1 = statement[1]
            s1 = statement[2]
            s2 = statement[3]
            e2 = statement[4]
            returnStatement[1] = e2
            returnStatement[2] = s1
            returnStatement[3] = s2
            returnStatement[4] = e1

            return returnStatement


        elif (statement[0] == 'from'):  # statement[1:4] = [e1, s1, s2, e2]

            e1 = statement[1]
            s1 = statement[2]
            s2 = statement[3]
            e2 = statement[4]
            returnStatement[1] = e2
            returnStatement[2] = s1
            returnStatement[3] = s2
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
        elif (statement[0] == 'require'):
            pass


def printMU(Gamma, MU):
    print(Gamma)
    for k, v in MU.items():
        if type(v) == Value :
            print(k, ':', '(', v.val, ',', v.ref, ',', v._type, ')')
        elif type(v) == dict:
            if not 'status' in v.keys():
                print(k, ':', 'list')
                for k in v.keys():
                    if k == 'type':
                        continue
                    print('   ', k, ': (', v[k].val,',', v[k].ref,',', v[k]._type, ')')
            else:
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

def writeValToMu(Gamma, globalMu, var, val):
    v =  globalMu[Gamma[var]]
    v.val =  val
    globalMu[Gamma[var]] = v

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
            globalMu[l] = Value(None, 'Address')
            objAddrValue = max(globalMu.keys()) + 1
            globalMu[l] = Value(objAddrValue, 'Address')
            globalMu[objAddrValue] = {'type' : fields[f], 'status': 'nil'}
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
    l = max(globalMu.keys()) + 1
    Gamma = {'this' : l} 
    objAddr = globalMu[addr].val
    globalMu[l] = Value(objAddr, 'Address')
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

def evalExp(Gamma, globalMu, exp):
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
                return evalExp(Gamma, globalMu, exp[0]) + evalExp(Gamma, globalMu, exp[2])
            elif (exp[1] == '-'):
                return evalExp(Gamma, globalMu, exp[0]) - evalExp(Gamma, globalMu, exp[2])

            elif (exp[1] == '/'):
                return evalExp(Gamma, globalMu, exp[0]) / evalExp(Gamma, globalMu, exp[2])
            elif (exp[1] == '*'):
                return evalExp(Gamma, globalMu, exp[0]) * evalExp(Gamma, globalMu, exp[2])
            elif (exp[1] == '='):
                e1 = evalExp(Gamma, globalMu, exp[0])
                e2 = evalExp(Gamma, globalMu, exp[2])
                return e1 == e2

            elif (exp[1] == '!='):
                e1 = evalExp(Gamma, globalMu, exp[0])
                e2 = evalExp(Gamma, globalMu, exp[2])
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
    elif exp == 'nil':
        return 'nil'
    else:
        content = globalMu[Gamma[exp]]
        t = content._type
        if t == 'int' :
            return content.val
        elif t == 'Address' and globalMu[content.val]['type'] == 'list':
            for k,v in globalMu[content.val].items():
                if (k != 'type'):
                    print(k, ':', v.val, ',',  v.ref, ',', v._type)
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

        if (statement[1] == '<=>'):
            if (type(statement[2]) != list and type(statement[3]) != list):
                leftAddr = Gamma[statement[2]]
                rightAddr = Gamma[statement[3]]
                leftContent = globalMu[leftAddr]
                rightContent = globalMu[rightAddr]

                leftContentVal = evalExp(Gamma, globalMu, statement[2], invert)
                rightContentVal = evalExp(Gamma, globalMu, statement[3])
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

        else:
            # readMu
            left = 0
            try:
                addr = Gamma[statement[2]]
                left = globalMu[addr].val
            except:
                print(statement[2], 'is not defined in class', '\'' + getType(globalMu[globalMu[Gamma['this']].val]['type']) + '\'')

            right = evalExp(Gamma, globalMu, statement[3])

            result = getAssignmentResult(statement[1], invert, left, right)

            # writeMu
            writeValToMu(Gamma, globalMu, statement[2], result)

    elif (statement[0] == 'print'):

        if statement[1][0] == '"' and statement[1][-1] == '"':
            print(statement[1][1:-1])
            #printMU(Gamma,globalMu)
        elif (statement[1] == 'memory'):
            printMU(Gamma, globalMu)
        else :
            print(evalExp(Gamma, globalMu, statement[1]))

    elif (statement[0] == 'skip'):
        pass
    elif (statement[0] == 'new'):

        # ['new', className, varName, 'separate']
        # ['new', className, varName]

        if isinstance(statement[1], list): 
            varAddr = Gamma[statement[2]]
            objAddr = globalMu[varAddr].val
            size = evalExp(Gamma, globalMu, statement[1][1])
            assert type(size) == int

            if statement[1][0] == 'int':
                d = {'type':'list'}
                for i in range(size):
                    d[i] = Value(0,'int')
                globalMu[objAddr] = d
            else :

                d = {'type':'list'}
                for i in range(size):
                    objPointerAddress = max(globalMu.keys()) + 1
                    d[i] = Value(objPointerAddress, 'Address')
                    globalMu[objPointerAddress] = Value(None,'Address')
                    objAddress = max(globalMu.keys()) + 1
                    globalMu[objPointerAddress] = Value(objAddress,'Address')
                    globalMu[objAddress] = {'type' : [statement[1][0]], 'status': 'nil'}

                globalMu[objAddr] = d

        else: 
            # new object
            
            if (len(statement) == 4):
                if isinstance(statement[2], list):
                    objPointerAddr = globalMu[globalMu[Gamma[statement[2][0]]].val][statement[2][1]].val
                    objAddr = globalMu[objPointerAddr].val
                else:
                    objPointerAddr = Gamma[statement[2]]
                    objAddr =  globalMu[Gamma[statement[2]]].val

                if (globalMu[objAddr]['type'][0] != 'separate' or globalMu[objAddr]['status'] != 'nil'):
                    print('separate-type object can\'t be non-separate-newed.')
                    return 'error'
                elif (globalMu[objAddr]['type'][1] != statement[1]):
                    print('type mismatch',globalMu[objAddr]['type'][1], statement[1] )
                    return 'error'



                proc = makeSeparatedProcess(classMap, globalMu,  objPointerAddr)
                global ProcDict
                ProcDict[Gamma[statement[2]]] = proc

            if (len(statement) == 3):

                if isinstance(statement[2], list):
                    objPointerAddr = globalMu[globalMu[Gamma[statement[2][0]]].val][int(statement[2][1])].val
                    objAddr = globalMu[objPointerAddr].val
                else:
                    objPointerAddr = Gamma[statement[2]]
                    objAddr =  globalMu[Gamma[statement[2]]].val

                if (globalMu[objAddr]['type'][0] == 'separate' or globalMu[objAddr]['status'] != 'nil'):
                    print('Error : separate-type object can\'t be non-separate-newed.')
                    return 'error'

                makeLocalObj(classMap, globalMu, objPointerAddr)
                
                



    elif (statement[0] == 'delete'):

        # ['delete', className, varName, 'separate']
        # ['delete', className, varName]

        if isinstance(statement[1], list): 
            # delete list
            pass

        else: 
            # delete object (not list).
            ignore = ['type', 'methodQ', 'status', 'gamma']

            if (len(statement) == 3):
                for k,v in globalMu[globalMu[Gamma[statement[2]]].val]['gamma'].items():
                    if k in ignore:
                        continue
                    varAddr = globalMu[v].val
                    if k == 'this':
                        globalMu.pop(v)
                    
                    elif globalMu[v]._type == 'int':
                        if globalMu[v].val != 0:
                            print('Error : delete object that has non-zero field')
                            return 'error'
                        else:
                            globalMu.pop(v)
                    elif globalMu[v]._type == 'Address':
                        if globalMu[varAddr]['status'] != 'nil' :
                            print('Error : delete object that has non-nil field')
                            return 'error'
                        else:
                            globalMu.pop(v)
                            globalMu.pop(varAddr)

                obj = globalMu[globalMu[Gamma[statement[2]]].val]
                obj.pop('gamma')
                obj['status'] = 'nil'
                globalMu[globalMu[Gamma[statement[2]]].val] = obj
            elif(len(statement) == 4):
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
        #['uncopy', 'Cell', 'cell', 'cellCopy']
        if statement[1] == 'int':
            assert globalMu[Gamma[statement[3]]]._type == 'int'
            globalMu[Gamma[statement[3]]].val = 0
        else:
            assert globalMu[Gamma[statement[3]]]._type == 'Address'
            assert globalMu[globalMu[Gamma[statement[3]]].val]['status'] != 'nil'
            l = max(globalMu.keys()) + 1
            writeValToMu(Gamma, globalMu, statement[3], l)
            globalMu[l] ={'type' : statement[1], 'status' : 'nil'}


    elif (statement[0] == 'call' or statement[0] == 'uncall'):
        # ['call', 'tc', 'test', [args]]
        # ['call', 'test', [args]]

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

                localInvert = invert
                if (statement[0] == 'uncall' and invert):
                    pass
                elif (statement[0] == 'uncall' and not invert):
                    localInvert = not invert

                runBlockStatement(classMap,
                                  statements,
                                  localGamma,
                                  globalMu, localInvert)

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
            
            objAddr = globalMu[Gamma['this']].val
            t          = getType(globalMu[objAddr]['type'])
            statements = classMap[t]['methods'][statement[1]]['statements']
            funcArgs   = classMap[t]['methods'][statement[1]]['args']
            passedArgs = statement[2]

            for i in range(len(funcArgs)):
                Gamma[funcArgs[i]['name']] = Gamma[passedArgs[i]]


            localInvert = invert
            if (statement[0] == 'uncall' and invert):
                pass
            elif (statement[0] == 'uncall' and not invert):
                localInvert = not invert


            runBlockStatement(classMap,
                              statements,
                              Gamma,
                              globalMu, localInvert)

            for i in range(len(funcArgs)):
                Gamma.pop(funcArgs[i]['name'])


            


    elif (statement[0] == 'if'):  
        e1Evaled = evalExp(Gamma, globalMu, statement[1])
        assert type(e1Evaled) == bool
        if e1Evaled :# if-True
            runBlockStatement(classMap,
                              statement[2],
                              Gamma,
                              globalMu, invert)

            e2Evaled = evalExp(Gamma, globalMu, statement[4])
            assert e2Evaled == True 
        else:       # if-False
            runBlockStatement(classMap,
                              statement[3],
                              Gamma,
                              globalMu, invert)

            e2Evaled = evalExp(Gamma, globalMu, statement[4])
            assert e2Evaled == False






    elif (statement[0] == 'from'):  # statement[1:4] = [e1, s1, s2, e2]
        #['from', e1, s1, s2, e2]

        assert evalExp(Gamma, globalMu, statement[1]) == True

        runBlockStatement(classMap,
                          statement[2],
                          Gamma,
                          globalMu, invert)

        while evalExp(Gamma, globalMu, statement[4]) == False:

            runBlockStatement(classMap,
                              statement[3],
                              Gamma,
                              globalMu, invert)

            assert evalExp( Gamma,
                           globalMu,
                           statement[1]) == False

            runBlockStatement(classMap,
                              statement[2],
                              Gamma,
                              globalMu, invert)
            



    # LOCAL:0 type:1 id:2 EQ exp:3  statements:4 DELOCAL type:5 id:6 EQ exp:7
    elif (statement[0] == 'local'):


        if (statement[1][0] == 'separate'):

            if (evalExp(Gamma, globalMu, statement[3]) != 'nil'):
                print('Error : local object must be nil-initialized.')
                return 'error'

            l = max(globalMu.keys()) + 1
            Gamma[statement[2]] = l
            globalMu[l] = Value(-1, 'Address')
            objAddr = max(globalMu.keys()) + 1
            globalMu[l] = Value(objAddr, 'Address')
            globalMu[objAddr] = {'type': statement[1], 'status': 'nil' }

            runBlockStatement(classMap, statement[4], Gamma, globalMu, invert)
            assertValue = evalExp(Gamma, globalMu, statement[7])
            addr = Gamma[statement[6]]

            assert  assertValue == 'nil'
            assert statement[2] == statement[6]
            assert globalMu[globalMu[addr].val]['status'] == 'nil'


            Gamma.pop(statement[6])
            globalMu.pop(globalMu[addr].val)
            globalMu.pop(addr)



        elif statement[1][0] == 'int':
            l = max(globalMu.keys()) + 1
            Gamma[statement[2]] = l
            initValue = evalExp(Gamma, globalMu, statement[3])

            assert type(initValue) == int
            globalMu[l] = Value(initValue, 'int')

            runBlockStatement(classMap, statement[4], Gamma, globalMu, invert)
            assertValue = evalExp(Gamma, globalMu, statement[7], invert)
            addr = Gamma[statement[6]]

            assert  'int' == globalMu[l]._type
            assert  assertValue == globalMu[addr].val
            assert statement[2] == statement[6]

            Gamma.pop(statement[6])
            globalMu.pop(addr)

        else:
            # local object (not separate)

            if (evalExp(Gamma, globalMu, statement[3]) != 'nil'):
                print('Error : local object must be nil-initialized.')
                return 'error'

            l = max(globalMu.keys()) + 1
            Gamma[statement[2]] = l
            globalMu[l] = Value(-1, 'Address')
            objAddr = max(globalMu.keys()) + 1
            globalMu[l] = Value(objAddr, 'Address')
            globalMu[objAddr] = {'type': statement[1], 'status': 'nil' }


            runBlockStatement(classMap, statement[4], Gamma, globalMu, invert)

            assertValue = evalExp(Gamma, globalMu, statement[7])
            addr = Gamma[statement[6]]

            assert  assertValue == 'nil'
            assert statement[2] == statement[6]
            assert globalMu[globalMu[addr].val]['status'] == 'nil'


            Gamma.pop(statement[6])

            globalMu.pop(globalMu[addr].val)
            globalMu.pop(addr)

    elif (statement[0] == 'require'):
        e1Evaled = evalExp(Gamma, globalMu, statement[1])
        if e1Evaled == False:
            return 'reQ'
        else:
            runBlockStatement(classMap, statement[2], Gamma, globalMu, invert)







    return 'success'

def interpreter(classMap,
                className,
                q, 
                Gamma,
                globalMu):

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
        if className[1] == "Buffer":

            print("histry size:", historyStack.qsize())
            tmp = []
            if historyStack.qsize() > 0:
                for i in range(historyStack.qsize()):
                    top = historyStack.get()
                    tmp.append(top)
                    print(top)
                for i in range(len(tmp)):
                    historyStack.put(tmp[len(tmp) - 1 - i])

            if q.qsize() > 0:
                tmp = []
                print("methodQ size:", q.qsize())
                for i in range(q.qsize()):
                    top = q.get()
                    tmp.append(top)
                    print(top)
                for i in range(len(tmp)):
                    q.put(tmp[i])
            


        if q.qsize() != 0:
            request = q.get()
            lenReq = len(request)
            if lenReq == 5:

                methodName   = request[0]
                passedArgs   = request[1]
                callORuncall = request[2]
                # if objAddr is 0, this intrprtr is running main func
                callerObjAddr      = request[3] 

                procObjtype = globalMu[globalMu[Gamma['this']].val]['type']

                if 'require' in classMap[getType(procObjtype)]['methods'][methodName].keys():
                    if callORuncall == 'call':
                        exp = classMap[getType(procObjtype)]['methods'][methodName]['require']
                    else:
                        assert callORuncall == 'uncall'
                        exp = classMap[getType(procObjtype)]['methods'][methodName]['ensure']

                    #printMU(Gamma,globalMu)

                    e1Evaled = evalExp(Gamma, globalMu, exp)
                    if e1Evaled == False:
                        print("require failed")
                        q.put(request)
                        continue
                    else:
                        print('require/ensure passed')
                        print(request)

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
                        print('history unmatched')
                        q.put(request)
                        continue

                    if (request[0]  == historyTop[0] and callerObjAddr == historyTop[3]) and ((historyTop[2] == 'call') and True):

                        print("HT:",historyTop)
                        print("HT MATCH:",request)
                    else:
                        print("HT :",historyTop)
                        print("HT ReQ:",request)
                        q.put(request)
                        historyStack.put(historyTop)
                        continue
                
                # Eval Statements
                initInvert = False
                if callORuncall == 'uncall' :
                    initInvert = True

                result = runBlockStatement(classMap, statements, Gamma, globalMu, initInvert)

                # decrement reference Counter & remove args from Gamma
                for i in range(len(passedArgs)):
                    Gamma.pop(funcArgs[i]['name'])
                    refcountDown(globalMu, passedArgs[i])


                # historyStack after execution
                if callORuncall == 'call':
                    historyStack.put(request)

                
                if (request[4] != None):
                    # attached
                    if (request[0] != 'main'):
                        request[4].send(methodName + ' method ended')
                    elif (request[0] == 'main' and len(ProcDict) == 0):
                        request[4].send(methodName + ' method ended')




