import json
from enum import Enum
from dataclasses import dataclass

nullar_instructions = ['inc', 'dec', 'halt', 'ei', 'di', 'push', 'pop', 'iret']

onear_instructions = ['load', 'store', 'out', 'in', 'cmp', 'test', 'jg', 'jz', 'jnz', 'jmp']

pseudo_commands = ['org']

data_types = ['.word']

class Opcode(str, Enum):
    
    NOP = "nop"
    
    INC = "inc"
    DEC = "dec"
    HALT = "halt"
    EI = "ei"
    DI = "di"
    PUSH = "push"
    POP = "pop"
    IRET = "iret"
    
    LOAD = "load"
    STORE = "store"
    OUT = "out"
    IN = "in"
    CMP = "cmp"
    TEST = "test"
    
    JG = "jg"
    JZ = "jz"
    JNZ = "jnz"
    JMP = "jmp"
    
    def __str__(self) -> str:
        return str(self.value)

@dataclass
class Term:
    index: int
    opcode: Opcode
    value: int
    indirect_mode: bool
    
    def __str__(self) -> str:
        return f"[ index: {self.index}; opcode: {self.opcode};  value: {self.value}; indirect_mode: {self.indirect_mode}]"

def write_code(filename, code):
    with open(filename, "w", encoding="utf-8") as file:
        buf = []
        for instr in code:
            buf.append(json.dumps(instr))
        file.write("[" + ",\n ".join(buf) + "]")

def read_code(filename):
    pass
