import multiprocessing as mp
import time
import sys
import queue
import traceback


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

def checkVarIsDefined(Gamma, var):
    if var in Gamma.keys():
        return True
    else:
        return False

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

def deleteObjFromMuGamma(Gamma, globalMu, objAddr, separate):

    ignore = ['type', 'methodQ', 'status', 'gamma']
    if separate:
        parent_conn, child_conn = mp.Pipe()
        globalMu[objAddr]['methodQ'].put(['delete', child_conn])
        deletable = parent_conn.recv()

        assert deletable == 'ready_delete'
        tobeNilobj = globalMu[objAddr]
        tobeNilobj.pop('methodQ')
        tobeNilobj['status'] = 'nil'

        globalMu[objAddr] = tobeNilobj
        ProcDict[objAddr].terminate()
        ProcDict.pop(objAddr)
    else:
        waitUntilDeletable(Gamma, globalMu, objAddr)
        for k,v in globalMu[objAddr]['gamma'].items():
            if k in ignore:
                continue
            varAddr = globalMu[v].val

            if k == 'this':
                globalMu.pop(v)
            elif globalMu[v]._type == 'int':
                globalMu.pop(v)
            elif globalMu[v]._type == 'Address':
                globalMu.pop(v)
                globalMu.pop(varAddr)

        obj = globalMu[objAddr]
        obj.pop('gamma')
        obj['status'] = 'nil'
        globalMu[objAddr] = obj

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

def waitUntilDeletable(Gamma, globalMu, objAddr):
    while True:
        if globalMu[objAddr]['type'][0] == 'list':
            # list deletable check
            if 'status' in globalMu[objAddr].keys():
                if globalMu[objAddr]['status'] != 'nil' :
                    continue 
                elif globalMu[objAddr]['status'] == 'nil' :
                    break
               
            else:
                # list is newed
                for k,v in globalMu[objAddr].items():
                    if k == 'type':
                        continue
                    elif globalMu[objAddr][0]._type == 'int':    
                        if v.val != 0 or v.ref != 1:
                            continue 
                    elif globalMu[objAddr][0]._type == 'Address':
                        if k == 'type':
                            continue
                        if globalMu[globalMu[v.val].val]['status'] != 'nil' or v.ref != 1:
                            continue
                            
                break
        else:
            # wait until local object is deletable
            flag = True
            localGamma = globalMu[objAddr]['gamma']
            for k,v in localGamma.items():
                if k == 'this':
                    continue
                elif globalMu[v]._type == 'int':
                    if globalMu[v].val != 0 or globalMu[v].ref != 1:
                        flag = False 
                        break
                elif globalMu[v]._type == 'Address':
                    if globalMu[globalMu[v].val]['status'] != 'nil':
                        flag = False 
                        break
            if flag:
                break
        break


def evalExp(Gamma, globalMu, exp):
    # expression doesnt care about invert? -> yes
    if isinstance(exp, list):
        if len(exp) == 2:
            # [ 'id', index ]
            index = evalExp(Gamma, globalMu, exp[1])

            try:
                return globalMu[globalMu[Gamma[exp[0]]].val][index].val
            except:
                print('error in evalExp', exp)
                raise KeyError(exp[0], 'is not defined in Gamma or out of index')

        else:
            if (exp[1] == '+'):
                return evalExp(Gamma, globalMu, exp[0]) + evalExp(Gamma, globalMu, exp[2])
            elif (exp[1] == '-'):
                return evalExp(Gamma, globalMu, exp[0]) - evalExp(Gamma, globalMu, exp[2])

            elif (exp[1] == '/'):
                return int(evalExp(Gamma, globalMu, exp[0]) / evalExp(Gamma, globalMu, exp[2]))
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
                result =evalExp(Gamma, globalMu, exp[0]) % evalExp(Gamma, globalMu, exp[2])
                return result
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

        managerQ = globalMu[-2]
        parent_conn, child_conn = mp.Pipe()
        managerQ.put([Gamma, statement, invert, child_conn])
        parent_conn.recv()

    elif (statement[0] == 'print'):

        if statement[1][0] == '"' and statement[1][-1] == '"':
            print(statement[1][1:-1])
        elif (statement[1] == 'memory'):
            printMU(Gamma, globalMu)
        elif isinstance(statement[1], list):
            if len(statement[1]) == 2:
                index = evalExp(Gamma, globalMu, statement[1][1])
                print(globalMu[globalMu[Gamma[statement[1][0]]].val][index].val)
            else:
                print(evalExp(Gamma, globalMu, statement[1]))

        else :
            try:
                content = globalMu[Gamma[statement[1]]]
                t = content._type
                if t == 'Address' and globalMu[content.val]['type'][0] == 'list':
                    print("[", end="")
                    for k,v in globalMu[content.val].items():
                        if (k != 'type'):
                            print( v.val, end="")
                            if k != len(globalMu[content.val].items()) - 2:
                                print(', ', end="")
                    print("]")

                elif t == 'Address':
                    print(globalMu[content.val])
                elif t == 'int':
                    print(evalExp(Gamma, globalMu, statement[1]))
            except:
                print(statement[1], 'is not defined')

    elif (statement[0] == 'skip'):
        pass
    elif (statement[0] == 'new'):

        if isinstance(statement[1], list): 
            # new list
            varAddr = Gamma[statement[2]]
            objAddr = globalMu[varAddr].val
            size = evalExp(Gamma, globalMu, statement[1][1])
            assert globalMu[objAddr]['type'][0] == 'list'
            assert type(size) == int
            if len(statement) == 4:
                # ['new', className, varName, 'separate']
                # ['new', ['Sieve', '11'], 'sieves', 'separate']
                assert globalMu[objAddr]['type'][2] == 'separate'
                # new list of separate object
                assert statement[1][0] != 'int'
                d = {'type':['list', statement[1][0]] }
                for i in range(size):
                    #TODO
                    objPointerAddress = max(globalMu.keys()) + 1
                    d[i] = Value(objPointerAddress, 'Address')
                    globalMu[objPointerAddress] = Value(None,'Address')
                    objAddress = max(globalMu.keys()) + 1
                    globalMu[objPointerAddress] = Value(objAddress,'Address')
                    globalMu[objAddress] = {'type' : ['separate', statement[1][0]], 'status': 'nil'}

                globalMu[objAddr] = d

            elif len(statement) == 3:
                # ['new', className, varName]
                # ['new', ['Sieve', '11'], 'sieves']
                if statement[1][0] == 'int':
                    d = {'type':['list', 'int']}
                    for i in range(size):
                        d[i] = Value(0,'int')
                    globalMu[objAddr] = d
                else :

                    d = {'type':['list', statement[1][0]] }
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
                    # statement: ['new',  '<ClassName>' [id, index] 'separate']
                    # new separate Consumer c[1]
                    index = evalExp(Gamma, globalMu, statement[2][1])
                    objPointerAddr = globalMu[globalMu[Gamma[statement[2][0]]].val][index].val
                    objAddr = globalMu[objPointerAddr].val

                    if (globalMu[objAddr]['type'][0] != 'separate' or globalMu[objAddr]['status'] != 'nil'):
                        print('separate-type object can\'t be non-separate-newed.')
                        return 'error'
                    elif (globalMu[objAddr]['type'][1] != statement[1]):
                        print('type mismatch',globalMu[objAddr]['type'][1], statement[1] )
                        return 'error'
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
                ProcDict[objAddr] = proc

            if (len(statement) == 3):

                if isinstance(statement[2], list):
                    # new Consumer c[3]
                    isdefined = checkVarIsDefined(Gamma, statement[2][0])
                    if not isdefined:
                        print(statement[2][0], 'is not defined')
                        return 'error'
                    index = evalExp(Gamma, globalMu,statement[2][1])

                    objPointerAddr = globalMu[globalMu[Gamma[statement[2][0]]].val][index].val
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
        # ['delete', [id, size], varName, 'separate']
        # ['delete', className, [varName, index], 'separate']
        # ['delete', className, varName]

        if isinstance(statement[1], list): 
            # delete list
            varAddr = Gamma[statement[2]]
            listAddr = globalMu[varAddr].val
            waitUntilDeletable(Gamma, globalMu, listAddr)

            if globalMu[listAddr][0]._type == 'int':    
                globalMu[listAddr] = {"type" : ["list", "int"], "status": "nil"}
            elif globalMu[listAddr][0]._type == 'Address':    
                for k,v in globalMu[listAddr].items():
                    if k != 'type':
                        globalMu[v.val] = {"type" : ["list", statement[1]], "status": "nil"}
            else:
                return 'error'
        else: 
            # delete object (not list).
            if (len(statement) == 3):
                objAddr = globalMu[Gamma[statement[2]]].val
                deleteObjFromMuGamma(Gamma, globalMu, objAddr, False)
            elif(len(statement) == 4):

                if isinstance(statement[2], list):
                    listAddr = globalMu[Gamma[statement[2][0]]].val
                    index = evalExp(Gamma, globalMu, statement[2][1])
                    objAddr = globalMu[globalMu[listAddr][index].val].val
                    assert globalMu[objAddr]['type'][0] == 'separate'
                else:
                    objAddr = globalMu[Gamma[statement[2]]].val
                    assert globalMu[objAddr]['type'][0] == 'separate'
                deleteObjFromMuGamma(Gamma, globalMu, objAddr, True)

    elif (statement[0] == 'copy'):
        #['copy', 'Cell', 'cell', 'cellCopy']
        if statement[1] == 'int':
            copyFromVar = Gamma[statement[2]]
            copyFromValValue = globalMu[copyFromVar].val ## 

            copyToVar = Gamma[statement[3]]
            targetVarVal = globalMu[copyToVar]

            if(targetVarVal.val != 0):
                print('Error : copy target should be 0')
                return 'error'
            else:
                # remove nil-obj with no reference
                globalMu.pop(targetVarVal.val)

            targetVarVal.val = copyFromValValue
            globalMu[copyToVar] = targetVarVal
        else:
            copyFromVar = Gamma[statement[2]]
            copyFromValValue = globalMu[copyFromVar].val ## 

            copyToVar = Gamma[statement[3]]
            targetVarVal = globalMu[copyToVar]

            if(globalMu[targetVarVal.val]['status'] != 'nil'):
                print('Error : copy target should be nil')
                return 'error'
            else:
                # remove nil-obj with no reference
                globalMu.pop(targetVarVal.val)

            targetVarVal.val = copyFromValValue
            globalMu[copyToVar] = targetVarVal

    elif (statement[0] == 'uncopy'):
        #['uncopy', 'Cell', 'cell', 'cellCopy']
        if statement[1] == 'int':
            assert globalMu[Gamma[statement[3]]]._type == 'int'
            while True:
                if globalMu[Gamma[statement[3]]].ref == 1:
                    break
            globalMu[Gamma[statement[3]]].val = 0
        else:
            assert globalMu[Gamma[statement[3]]]._type == 'Address'
            #check copied var reference is 1
            # no need to check var is nil
            while True:
                if globalMu[Gamma[statement[3]]].ref == 1:
                    break

            l = max(globalMu.keys()) + 1
            writeValToMu(Gamma, globalMu, statement[3], l)
            globalMu[l] ={'type' : statement[1], 'status' : 'nil'}


    elif (statement[0] == 'call' or statement[0] == 'uncall'):
        # ['call', 'tc', 'test', [args]]
        # ['call', 'test', [args]]
        # ['call', ['sieves', 'i'], 'setPrime', ['i']]
        if len(statement) == 4:  
            # call method for local or r1emote object
            if isinstance(statement[1], list):
                index = evalExp(Gamma, globalMu, statement[1][1])
                listAddr = globalMu[Gamma[statement[1][0]]].val
                objPointerAddr = globalMu[listAddr][index].val
                objAddr = globalMu[objPointerAddr].val
            else:
                objAddr = globalMu[Gamma[statement[1]]].val

            if (globalMu[objAddr]['status'] == 'nil'):
                print('Error : nil object can\'t be called.')
                return 'error'

            if ('gamma' in globalMu[objAddr].keys() ):
                # call method for local object

                t          = getType(globalMu[objAddr]['type'])
                statements = classMap[t]['methods'][statement[2]]['statements']
                funcArgs   = classMap[t]['methods'][statement[2]]['args']
                passedArgs = statement[3]
                localGamma = globalMu[objAddr]['gamma']

                if (len(funcArgs) != len(passedArgs)):
                    print('Error : number of arguments is not matched.')
                    return 'error'

                for i in range(len(funcArgs)):

                    varAddr = Gamma[statement[3][i]]

                    # type check
                    if globalMu[varAddr]._type == 'int':
                        assert funcArgs[i]['type'][0] == 'int'
                    else:
                       argObjAddr = globalMu[varAddr].val
                       if funcArgs[i]['type'][0] == 'separate': 
                           assert globalMu[argObjAddr]['type'][0] == 'separate'
                           assert funcArgs[i]['type'][1] == globalMu[argObjAddr]['type'][1]
                       else:
                           assert funcArgs[i]['type'][0] == globalMu[argObjAddr]['type'][0]

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
                # call method for remote object

                t          = getType(globalMu[objAddr]['type'])
                statements = classMap[t]['methods'][statement[2]]['statements']
                funcArgs   = classMap[t]['methods'][statement[2]]['args']

                callerAddr    = Gamma['this']
                callOrUncall  = statement[0]
                targetObjAddr = objAddr
                methodName    = statement[2]

                argsAddr      = []
                attachedFlag  = False
                assert len(funcArgs) == len(statement[3])
                for i in range(len(statement[3])):

                    varAddr = Gamma[statement[3][i]]

                    # type check
                    if globalMu[varAddr]._type == 'int':
                        assert funcArgs[i]['type'][0] == 'int'
                    else:
                       argObjAddr = globalMu[varAddr].val
                       if funcArgs[i]['type'][0] == 'separate': 
                           assert globalMu[argObjAddr]['type'][0] == 'separate'
                           assert funcArgs[i]['type'][1] == globalMu[argObjAddr]['type'][1]
                       else:
                           assert funcArgs[i]['type'][0] == globalMu[argObjAddr]['type'][0]

                    if funcArgs[i]['type'][0] != 'separate':
                        attachedFlag = True

                    refcountUp(globalMu, varAddr)
                    argsAddr.append(varAddr)

                q = globalMu[targetObjAddr]['methodQ']
                time.sleep(sys.float_info.min)

                if attachedFlag:
                    # one of the args is non-separete.
                    parent_conn, child_conn = mp.Pipe()
                    q.put([methodName, argsAddr, callOrUncall, callerAddr, child_conn])
                    msg = parent_conn.recv()
                else:
                    # all args are non-separete.
                    q.put([methodName, argsAddr, callOrUncall, callerAddr, None])


        elif len(statement) == 3:  
            # call method for this object
            objAddr = globalMu[Gamma['this']].val
            t          = getType(globalMu[objAddr]['type'])
            statements = classMap[t]['methods'][statement[1]]['statements']
            funcArgs   = classMap[t]['methods'][statement[1]]['args']
            passedArgs = statement[2]

            #local call use Same Gamma.

            for i in range(len(funcArgs)):
                varAddr = Gamma[statement[3][i]]
                # type check
                if globalMu[varAddr]._type == 'int':
                    assert funcArgs[i]['type'][0] == 'int'
                else:
                   argObjAddr = globalMu[varAddr].val
                   if funcArgs[i]['type'][0] == 'separate': 
                       assert globalMu[argObjAddr]['type'][0] == 'separate'
                       assert funcArgs[i]['type'][1] == globalMu[argObjAddr]['type'][1]
                   else:
                       assert funcArgs[i]['type'][0] == globalMu[argObjAddr]['type'][0]


            assert len(funcArgs) == len(passedArgs)
            localInvert = invert
            # here, already call/uncall is inverted.
            if (statement[0] == 'call' and invert):
                # call is inverted from uncall.
                # means uncall in uncall
                localInvert = not invert
                pass
            elif (statement[0] == 'call' and not invert):
                # call
                pass
            elif (statement[0] == 'uncall' and invert):
                # means call in uncall
                pass
            elif (statement[0] == 'uncall' and not invert):
                localInvert = not invert

            for i in range(len(funcArgs)):
                if (funcArgs[i]['name'] != passedArgs[i]):
                    Gamma[funcArgs[i]['name']] = Gamma[passedArgs[i]]


            runBlockStatement(classMap,
                              statements,
                              Gamma,
                              globalMu, localInvert)


            for i in range(len(funcArgs)):
                if (funcArgs[i]['name'] != passedArgs[i]):
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
            try:
                assert e2Evaled == True 
            except AssertionError:
                _, _, tb = sys.exc_info()
                traceback.print_tb(tb) # Fixed format
                tb_info = traceback.extract_tb(tb)
                filename, line, func, text = tb_info[-1]
                print('An error occurred on line {} in statement {}'.format(line, text))
                exit(1)
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

    elif (statement[0] == 'local'):
        # local - delocal
        # LOCAL:0 type:1 id:2 EQ exp:3  statements:4 DELOCAL type:5 id:6 EQ exp:7
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
            assertValue = evalExp(Gamma, globalMu, statement[7])
            addr = Gamma[statement[6]]

            assert  'int' == globalMu[l]._type
            assert statement[2] == statement[6]

            while True:
                if globalMu[l].ref == 1 and assertValue == globalMu[addr].val:
                    break

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

            assert statement[2] == statement[6]

            while True:
                if globalMu[addr].ref == 1 and assertValue == evalExp(Gamma, globalMu, statement[6]):
                    break

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
                callerObjAddr      = request[3] 

                procObjtype = globalMu[globalMu[Gamma['this']].val]['type']

                if 'require' in classMap[getType(procObjtype)]['methods'][methodName].keys():
                    if callORuncall == 'call':
                        exp = classMap[getType(procObjtype)]['methods'][methodName]['require']
                    else:
                        assert callORuncall == 'uncall'
                        exp = classMap[getType(procObjtype)]['methods'][methodName]['ensure']

                    e1Evaled = evalExp(Gamma, globalMu, exp)
                    if e1Evaled == False:
                        q.put(request)
                        continue
                    else:
                        pass

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

                    if (request[0]  == historyTop[0] and callerObjAddr == historyTop[3]) and ((historyTop[2] == 'call') and True):

                        pass
                    else:
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
            elif lenReq == 2:
                if (historyStack.qsize() == 0 and q.qsize() == 0):
                    flag = True 
                    for k,v in Gamma.items():
                        if globalMu[v]._type == 'int':
                            # integer deletable check = 0 - check
                            if globalMu[v].val != 0 or globalMu[v].ref != 1:
                                flag = False
                                break
                        elif globalMu[v]._type == 'Address':
                            listAddr = globalMu[v].val
                            if globalMu[listAddr]['type'][0] == 'list':
                                # list deletable check
                                if not 'status' in globalMu[listAddr].keys():
                                    flag = False
                                    break
                                elif 'status' in globalMu[listAddr].keys():
                                    if globalMu[listAddr]['status'] == 'nil':
                                        pass
                                else:
                                    pass
                            elif globalMu[listAddr]['type'][0] == 'separate':
                                # object deletable check
                                if globalMu[globalMu[v].val]['status'] != 'nil' or globalMu[v].ref != 1:
                                    if('this' == k) :
                                        continue 
                                    flag = False
                                    break
                            else:
                                raise Exception("not supported type")
                    if flag:
                        for k,v in Gamma.items():
                            if globalMu[v]._type == 'int':
                                globalMu.pop(v)
                            elif globalMu[v]._type == 'Address':
                                if k != 'this':
                                    globalMu.pop(globalMu[v].val)
                                globalMu.pop(v)

                        request[1].send('ready_delete')
                    else:
                        q.put(request)
                else:
                    q.put(request)








