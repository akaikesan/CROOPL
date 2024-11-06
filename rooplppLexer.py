import ply.lex as lex

tokens = (
    'PRIVATE',
    'NUMBER',
    'STR',
    'ID',
    'CONST',
    'STRING',
    'MUL',
    'DIV',
    'MOD',
    'ADD',
    'SUB',
    'LT',
    'LEQ',
    'GT',
    'GEQ',
    'EQ',
    'NEQ',
    'NE',
    'BAND',
    'XOR',
    'BOR',
    'AND',
    'OR',
    'SWAP',
    'COMMA',
    'WCOLON',
    'MODADD',
    'MODSUB',
    'MODXOR',
    'COLON',
    'LPAREN',
    'RPAREN',
    'LBRA',
    'RBRA',
    'CLASS',
    'INHERITS',
    'METHOD',
    'REQUIRE',
    'ENSURE',
    'CALL',
    'UNCALL',
    'CONSTRUCT',
    'DESTRUCT',
    'SKIP',
    'FROM',
    'DO',
    'LOOP',
    'UNTIL',
    'FOR',
    'IN',
    'END',
    'SWITCH',
    'HCTIWS',
    'CASE',
    'FCASE',
    'ECASE',
    'ESAC',
    'BREAK',
    'DEFAULT',
    'INT',
    'NIL',
    'IF',
    'THEN',
    'ELSE',
    'FI',
    'LOCAL',
    'DELOCAL',
    'NEW',
    'DELETE',
    'COPY',
    'UNCOPY',
    'SHOW',
    'PRINT',
    'EOF',
    'PLUS',
    'TIMES',
    'MINUS',
    'DIVIDE',
    'LBRACE',
    'RBRACE',
    'SEPARATE',
    'ATTACHED',
    'DETACHABLE',
)

reserved = {
    'class': 'CLASS',
    'private': 'PRIVATE',
    'copy': 'COPY',
    'print': 'PRINT',
    'skip': 'SKIP',
    'new': 'NEW',
    'delete': 'DELETE',
    'from': 'FROM',
    'if': 'IF',
    'do': 'DO',
    'loop': 'LOOP',
    'until': 'UNTIL',
    'fi': 'FI',
    'then': 'THEN',
    'else': 'ELSE',
    'while': 'WHILE',
    'method': 'METHOD',
    'require': 'REQUIRE',
    'ensure': 'ENSURE',
    'int': 'INT',
    'call': 'CALL',
    'uncall': 'UNCALL',
    'local': 'LOCAL',
    'delocal': 'DELOCAL',
    'separate': 'SEPARATE',
    'nil': 'NIL',
    'attached': 'ATTACHED',
    'detachable': 'DETACHABLE',
}


def t_ID(t):
    r'[a-zA-Z][a-zA-Z0-9]*'
    t.type = reserved.get(t.value, 'ID')
    return t


def t_NEW(t):
    r'new'
    t.type = reserved.get(t.value, 'NEW')
    return t

def t_SKIP(t):
    r'skip'
    t.type = reserved.get(t.value, 'SKIP')
    return t

def t_NIL(t):
    r'nil'
    t.type = reserved.get(t.value, 'NIL')
    return t

def t_CALL(t):
    r'call'
    t.type = reserved.get(t.value, 'CALL')
    return t


def t_UNCALL(t):
    r'uncall'
    t.type = reserved.get(t.value, 'UNCALL')
    return t


def t_ELSE(t):
    r'else'
    t.type = reserved.get(t.value, 'ELSE')
    return t


def t_FI(t):
    r'fi'
    t.type = reserved.get(t.value, 'FI')
    return t


def t_IF(t):
    r'if'
    t.type = reserved.get(t.value, 'IF')
    return t


def t_THEN(t):
    r'then'
    t.type = reserved.get(t.value, 'THEN')
    return t


def t_FROM(t):
    r'from'
    t.type = reserved.get(t.value, 'FROM')
    return t


def t_DO(t):
    r'do'
    t.type = reserved.get(t.value, 'DO')
    return t


def t_LOOP(t):
    r'loop'
    t.type = reserved.get(t.value, 'loop')
    return t


def t_UNTIL(t):
    r'until'
    t.type = reserved.get(t.value, 'until')
    return t


t_CLASS = 'class'
t_DELETE = 'delete'
t_COPY= 'copy'
t_PRINT = 'print'
t_COMMA = ','
t_METHOD = 'method'
t_REQUIRE= 'require'
t_ENSURE= 'ensure'
t_COLON = ':'
t_WCOLON = '::'
t_ADD = r'\+'
t_GT= r'>'
t_LT= r'<'
t_GEQ= r'>='
t_LEQ= r'<='
t_MODADD = r'\+='
t_MODSUB = r'-='
t_MODXOR = r'\^='
t_SWAP = r'<=>'
t_EQ = r'='
t_NEQ = r'!='
t_SUB = r'-'
t_AND = r'&'
t_MOD = r'%'
t_MUL = r'\*'
t_DIV = r'/'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LBRA = r'\['
t_RBRA = r'\]'
t_NUMBER = r'(0 | [1-9][0-9]*)'
t_LBRACE = '{'
t_RBRACE = '}'
t_STR= r'\".*\"'
# A string containing ignored characters (spaces and tabs)
t_ignore_COMMENT = r'//.*'
t_ignore = ' \t'
# A regular expression rule with some action code




def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


# Error handling rule


def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)


# Build the lexer
lexer = lex.lex()


def lex_test():
    f = open('data.txt', 'r')
    data = f.read()
    f.close()

    lexer.input(data)

    while True:
        tok = lexer.token()
        if not tok:
            break
        print(tok)
    print(lexer.lineno)


if __name__ == '__main__':
    lex_test()
