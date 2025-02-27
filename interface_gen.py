#!/usr/bin/python3
from interface_parse import Interface, ArgDirection, Method

class InterfaceGen:
    preamble = '''
    /* This file is automatically generated, DO NOT EDIT */
    '''
    def __str__(self):

        return str(self.__class__) + ": " + str(self.__dict__)

    def __init__(self, interface, filebasename , wordsize):

        self.interface = interface
        self.filebasename = filebasename
        self.wordsize = wordsize

    def formatarg(self,a):
        if a.const:
            const = 'const '
        else:
            const=''
        if a.direction == ArgDirection.IN:
            return f'{const}{a.ctype} {a.name}'
        else:
            return f'{a.ctype} *{a.name}'

    def formatcaparg(self,a):
        return f'{a.ctype} {a.name}'



    def ipc_in_struct_name(self,method : str):
        return f'{method}_ipc_in'

    def ipc_out_struct_name(self,method: str):
        return f'{method}_ipc_out'

    def gen_ipc_in_struct(self,method: Method, indent='', name_prefix=''):
        buf=''
        buf=buf+f'{indent}struct {name_prefix}{self.ipc_in_struct_name(method.name)} {{'+'\n'
        for a in method.args:
            if a.direction != ArgDirection.OUT:
                if a.const and a.direction == ArgDirection.IN and '*' in a.ctype:
                    # super hacky check if passing const pointer by value
                    # passing values, const is discarded
                    const = 'const '
                else:
                    const=''
                buf=buf+f'{indent}    {const}{a.ctype} {a.name};'+'\n'
        buf=buf+f'{indent}}};'+'\n'
        return buf

    def gen_ipc_out_struct(self, method: Method, indent='',name_prefix=''):
        buf=''
        buf=buf+f'{indent}struct {name_prefix}{self.ipc_out_struct_name(method.name)} {{'+'\n'
        if method.return_type != 'void' and method.return_type != 'seL4_MessageInfo_t':
            buf=buf+f'{indent}    {method.return_type} __ret;'+'\n'
        for a in method.args:
            if a.direction != ArgDirection.IN:
                buf=buf+f'{indent}    {a.ctype} {a.name};'+'\n'
        buf=buf+f'{indent}}};'+'\n'
        return buf


class InterfacePrint(InterfaceGen):
    def __str__(self):

        return str(self.__class__) + ": " + str(self.__dict__)

    def __init__(self, interface, filebasename = '', wordsize=8):

        super().__init__(interface, filebasename, wordsize)
        
        for i in self.interface.includes:
            print(f'#include {i.header}')

        for i in self.interface.defines:
            print(f'#define {i.name} ({i.value})')

        for i in self.interface.methods:
            print(f'{i.name}[id={i.id}](',end='')
            print(', '.join(map(self.formatarg,i.args)),end='')
            print(f') -> {i.return_type}')



# should add check the id are greater than seL4_NumErrors

class InterfaceClientStubs(InterfaceGen):
    def __str__(self):

        return str(self.__class__) + ": " + str(self.__dict__)

    def __init__(self, interface, filebasename = '', wordsize=8):

        super().__init__(interface, filebasename, wordsize)

        with open(self.filebasename + '.h', 'w') as hf:
            print(self.preamble, file=hf)
            
            for i in self.interface.includes:
                if i.client:
                    print(f'#include {i.header}',file=hf)

            print(f'#define sizeof_in_MRs(x)    ((sizeof(x)+{self.wordsize}-1)/{self.wordsize})',file=hf)    
            for i in self.interface.defines:
                print(f'#define {i.name} ({i.value})', file=hf)

            for i in self.interface.methods:
                print(f'#define METHOD_NUM_{i.name.upper()} {i.id}',file=hf)
                print(f'extern {i.return_type} {i.name}(',end='', file=hf)

                    
                if len(i.args) == 0 and len(i.cap_args) == 0:
                    print(f'void',end='', file=hf)
                else:
                    if len(i.args) > 0:
                        print(', '.join(map(self.formatarg,i.args)),end='',file=hf)
                    if len(i.cap_args) > 0:
                        print(', '.join(map(self.formatcaparg,i.cap_args)),end='',file=hf)
                
                print(');\n',file=hf)
            
            
        with open(self.filebasename + '.c', 'w') as cf:
            print(self.preamble, file=cf)
            print(f'#include <{self.filebasename + ".h"}>',file=cf)

            #for i in self.interface.includes:
            #    print(f'#include {i.header}',file=cf)


            for i in self.interface.methods:
                print(f'{i.return_type} {i.name}(',end='', file=cf)
                
                if len(i.args) == 0 and len(i.cap_args) == 0:
                    print(f'void',end='', file=cf)
                else:
                    if len(i.args) > 0:
                        print(', '.join(map(self.formatarg,i.args)),end='',file=cf)
                    if len(i.cap_args) > 0:
                        print(', '.join(map(self.formatcaparg,i.cap_args)),end='',file=cf)
                
                
                print(')\n{',file=cf)
                print(self.gen_ipc_in_struct(i,'    '),file=cf)
                print(self.gen_ipc_out_struct(i,'    '),file=cf)
                print(f'    seL4_MessageInfo_t message;', file=cf)
                print(f'    seL4_IPCBuffer *ipc_buf = seL4_GetIPCBuffer();', file=cf)
                print(f'    struct {self.ipc_in_struct_name(i.name)} *argsin_ptr = (struct {self.ipc_in_struct_name(i.name)} *) &(ipc_buf->msg[0]);', file=cf)
                print(f'    struct {self.ipc_out_struct_name(i.name)} *argsout_ptr = (struct {self.ipc_out_struct_name(i.name)} *) &(ipc_buf->msg[0]);', file=cf)

                if len(i.args) > 0:
                    print(f'    *argsin_ptr = ((struct {self.ipc_in_struct_name(i.name)}) {{', end='', file=cf)
                    initialiser = ', '.join(map(lambda a: f'{a.name}' if a.direction == ArgDirection.IN else f'*{a.name}',filter(lambda a: a.direction != ArgDirection.OUT, i.args)))
                    print(initialiser, end='',file=cf)
                    print('});',file=cf)
                in_caps = list(filter(lambda c: c.direction == ArgDirection.IN,i.cap_args))
                num_in_caps = len(in_caps)
                out_caps = list(filter(lambda c: c.direction == ArgDirection.OUT,i.cap_args))
                num_out_caps = len(out_caps)

                for ci in range(num_in_caps):
                    print(f'    ipc_buf->caps_or_badges[{ci}] = {in_caps[ci].name};',file=cf)
                    
                    
                
                if num_out_caps == 0:
                    pass
                elif num_out_caps == 1:
                   print(f'    ipc_buf->receiveCNode = {self.interface.client_cspace_root};',file=cf) 
                   print(f'    ipc_buf->receiveIndex = {out_caps[0].name};',file=cf) 
                   print(f'    ipc_buf->receiveDepth = {self.interface.client_cspace_depth};',file=cf) 
                else:
                    raise RuntimeError('Only one capability can be received')                    


                print(f'    message = seL4_MessageInfo_new(METHOD_NUM_{i.name.upper()}, 0, {num_in_caps}, sizeof_in_MRs(struct {self.ipc_in_struct_name(i.name)}));', file=cf)
                print(f'    message = seL4_Call({i.cap}, message);',file=cf)
                outs = [a for a in i.args if a.direction != ArgDirection.IN]
                for o in outs:
                    print (f'    *{o.name} = argsout_ptr->{o.name};',file=cf)
                if i.return_type == 'void':
                    pass
                elif i.return_type == 'seL4_MessageInfo_t':
                    print(f'    return message;', file=cf)
                else:
                    print(f'    return argsout_ptr->__ret;', file=cf)

                print('}\n\n',file=cf)



#############
# Server side generation
#
# Note: The assumption here is that the compiler and developer combine
# sanely with a switch that results in resonable code. Needs some
# investigation to confirm. A good analysis in the space is the
# following paper.
#
# Roger A. Sayle, "A Superoptimizer Analysis of Multiway Branch Code
# Generation", Proc. GCC Summit, 2008


class InterfaceServerDispatch(InterfaceGen):
    def __str__(self):

        return str(self.__class__) + ": " + str(self.__dict__)

    def __init__(self, interface, filebasename = '', wordsize=8):

        super().__init__(interface, filebasename, wordsize)

        with open(self.filebasename + '.h', 'w') as hf:
            print(self.preamble, file=hf)
            
            for i in self.interface.includes:
                if i.server:
                    print(f'#include {i.header}',file=hf)

            print(f'#define sizeof_in_MRs(x)    ((sizeof(x)+{self.wordsize}-1)/{self.wordsize})',file=hf)    
            for i in self.interface.defines:
                print(f'#define {i.name} ({i.value})', file=hf)

            print(f'extern seL4_MessageInfo_t {self.interface.dispatch_func}(seL4_CPtr ep, seL4_MessageInfo_t msginfo, void * reply, void *data);',file=hf)
            print(f'extern seL4_MessageInfo_t {self.interface.error_func}(seL4_CPtr ep, seL4_MessageInfo_t msginfo, void *reply, void *data);',file=hf)

            for i in self.interface.methods:
                print('\n/****************************************', file=hf)
                print(f' * extern {i.return_type} {i.name}(',end='', file=hf)
                if len(i.args) != 0:
                    print(', '.join(map(self.formatarg,i.args)),end='',file=hf)
                else:
                    print(f'void',end='', file=hf)
                        
                
                print(');',file=hf)
                print(' */', file=hf)    
                print(f'#define METHOD_NUM_{i.name.upper()} {i.id}',file=hf)
                print(self.gen_ipc_in_struct(i,'', self.interface.server_prefix),file=hf)
                print(self.gen_ipc_out_struct(i,'', self.interface.server_prefix ),file=hf)

                print(f'extern seL4_MessageInfo_t {self.interface.server_prefix}{i.name}(seL4_CPtr ep, seL4_MessageInfo_t msginfo, void * reply, void *data);\n', file=hf)
            
            
        with open(self.filebasename + '.c', 'w') as cf:
            print(self.preamble, file=cf)
            print(f'#include <{self.filebasename + ".h"}>',file=cf)

            #for i in self.interface.includes:
            #    if i.server:
            #        print(f'#include {i.header}',file=cf)

            print(f'seL4_MessageInfo_t {self.interface.dispatch_func}(seL4_CPtr ep, seL4_MessageInfo_t msginfo, void *reply, void *data)\n{{',file=cf)
            print('    seL4_MessageInfo_t msg;',file=cf);
            print('    switch (seL4_MessageInfo_get_label(msginfo)) {', file=cf)
            for i in self.interface.methods:
                print(f'        case METHOD_NUM_{i.name.upper()}: msg = {self.interface.server_prefix}{i.name}(ep, msginfo, reply, data); break;', file=cf)

                
            print(f'\n        default: msg = {self.interface.error_func}(ep, msginfo, reply, data);',file=cf)
            print('    }',file=cf)
            print('    return msg;',file=cf)
            print('}',file=cf)


