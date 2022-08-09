#!/usr/bin/python3
from interface_parse import Interface, ArgDirection

class InterfaceGen:
    def __str__(self):

        return str(self.__class__) + ": " + str(self.__dict__)

    def __init__(self, interface, filebasename , wordsize):

        self.interface = interface
        self.filebasename = filebasename
        self.wordsize = wordsize

        
class InterfacePrint(InterfaceGen):
    def __str__(self):

        return str(self.__class__) + ": " + str(self.__dict__)

    def __init__(self, interface, filebasename = '', wordsize=8):

        super().__init__(interface, filebasename, wordsize)
        
        for i in self.interface.includes:
            print(f'#include <{i.name}>')

        for i in self.interface.defines:
            print(f'#define {i.name} ({i.value})')

        for i in self.interface.methods:
            print(f'{i.name}[id={i.id}](',end='')
            for a in i.args[:-1]:
                if a.direction == ArgDirection.IN:
                    print(f'{a.ctype}[size={a.size}] {a.name}',end=', ')
                else:
                    print(f'{a.ctype}[size={a.size}] *{a.name}',end=', ')
            if i.args[-1] != None:
                a = i.args[-1] 
                if a.direction == ArgDirection.IN:
                    print(f'{a.ctype}[size={a.size}] {a.name}',end='')
                else:
                    print(f'{a.ctype}[size={a.size}] *{a.name}',end='')
                
            print(f') -> {i.return_type}')
            
            
