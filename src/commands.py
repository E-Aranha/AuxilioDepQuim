from database_handler import DatabaseHandler
from psycopg2._psycopg import connection, cursor, OperationalError, Error
from tabulate import tabulate
import sys

def getInput(startString: str = '>> '):
    return input(startString)

# define a function that handles and parses psycopg2 exceptions
def print_psycopg2_exception(err):
    # get details about the exception
    err_type, err_obj, traceback = sys.exc_info()

    # get the line number when exception occured
    line_num = traceback.tb_lineno

    # print the connect() error
    print ("\npsycopg2 ERROR:", err, "on line number:", line_num)
    print ("psycopg2 traceback:", traceback, "-- type:", err_type)

    # psycopg2 extensions.Diagnostics object attribute
    print ("\nextensions.Diagnostics:", err.diag)

    # print the pgcode and pgerror exceptions
    print ("pgerror:", err.pgerror)
    print ("pgcode:", err.pgcode, "\n")


def outputToScreen(cursor: cursor) -> str:

    table = [list(result) for result in cursor.fetchall() ]
    table.insert(0, [desc[0].upper() for desc in cursor.description])

    return tabulate(table)

class Funcionalidades:
    instances = []

    dbHandler = DatabaseHandler()

    def __init__(self, name: str, handler: any, help: str = None) -> None:
        self.name = name
        self.handler = handler
        self.help = help

    def run(self, args, *param):
        conn: connection
        cur: cursor
        conn, cur = self.dbHandler.connectToDatabase()
        outputList = self.handler(cur, args, param)
        self.dbHandler.disconnectFromDatabase(conn=conn, cur=cur, commit = True)
        return outputList

    def displayHelp(self):
        print(self.help or "...sem mensagem...")


def funcionalidade(name: str, help: str = None):
    def decorator(handler):
        Funcionalidades.instances.append(
            Funcionalidades(name, handler, help=help))
        return handler

    return decorator


### CRIACAO DAS FUNCIONALIDADES ###

### Rodar o consultas.sql ###

@funcionalidade('consultas', help="Roda o arquivo de consultas.sql")
def runConsultasSQL(cur: cursor, _, __):
    # Open and read all
    fd = open('../data/consultas.sql', 'r')
    sqlFile = fd.read()
    fd.close()


    # Split at ;
    sqlCommands = sqlFile.replace("\n", " ").split(';')
    sqlCommands.pop()

    # Remove comments
    for index, cmd in enumerate(sqlCommands):
        if(cmd.find('--') != -1):
            sqlCommands.pop(index)

    outputList = []

    # Execute the queries
    for command in sqlCommands:
        outputList.append(f"\nRODANDO CONSULTA:   {command}\n")
        try:
            cur.execute(command)
        except:
            print(f"[ ERRO ] Commando com erro: {command}")
            return

        if cur.row_factory == 0:
            print("[ INFO ] Sem resultados ")
        else:
            outputList.append(outputToScreen(cur))
    
    return outputList

@funcionalidade("runSQL", help="Roda um sql")
def runSQL(cur: cursor, args, *param):
    """Recebe uma string como parametro e executa ela como um codigo SQL.

    Args:
        cur (cursor): cursor de manipulação da database
        args (_type_): string com a consulta

    Returns:
        _type_: retorna o resultado da consulta de forma tabular/formatada. Pode retornar também ERRO ou Sem resultados.
    """
    sql = args.replace('\n', '')
    try:
        cur.execute(sql)
    except Error as e:

        return("[ ERRO ] Commando com erro" + "\n" + str(e))

    if cur.row_factory == 0:
        return("[ INFO ] Sem resultados ")
    else:
        return outputToScreen(cur)
    

@funcionalidade("tableNames", help="retorna nome das tabelas")
def tableName(cur: cursor):
    """Itera sobre a base de dados a fim de gerar uma lista com o nome de todas as tabelas

    Args:
        cur (cursor): cursor de manipulação da databse

    """
    tables = "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"
    try:
        cur.execute(tables)
    except Exception as e:
        print(e)
    table = [result[0] for result in cur.fetchall() ]
    return(table)


@funcionalidade("columnNames", help="retorna atributos")
def columnNames(cur: cursor, args):
    """Dada uma tabela, itera em cima desta e retorna uma lista com o nome de suas colunas

    Args:
        cur (cursor): cursor de manipulação da database
        args (_type_): string com o nome da tabela a ser iterada
    """
    coluna = str(args)
    try:
        cur.execute("SELECT * FROM " + coluna + " WHERE 1=0;")
    except Exception as e:
        print(e)
    table = [result for result in cur.fetchall() ]
    table.insert(0, [desc[0].upper() for desc in cur.description])
    return(table[0])

@funcionalidade("directQuery", help="insere centro")
def directQuery(cur: cursor, args,):
    cur.execute("SELECT "+ args[1] + " FROM "+ args[0] + ";")
    return outputToScreen(cur)


@funcionalidade("insertCentro", help="insere centro")
def insertCentro(cur: cursor, args):
    """Função para geração de um SQL de inserção de novos valores dentro de centro

    Args:
        cur (cursor): cursor de manipulação da database
        args (_type_): cnpj, caixa, nome, local e presidente a serem inseridos
    """
    sqlCentro = "INSERT INTO CENTRO(CNPJ,CAIXA,NOME, LOCAL,PRESIDENTE) VALUES (%s,%s,%s,%s,%s);"
    try:
        cur.execute(sqlCentro, args)
    except Exception as e:
        return(-1)

@funcionalidade("insertEmp", help="insere empresa")
def insertEmp(cur: cursor, args):
    """Função para realizar a inserção de uma nova empresa. Inicialmente, os valores são inseridos em Terceiros e posteriormente, em Empresa Parceira

    Args:
        cur (cursor): cur (cursor): cursor de manipulação da database
        args (_type_): Nome, Cnpj, Numero de funcionarios e numero maximo de funcionarios

    Returns:
        _type_: retorna um ouput com o retorno do cursor para a consulta em questão, ou -1 em caso de erro
    """
    sqlTerceiros = "INSERT INTO TERCEIROS (NUCPFCNPJ,NOME,TIPO) VALUES (%s, %s,'EMPRESA PARCEIRA');"
    data = (args[1], args[0])
    try:
        cur.execute(sqlTerceiros, data)
    except Exception as e:
        print(e)
        return(-1)
    
    sqlEmpresas = "INSERT INTO EMPRESAS_PARCEIRAS(CNPJ, NUFUNCIONARIOS, MAXFUNCIONARIOS) VALUES (%s, %s, %s);"
    try:
        data = (args[1], args[2], args[3])
        cur.execute(sqlEmpresas, data)
    except Exception as e:
        print(e)
        return(-1)

    cur.execute("SELECT NOME FROM TERCEIROS;")
    print(outputToScreen(cur))
    return outputToScreen(cur)

@funcionalidade("insertFunc", help="insereFuncionario")
def insertFunc(cur: cursor, args,):
    """Gera um sql para a inserção de um novo funcionario, colocando-o inicialmente como pessoa fisica, depois na tabela do tipo de pessoa e por fim como funcionario

    Args:
        cur (cursor): cursor de manipulação da database
        args (_type_): Nome e cnpj do funcionario

    Returns:
        _type_: -1 em caso de erro ou o retorno do cursor para a inserção
    """
    sqlTerceiros = "INSERT INTO TERCEIROS (NUCPFCNPJ,NOME,TIPO) VALUES (%s, %s,'PESSOA FISICA');"
    try:
        data = (args[1], args[0])
        cur.execute(sqlTerceiros, data)
    except Exception as e:
        print(e)
        return(-1)

    sqlPF = "INSERT INTO PESSOA_FISICA(CPF) VALUES (%s);"
    sqlTipo = "INSERT INTO TIPO_PESSOA_FISICA(CPF,TIPOPF) VALUES (%s,'FUNCIONARIO');"
    sqlFunc = "INSERT INTO FUNCIONARIO(CPF,CENTRO) VALUES (%s, %s);"

    try:
        cur.execute(sqlPF, [args[1]])
        cur.execute(sqlTipo, [args[1]])

        data = (args[1], args[2])
        cur.execute(sqlFunc, data)

    except:
        return(-1)

    return outputToScreen(cur)

@funcionalidade("lista terceiro", help="Lista o terceiro pesquisado por nome")
def listCitites(cur: cursor, _):
    # pegar input da cidade

    nucpfcnpj = getInput("Numero: ")

    try:
        cur.execute(
            f"SELECT * FROM terceiros t WHERE t.nucpfcnpj = '{nucpfcnpj}';")
    except:
        
        raise Exception(f"Erro ao pegar dados da cidade {nucpfcnpj}")

    if cur.rowcount == 0:
        print("Nao ha terceiros com esse numero")
    else:
        outputToScreen(cur)
