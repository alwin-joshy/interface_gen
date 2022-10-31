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
    CAPIN = auto()
    CAPOUT = auto()
    INOUT = auto()
    STRIN = auto()

class ArgDirection(Enum):
    IN = auto()
    OUT = auto()
    INOUT = auto()

#class IdlArgType(Enum):
#    VALUE = auto()
#    CAP = auto()
    
class Interface:

    def __init__(self, disp, err, pre, croot, cdepth):
        self.dispatch_func = disp
        self.server_prefix = pre
        self.error_func = err
        self.client_cspace_root = croot
        self.client_cspace_depth = cdepth
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
    
    
# class CType:
#     def __init__(self, name, arg_type):
#         self.name = name
#         self.arg_type = arg_type
#     def __str__(self):
#         return str(self.__class__) + ": " + str(self.__dict__)

class Method:
    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)
    def __init__(self, name, id, return_type, invocation_is_arg, invocation_cap):
        self.name = name
        self.id = id
        self.return_type = return_type
        self.invocation_is_arg = invocation_is_arg
        self.invocation_cap = invocation_cap
        self.args = []
        self.cap_args = []
        self.str_args = []

    def add_arg(self, arg):
        self.args.append(arg)
        
    def add_cap_arg(self, arg):
        self.cap_args.append(arg)

    def add_str_arg(self, arg):
        self.str_args.append(arg)

class Arg:
    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)
    def __init__(self, ctype, name, direction, const):
        self.ctype = ctype
        self.name = name
        self.direction = direction
        self.const = const

class CapArg:
    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    def __init__(self, ctype, name, direction):
        self.ctype = ctype
        self.name = name
        self.direction = direction
        
class StrArg:
    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    def __init__(self, name, direction):
        self.name = name
        self.direction = direction
        
    
class InterfaceParser:

    def __init__(self, wordsize):
        self.wordsize = wordsize
        self.scope = [Scope.XML]
#        self.ctypes = dict()
        self.args = []
        self.wordsize = 0
        self.interface = None
        self.highest_method_id = 0

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    def start(self, tag, attrib): # Called for each opening tag
        if tag == 'interface':
            if self.scope[-1] != Scope.XML:
                raise RuntimeError('Only a single interface allowed')
            else:
                self.scope.append(Scope.INTERFACE)
                if 'client_cspace_root' in attrib.keys():
                    cspace=attrib['client_cspace_root']
                else:
                    cspace=""
                    
                if 'client_cspace_depth' in attrib.keys():
                    cdepth=attrib['client_cspace_depth']
                else:
                    cdepth=""
                    
                self.interface = Interface(attrib['dispatch_func'], attrib['error_func'], attrib['server_prefix'],cspace,cdepth);
                
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
                
        # elif tag == 'ctype':
        #     if self.scope[-1] != Scope.INTERFACE:
        #         raise RuntimeError('Define must be in <interface> scope')
        #     else:
        #         self.scope.append(Scope.CTYPE)
        #         self.ctypes[attrib['name']] = CType(attrib['name'], attrib['type'])
        
        elif tag == 'method':
            if self.scope[-1] != Scope.INTERFACE:
                raise RuntimeError('Method definition outside interface scope')
            else:
                self.scope.append(Scope.METHOD)
                # More extensive checks required
                if 'return_type' not in attrib.keys():
                    rt = 'seL4_MessageInfo_t'
                else:
                    rt = attrib['return_type']

                id = 0;
                if (attrib["id"].isdigit()):
                    id = int(attrib["id"])
                    if (id > self.highest_method_id):
                        self.highest_method_id = id
                    else:
                        raise RuntimeError("Have functions in order please")
                elif (attrib["id"] == "*"):
                    if (self.highest_method_id == 0):
                        raise RuntimeError("At least give the first method an ID")
                    self.highest_method_id += 1
                    id = self.highest_method_id
                else:
                    raise RuntimeError("Invalid method id")
                self.cur_method = Method(attrib['name'],id,rt, attrib["invocation_is_arg"].lower() == 'true', attrib['invocation_cap'])

                
        elif tag == 'in':
            if self.scope[-1] != Scope.METHOD:
                raise RuntimeError('arg definition outside method scope' + attrib['name'])
            else:
                self.scope.append(Scope.IN)

                if 'const' in attrib.keys():
                    const = (attrib['const'].lower() == 'true')
                else:
                    const = False
                    
                self.cur_method.add_arg(Arg(attrib['ctype'],
                                                attrib['name'],
                                                ArgDirection.IN,
                                                const))
                                
        elif tag == 'out':
            if self.scope[-1] != Scope.METHOD:
                raise RuntimeError('arg definition outside method scope')
            else:
                self.scope.append(Scope.OUT)
                    
                self.cur_method.add_arg(Arg(attrib['ctype'],
                                                attrib['name'],
                                                ArgDirection.OUT, False))

        elif tag == 'inout':
            if self.scope[-1] != Scope.METHOD:
                raise RuntimeError('arg definition outside method scope')
            else:
                self.scope.append(Scope.INOUT)
                    
                self.cur_method.add_arg(Arg(attrib['ctype'],
                                            attrib['name'],
                                            ArgDirection.INOUT, False))

        elif tag == 'capin':
            if self.scope[-1] != Scope.METHOD:
                raise RuntimeError('arg definition outside method scope')
            else:
                self.scope.append(Scope.CAPIN)
                    
                self.cur_method.add_cap_arg(CapArg(attrib['ctype'],
                                            attrib['name'],
                                            ArgDirection.IN))

        elif tag == 'capout':
            if self.scope[-1] != Scope.METHOD:
                raise RuntimeError('arg definition outside method scope')
            else:
                self.scope.append(Scope.CAPOUT)
                    
                self.cur_method.add_cap_arg(CapArg(attrib['ctype'],
                                            attrib['name'],
                                            ArgDirection.OUT))
        elif tag == 'strin':
            if self.scope[-1] != Scope.METHOD:
                raise RuntimeError('arg definition outside method scope')
            else:
                self.scope.append(Scope.STRIN)
                    
                self.cur_method.add_str_arg(StrArg(attrib['name'],
                                                   ArgDirection.IN))
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
        elif tag == 'capin':
            if self.scope[-1] != Scope.CAPIN:
                raise RuntimeError('Missing <capin> arg start')
            else:
                self.scope.pop()
        elif tag == 'capout':
            if self.scope[-1] != Scope.CAPOUT:
                raise RuntimeError('Missing <capout> arg start')
            else:
                self.scope.pop()
        elif tag == 'strin':
            if self.scope[-1] != Scope.STRIN:
                raise RuntimeError('Missing <strin> arg start')
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



