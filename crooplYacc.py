import ply.yacc as yacc
import sys
import time

from crooplLexer import tokens
from crooplEval import   makeSeparatedProcess, Value
from crooplStoreLoop import makeMuManager

classMap = {}


def p_program(p):
    '''
    program :  classes
    '''


def p_classes(p):
    '''
    classes : classes class
    |
    '''


def p_class(p):
    '''
    class : CLASS className varDeclarations methods
    '''
    classMap[p[2]] = {"fields": p[3], "methods": p[4]}


def p_className(p):
    '''
    className : ID
    '''
    p[0] = p[1]


def p_varDeclarations(p):
    '''
    varDeclarations : varDeclarations varDeclaration
    |
    '''
    if (len(p) == 3):
        varDecls = p[1]
        varDecls[p[2][0]["name"]] = p[2][0]["type"]
        p[0] = varDecls
    else:
        p[0] = {}


def p_type(p):
    '''
    type : INT
    | ID
    | SEPARATE ID
    | INT LBRA RBRA
    | ID LBRA RBRA
    | SEPARATE ID LBRA RBRA
    '''
    if len(p) == 2:
        p[0] = [p[1]]
    elif len(p) == 3:
        p[0] = [p[1],p[2]]

    elif len(p) == 4:
        if p[1] == "separate":
            p[0] = [p[1], p[2], p[3]]
        else:
            p[0] = ['list', p[1]]
    elif len(p) == 5:
        p[0] = ['list', p[2], p[1]]


def p_arrayType(p):
    '''
    arrayType : ID LBRA exp RBRA
    | INT LBRA exp RBRA
    '''
    p[0] = [p[1], p[3]]


def p_methods(p):
    '''
    methods  : methods method
    |
    '''
    if len(p) == 3:
        methods = p[1]
        methods[p[2]["methodName"]] = p[2]
        p[0] = methods
    else:
        p[0] = {}


def p_method(p):
    '''
    method : METHOD ID LPAREN varDecCommas RPAREN REQUIRE exp statements ENSURE exp
    method : METHOD ID LPAREN varDecCommas RPAREN statements
    method : PRIVATE METHOD ID LPAREN varDecCommas RPAREN statements
    '''
    if len(p) == 7:
        p[0] = { "methodName": p[2], "args": p[4], "statements": p[6] }
    if len(p) == 8:
        p[0] = { "methodName": p[3], "args": p[5], "statements": p[7] }
    elif len(p) == 11:
        p[0] = {"methodName": p[2], "args": p[4], "statements": p[8], "require": p[7], "ensure": p[10] }

def p_varDeclaration(p):
    '''
    varDeclaration : type ID 
    '''
    p[0] = [{"name": p[2], "type": p[1]}]

def p_varDecCommas(p):
    '''
    varDecCommas : varDecCommas1
    |
    '''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = []

def p_varDecCommas1(p):
    '''
    varDecCommas1 : varDecCommas1 COMMA varDeclaration
    | varDeclaration
    '''
    if len(p) == 2:
        p[0] = p[1]
    else:
        varDeclCommas = p[1]
        varDeclCommas.append(p[3][0])
        p[0] = varDeclCommas


# varDeclaration  returns {"name": varName, "type": typeName}



def p_statements(p):
    '''
    statements :  statements statement
    |
    '''
    if len(p) == 1:
        p[0] = []
    else:
        statements = p[1]
        statements.append(p[2])
        p[0] = statements




def p_y(p):
    '''
    y : ID LBRA exp RBRA
    | ID
    '''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = [p[1], p[3]]

def p_id(p):
    '''
    id : ID 
    '''
    p[0] = [p[1]]


def p_arg(p):
    '''
    arg : y
    | exp
    | THIS 
    '''
    p[0] = p[1]


def p_anyIds(p):
    '''
    anyIds : anyIds1
    |
    '''
    if len(p) == 1:
        p[0] = []
    else:
        p[0] = p[1]

def p_anyIds1(p):
    '''
    anyIds1 : anyIds1 COMMA arg
    | arg
    '''
    if len(p) == 2:
        p[0] = [p[1]]
    if len(p) == 4:
        ids = p[1]
        p[0] = ids + [p[3]]


def p_statement(p):
    '''
    statement : y modOp exp
    | NEW arrayType ID
    | NEW SEPARATE arrayType ID
    | NEW SEPARATE ID y
    | NEW ID y
    | DELETE arrayType ID
    | DELETE SEPARATE ID y
    | DELETE ID y
    | SKIP
    | PRINT exp
    | PRINT STR
    | PRINT THIS
    | y SWAP y
    | COPY type y y
    | CALL   y WCOLON ID LPAREN anyIds RPAREN
    | CALL   y LPAREN anyIds RPAREN
    | UNCALL y WCOLON ID LPAREN anyIds RPAREN
    | UNCALL y LPAREN anyIds RPAREN
    | IF exp THEN statements ELSE statements FI exp
    | FROM exp DO statements LOOP statements UNTIL exp
    | LOCAL type y EQ exp  statements DELOCAL type y EQ exp
    '''
    if len(p) == 2:
        p[0] = [p[1]]
    elif len(p) == 3:
        p[0] = [p[1], p[2]]
    elif len(p) == 4:
        if p[1] == 'new' or p[1] == 'delete':
            p[0] = [p[1], p[2], p[3]]
        else:
            p[0] = ['assignment', p[2], p[1], p[3]]
    elif len(p) == 5: 
        if p[1] == 'new' or p[1] == 'delete':
            p[0] = [p[1], p[3], p[4], p[2]]
        else:
            p[0] = [p[1], p[2], p[3], p[4]]
    elif len(p) == 6: # local call
        p[0] = [p[1], p[2], p[4]]
    elif len(p) == 8: # call object method
        p[0] = [p[1], p[2], p[4], p[6]]
    elif len(p) == 9: # if or from do until
        p[0] = [p[1], p[2], p[4], p[6], p[8]]
    elif len(p) == 12: # local-delocal
        p[0] = [p[1], p[2], p[3], p[5], p[6], p[8], p[9], p[11]]

def p_modOp(p):
    '''
    modOp : MODADD
    | MODSUB
    | MODXOR
    '''
    if p[1] == '+=':
        p[0] = "+="
    elif p[1] == '-=':
        p[0] = "-="
    elif p[1] == '^=':
        p[0] = '^='


precedence = (
    ('left', 'AND'),
    ('left', 'XOR'),
    ('nonassoc', 'EQ', 'NEQ'),
    ('left', 'ADD', 'SUB'),
    ('left', 'MUL', 'DIV', 'MOD'),
)


def p_exp(p):
    '''
    exp : NUMBER
    | y
    | NIL 
    | exp MUL exp
    | exp DIV exp
    | exp ADD exp
    | exp SUB exp
    | exp EQ exp
    | exp NEQ exp
    | exp AND exp
    | exp GT exp
    | exp GEQ exp
    | exp LT exp
    | exp LEQ exp
    | exp MOD exp
    | LPAREN exp RPAREN
    '''

    if (len(p) == 2):
        p[0] = p[1]
    elif (len(p) == 4):
        if p[2] == '+':
            p[0] = [p[1], "+", p[3]]
        elif p[2] == '-':
            p[0] = [p[1], "-", p[3]]
        elif p[2] == '*':
            p[0] = [p[1], "*", p[3]]
        elif p[2] == '/':
            p[0] = [p[1], "/", p[3]]
        elif p[2] == '%':
            p[0] = [p[1], "%", p[3]]
        elif p[2] == '&':
            p[0] = [p[1], "&", p[3]]
        elif p[2] == '=':
            p[0] = [p[1], "=", p[3]]
        elif p[2] == '!=':
            p[0] = [p[1], "!=", p[3]]
        elif p[2] == '>':
            p[0] = [p[1], ">", p[3]]
        elif p[2] == '<':
            p[0] = [p[1], "<", p[3]]
        elif p[2] == '<=':
            p[0] = [p[1], "<=", p[3]]
        elif p[2] == '>=':
            p[0] = [p[1], ">=", p[3]]
        elif p[1] == '(':
            p[0] = p[2]


def yacc_test():
    # open file
    args = sys.argv

    if len(args) == 1:
        raise Exception("filename not provided.")

    f = open(args[-1], 'r')
    data = f.read()
    f.close()

    # parse input program
    parser = yacc.yacc()
    parser.parse(data)

    # nil-init Program object in Mu.
    m = mp.Manager()
    globalMu = m.dict()
    globalMu[0]  = Value(None, 'Address')
    objAddrValue = len(globalMu.keys())
    globalMu[0]  = Value(objAddrValue, 'Address')
    globalMu[objAddrValue] = {'status': 'nil', 'type' : ['separate','Program']}

    
    # generate Process
    # new Program object.
    initProcess = makeSeparatedProcess(classMap, globalMu, 0)
    muManager = makeMuManager(globalMu, m)
    

    if initProcess == None:
        raise Exception("initProcess is None.")

    q = globalMu[globalMu[0].val]['methodQ']


    parent_conn, child_conn = mp.Pipe()

    # request process to run main func
    q.put(["main", [], "call", -1, child_conn])

    
    '''
    inp = input("Press Enter to continue...\n")
    if inp == "exit":
    '''

    parent_conn.recv()

    # break loop of main process
    parent_conn, child_conn = mp.Pipe()
    q.put(['deleteMain', child_conn])
    deletable = parent_conn.recv()
    assert deletable == 'ready_delete'

    # break loop of Store
    managerQ = globalMu[-2]
    parent_conn, child_conn = mp.Pipe()
    managerQ.put(['delete', child_conn])
    deletable = parent_conn.recv()
    assert deletable == 'ready_delete'

    initProcess.kill()
    muManager.kill()

    time.sleep(sys.float_info.min)

    initProcess.join()
    muManager.join()
    initProcess.close()
    muManager.close()
    m.shutdown()



if __name__ == '__main__':
    import multiprocessing as mp
    mp.set_start_method('spawn', True)
    yacc_test()
