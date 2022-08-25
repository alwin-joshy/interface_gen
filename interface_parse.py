#!/usr/bin/python3
import sys, argparse
import xml.etree.ElementTree as ET
from enum import Enum,auto
import string

class Scope(Enum):
    XML = auto()
    INTERFACE = auto()
    METHOD = auto()
    INCLUDE = auto()
    DEFINE = auto()
    CTYPE=auto()
    IN = auto()
    OUT = auto()
    INOUT = auto()

class ArgDirection(Enum):
    IN = auto()
    OUT = auto()
    INOUT = auto()

class IdlArgTypes(Enum):
    VALUE = auto()
    CAP = auto()
    
class Interface:

    def __init__(self, disp, err, pre):
        self.dispatch_func = disp
        self.server_prefix = pre
        self.error_func = err
        self.methods = []
        self.includes = []
        self.defines = []
        
    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    def add_method(self, method):
        self.methods.append(method)

    def add_include(self, inc):
        self.includes.append(inc)
        
    def add_define(self, d):
        self.defines.append(d)
        
class Include():
    def __init__(self,header,client=True, server=True):
        self.header = header
        self.client = client
        self.server = server

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

class Define:
    def __init__(self,name,value):
        self.name = name
        self.value = value

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)
    
    
class CType:
    def __init__(self, name, arg_type):
        self.name = name
        self.arg_type = arg_type
    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

class Method:
    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)
    def __init__(self, name, id, return_type, cap):
        self.name = name
        self.id = id
        self.return_type = return_type
        self.cap = cap
        self.args = []

    def add_arg(self, arg):
        self.args.append(arg)

class Arg:
    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)
    def __init__(self, ctype, name, arg_type, direction, const):
        self.ctype = ctype
        self.name = name
        self.arg_type = arg_type
        self.direction = direction
        self.const = const
        
    
class InterfaceParser:

    def __init__(self, wordsize):
        self.wordsize = wordsize
        self.scope = [Scope.XML]
        self.ctypes = dict()
        self.args = []
        self.wordsize = 0
        self.interface = None
    
    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    def start(self, tag, attrib): # Called for each opening tag
        if tag == 'interface':
            if self.scope[-1] != Scope.XML:
                raise RuntimeError('Only a single interface allowed')
            else:
                self.scope.append(Scope.INTERFACE)
                self.interface = Interface(attrib['dispatch_func'], attrib['error_func'], attrib['server_prefix']);
                
        elif tag == 'include':
            if self.scope[-1] != Scope.INTERFACE:
                raise RuntimeError('Include must be in interface scope')
            else:
                self.scope.append(Scope.INCLUDE)
                client=True
                server=True
                if 'client' in attrib.keys():
                    client = str(attrib['client']).lower() == 'true'
                if 'server' in attrib.keys():
                    server = attrib['server'].lower() == 'true'
                self.interface.add_include(Include(attrib['header'],client,server))
                
        elif tag == 'define':
            if self.scope[-1] != Scope.INTERFACE:
                raise RuntimeError('Define must be in interface scope')
            else:
                self.scope.append(Scope.DEFINE)
                self.interface.add_define(Define(attrib['name'],attrib['value']))
                
        elif tag == 'ctype':
            if self.scope[-1] != Scope.INTERFACE:
                raise RuntimeError('Define must be in <interface> scope')
            else:
                self.scope.append(Scope.CTYPE)
                self.ctypes[attrib['name']] = CType(attrib['name'], attrib['type'])
        
        elif tag == 'method':
            if self.scope[-1] != Scope.INTERFACE:
                raise RuntimeError('Method definition outside interface scope')
            else:
                self.scope.append(Scope.METHOD)
                if attrib['return_type'] in self.ctypes:
                    # More extensive checks required
                    self.cur_method = Method(attrib['name'],int(attrib['id']),attrib['return_type'],attrib['clientcap'])
                else:
                    raise RuntimeError('method return type not defined "%s"' % attrib['return_type'] )
                
        elif tag == 'in':
            if self.scope[-1] != Scope.METHOD:
                raise RuntimeError('arg definition outside method scope')
            else:
                self.scope.append(Scope.IN)
                ctype = attrib['ctype']
                if 'const' in attrib.keys():
                    const = attrib['const']
                else:
                    const = 'false'
                if ctype in self.ctypes:
                    
                    self.cur_method.add_arg(Arg(attrib['ctype'],
                                                attrib['name'],
                                                self.ctypes[ctype].arg_type,
                                                ArgDirection.IN,
                                                const))
                else:
                    raise RuntimeError(f'Args ctype not defined "{ctype}"')
                
        elif tag == 'out':
            if self.scope[-1] != Scope.METHOD:
                raise RuntimeError('arg definition outside method scope')
            else:
                self.scope.append(Scope.OUT)
                ctype = attrib['ctype']
                if ctype in self.ctypes:
                    
                    self.cur_method.add_arg(Arg(attrib['ctype'],
                                                attrib['name'],
                                                self.ctypes[ctype].arg_type,
                                                ArgDirection.OUT, 'false'))
                else:
                    raise RuntimeError('Args ctype not defined')

        elif tag == 'inout':
            if self.scope[-1] != Scope.METHOD:
                raise RuntimeError('arg definition outside method scope')
            else:
                self.scope.append(Scope.INOUT)
                ctype = attrib['ctype']
                if ctype in self.ctypes:
                    
                    self.cur_method.add_arg(Arg(attrib['ctype'],
                                                attrib['name'],
                                                self.ctypes[ctype].arg_type,
                                                ArgDirection.INOUT, 'false'))
                else:
                    raise RuntimeError('Args ctype not defined')

        else:
            raise RuntimeError(f'Unknown xml tag: {tag}')
        
    def end(self, tag):           # Called for each closing tag.
        if tag == 'interface':
            if self.scope[-1] != Scope.INTERFACE:
                raise RuntimeError('Missing <interface> scope start')
            else:
                self.scope.pop()
        elif tag == 'include':
            if self.scope[-1] != Scope.INCLUDE:
                raise RuntimeError('Missing <include> scope start')
            else:
                self.scope.pop()
        elif tag == 'define':
            if self.scope[-1] != Scope.DEFINE:
                raise RuntimeError('Missing <define> start')
            else:
                self.scope.pop()
        elif tag == 'ctype':
            if self.scope[-1] != Scope.CTYPE:
                raise RuntimeError('Missing <ctype> scope start')
            else:
                self.scope.pop()
        elif tag == 'method':
            if self.scope[-1] != Scope.METHOD:
                raise RuntimeError('Missing method start')
            else:
                self.scope.pop()
                self.interface.add_method(self.cur_method)
                
        elif tag == 'in':
            if self.scope[-1] != Scope.IN:
                raise RuntimeError('Missing <in> arg start')
            else:
                self.scope.pop()
        elif tag == 'out':
            if self.scope[-1] != Scope.OUT:
                raise RuntimeError('Missing <out> arg start')
            else:
                self.scope.pop()
        elif tag == 'inout':
            if self.scope[-1] != Scope.INOUT:
                raise RuntimeError('Missing <inout> arg start')
            else:
                self.scope.pop()
        else:
            raise RuntimeError(f'Unknown xml tag: {tag}')
        
    def data(self, data):
        if data.translate({ord(c): None for c in string.whitespace}) != '':
            raise RuntimeError(f'Unexpected data in the XML: {data}')
        
    def close(self):              # Called when all data has been parsed.
            if self.scope[-1] != Scope.XML:
                raise RuntimeError('Premature end of file')
            else:
                return self.interface



