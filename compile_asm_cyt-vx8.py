#!/usr/bin/python3
import math
import json
import sys
import re


DRKRED  = '\x1B[38;2;255;0;0m'
RED     = '\x1B[38;2;255;128;128m'
YELLOW  = '\x1B[38;2;255;255;128m'
BLUE    = '\x1B[38;2;128;128;255m'
NONE    = '\x1B[0m'
DRKBLUE = '\x1B[38;2;70;70;140m'
DRKGRAY = '\x1B[38;2;96;96;96m'


def log(msg):
    msg += f"{NONE}"
    print(msg, file=sys.stderr)


def warning(msg):
    msg = f"{YELLOW}[WRN] {msg}"
    log(msg)
    
    
def error(msg):
    msg = f"{RED}[ERR] {msg}"
    log(msg)
    
def decode_op(data, cfg):
    out   = None
    cause = None
    mnemo = data[0]
    args  = data[1:] 
    # search for mnemonic in config
    if not mnemo in cfg['mnemonics']:
        return None, f"Mnemonic has not been found ('{mnemo}')"
        
    # Add opcode value
    data = cfg['mnemonics'][mnemo]
    op   = int(data['opcode'],16) << data['shift']

    # Add argument values
    if len(args) != len(data['arguments']):
        return None, f"Wrong nb arguments. Provided #{len(args)}. Expected #{len(data['arguments'])}"   
         
    # Check each argument value
    for i in range(len(args)):
        if args[i] not in data['arguments'][i]['values']:
            # Before returning an error, check if this argument can 
            # be a specific one (IMMediate value or ADDR, ...)
            if 'CNST8' not in data['arguments'][i]['values'] and 'ADDR8' not in data['arguments'][i]['values']:
                return None, f"Unhandled value ({args[i]}) for argument #{i+1}"
                                   
    # now get argument value
    for i in range(len(args)):
        if args[i] not in cfg['registers']:
            # First check if the requested values are in specifics ?
                if 'CNST8' in data['arguments'][i]['values']:
                    rng = cfg['specific']['CNST8']
                    value_ok = True
                    try:
                        v = int(args[i], 16)
                    except:
                        value_ok = False                        
                    if not (value_ok) or not (rng[0] <= int(args[i],16) <= rng[1]):
                        msg  = f"Bad value ({args[i]}) "
                        msg += f"for CNST8 argument #{i+1}"
                        msg += f"(range=[0x{hex(rng[0])[2:].upper()},"
                        msg += f"0x{hex(rng[1])[2:].upper()}])"
                        return None, msg

                elif 'ADDR8' in data['arguments'][i]['values']:
                    rng = cfg['specific']['ADDR8']
                    value_ok = True
                    try:
                        v = int(args[i], 16)
                    except:
                        value_ok = False                        
                    if not (value_ok) or not (rng[0] <= int(args[i],16) <= rng[1]):
                        msg  = f"Bad value ({args[i]}) "
                        msg += f"for ADDR8 argument #{i+1}"
                        msg += f"(range=[0x{hex(rng[0])[2:].upper()},"
                        msg += f"0x{hex(rng[1])[2:].upper()}])"
                        return None, msg
                    
                else:                       
                    return None, f"Register value ({args[i]}) does not exist"
        
        elif args[i] not in data['arguments'][i]['values']:
            return None, f"Unhandled value ({args[i]}) for argument #{i+1}"

        else:
            # Get register value
            v = cfg['registers'][args[i]]
            
        # Shift and limit size of value 
        shift, size = data['arguments'][i]['position']
        tmp = 2**(size)-1 & v 
        tmp = tmp << shift            
        op = op | tmp
        # if we have to duplicate this field
        if 'duplicate' in data['arguments'][i]:
            shift, size = data['arguments'][i]['duplicate']
            tmp = 2**(size)-1 & v 
            tmp = tmp << shift            
            op = op | tmp
            
    # apply default OR mask
    mask = int(data['or_mask'], 16)
    op = op | mask        

    # bytecode output    
    size = math.ceil(cfg['instr_size']//8)
    op = (('0' * size*2) + hex(op)[2:])[-size*2:]
    op = op.upper()

    # check instruction value with regexp
    if not re.fullmatch(data['regexp'], op):
        print(data['regexp'], op)
        return None, f"{DRKRED}Instruction value ({op}) differs from regexp ({data['regexp']})"

    out = f"{op}"
    return out, None   


def compile_CYT_VX(filepath, cfg):
    # open file and read line by line 
    bytecode = ""
    bytecodet = ""
    textcode = ""  
    with open(filepath, 'r') as f:
        print('#####################################################')
        print(f"compiling '{filepath}'...")
        print('#####################################################\n')
        line = "NOP"
        instrno = 0
        lineno  = 0
        errors  = 0
        while line != '':
            line2 = line.strip()
            line2 = line2.replace(' ', '').replace('\t', '').upper()
            code  = ""
            codet = ""
            text  = ""
            if line2 != "":
                if not line2.startswith('#'):
                    data = line2.split(',')
                    line3 = line2.replace(',', ', ')
                    if len(data) < 1:
                        errors += 1
                        text  = f"{RED}{line3}"
                        rem   = 18 - len(line3)
                        text += ' ' * rem
                        text += f" > Line too short{NONE}"

                    # Decode one operation and return bytecode
                    code, cause = decode_op(data, cfg)
                    if code is None:
                        errors += 1
                        codet = f"{RED}------{NONE}"
                        text = f"{RED}{line3}"
                        rem = 18 - len(line3)
                        text += ' ' * rem
                        text += f" > {cause}{NONE}"
                    else:
                        instr = ("00" + hex(instrno).replace('0x',''))[-2:].upper()
                        codet = f"{YELLOW}{instr}{BLUE} | {DRKGRAY}{code}{NONE}"
                        text = f"{DRKGRAY}{line3}{NONE}"
                        instrno += 1
                else:
                    # write line of comment
                    test=line.replace('\n', '').replace('#', '').strip()
                    text += f"{BLUE}#{test}{NONE}"
                    
            bytecodet += f"{codet}\n"
            bytecode += f"{code}\n"
            textcode += f"{BLUE}{lineno:4d} | {NONE}" 
            if code != '':
                textcode += f"{codet}{BLUE} | "
            if text != '':
                textcode += f"{text}"
            textcode += '\n'
                    
            line = f.readline()
            lineno += 1    

        if errors > 0:
            s = 's' if errors > 1 else ''
            print(f"{errors} error{s} during compilation : \n")
            print(textcode)
            exit(1)
        else:
            print(textcode)
            return bytecode
            
                 
if __name__ == "__main__":

    cfg_name = "CYT-VX8_F24-6_M256-0_R6-2_L1.json"

    # Load default CYT-VX config
    content = ""
    with open(cfg_name, 'r') as f:
        content = f.read()
    cfg = json.loads(content)
    
    # Get program file
    if len(sys.argv) <= 2:
        print("usage : ./compile_asm_cyt-vx8.py <file.cyt> <executable>")
        exit(1)

    byte_code = compile_CYT_VX(sys.argv[1], cfg)
    byte_code = "v2.0 raw\n" + byte_code
    while "\n\n" in byte_code:
        byte_code = byte_code.replace('\n\n', '\n')
        
    fp = open(sys.argv[2], "w")
    fp.write(byte_code)
    fp.close()
    print(f"Bytecode saved to : '{sys.argv[2]}' ")
    print()
    print()



