#!/usr/bin/python3
import sys, argparse
import xml.etree.ElementTree as ET
from interface_parse import InterfaceParser
from interface_gen import InterfacePrint
            
generators = {'printer' : InterfacePrint}
        
def main() -> int:
    global wordsize_in_bytes
    
    ap = argparse.ArgumentParser(description='Generate seL4 RPC stubs for an interface specified in XML') 
    ap.add_argument('filename', metavar='file_name.xml',
                    type=str, help='Interface xml file')
    ap.add_argument('-w','--wordsize', dest='wordsize', default='64',
                    type=str, help='CPU word size in bits (default=64)')
    ap.add_argument('-g','--generator',
                    dest='generator',
                    default='printer',
                    choices=generators.keys(),
                    type=str,
                    help='Choose output interface generator (default=printer)')
    ap.add_argument('-o','--output', dest='filebasename', default='',
                    type=str, help='Choose output file base name')

    args = ap.parse_args()
    if args.wordsize == '64':
        wordsize_in_bytes = 8
    elif args.wordsize == '32':
        wordsize_in_bytes=4
    else:
        raise RuntimeError(f'Unsupported word size "{args.wordsize}"')
    

    target = InterfaceParser(wordsize_in_bytes)
    parser = ET.XMLParser(target=target)
    with open(args.filename) as xmlfile:
        for line in xmlfile:
            parser.feed(line)
        interface = parser.close()


    if args.generator in generators.keys():
        generators[args.generator](interface,
                                   args.filebasename,
                                   wordsize_in_bytes)
    else:
        raise RuntimeError(f'Non-existant output generator "{args.generator}"')
    return 0

if __name__ == '__main__':
    sys.exit(main())
