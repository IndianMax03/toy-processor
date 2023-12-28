import logging
import sys

from isa import Opcode, ALU_Opcode, Selectors, Program_Mode, read_code, nullar_instructions, onear_instructions, branch_instructions

class Halt(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class ALU:
    
    alu_operations = [ALU_Opcode.INC, ALU_Opcode.DEC, ALU_Opcode.ADD, ALU_Opcode.CMP, ALU_Opcode.TEST, ALU_Opcode.SKIP_A, ALU_Opcode.SKIP_B]
    result = None
    src_a = None
    src_b = None
    operation = None
    n_flag = None
    z_flag = None
    
    def __init__(self):
        self.result = 0
        self.src_a = 0
        self.src_b = 0
        self.operation = None
        self.n_flag = False
        self.z_flag = True
    
    def calc(self):
        tmp_result = None
        if self.operation == ALU_Opcode.INC:
            if self.src_b is None:
                self.result = self.src_a + 1
            else:
                self.result = self.src_b + 1
        elif self.operation == ALU_Opcode.DEC:
            if self.src_b is None:
                self.result = self.src_a - 1
            else:
                self.result = self.src_b - 1
        elif self.operation == ALU_Opcode.ADD:
            self.result = self.src_a + self.src_b
        elif self.operation == ALU_Opcode.CMP:
            tmp_result = self.src_a - self.src_b
        elif self.operation == ALU_Opcode.TEST:
            tmp_result = self.src_a & self.src_b
        elif self.operation == ALU_Opcode.SKIP_A:
            self.result = self.src_a
        elif self.operation == ALU_Opcode.SKIP_B:
            self.result = self.src_b
        else:
            raise f"Unknown ALU operation: {self.operation}"
        self.set_flags(tmp_result)
    
    def set_flags(self, op_result):
        if op_result is None:
            self.n_flag = self.result < 0
            self.z_flag = self.result == 0
        else:
            self.n_flag = op_result < 0
            self.z_flag = op_result == 0
    
    def set_details(self, src_a : int | None, src_b: int | None, operation):
        assert operation in self.alu_operations, f"Unknown ALU operation: {operation}"
        self.src_a = src_a
        self.src_b = src_b
        self.operation = operation
    

class DataPath:
    memory_size = None
    "Размер памяти."

    memory = None
    "Память. Инициализируется NOP'ами."

    addr = None
    "Регистр адреса. Инициализируется нулём."
    
    to_mem = None
    "Регистр записи в память. Инициализируется нулём."
    
    ir = None
    "Регистр инструкции. Инициализируется NOP'ом."

    dr = None
    "Регистр данных. Инициализируется нулём."
    
    pc = None
    "Регистр адреса следующей команды. Инициализируется входными данными конструктора (_start)."
    
    sp = None
    "Регистр стека. Инициализируется нулём."
    
    ps = None
    "Регистр статуса программы. Флагами АЛУ. Прерывания запрещены"
    
    ac = None
    "Аккумулятор. Инициализируется нулём."

    input_buffer = None
    "Буфер входных данных. Инициализируется входными данными конструктора."

    output_buffer = None
    "Буфер выходных данных."
    
    alu = None
    "АЛУ"

    def __init__(self, _start, memory_size, input_buffer):
        assert memory_size > 0, "memory size should be greater than zero"
        self.alu = ALU()
        self.memory_size = memory_size
        self.memory = [{"opcode" : Opcode.NOP}] * memory_size
        self.addr = 0
        self.to_mem = 0
        self.ir = {"opcode" : Opcode.NOP}
        self.dr = 0
        self.pc = _start
        self.sp = 0
        self.ps = {"N": self.alu.n_flag, "Z": self.alu.n_flag, "INT_EN": False}
        self.ac = 0
        self.input_buffer = input_buffer
        self.output_buffer = []
      
    def signal_fill_memory(self, program):
        for mem_cell in program:
            index = mem_cell['index']
            self.memory[index] = mem_cell
      
    def signal_latch_addr(self):
        self.addr = self.alu.result
    
    def signal_latch_to_mem(self):
        self.to_mem = self.alu.result
    
    def signal_latch_ir(self):
        assert self.addr >= 0 and self.addr <= self.memory_size, f"Can't read out of memory!"
        self.ir = self.memory[self.addr]
    
    def signal_latch_dr(self):
        assert self.addr >= 0 and self.addr <= self.memory_size, f"Can't read out of memory!"
        self.dr = self.memory[self.addr]['value']
        
    def signal_latch_pc(self):
        self.pc = self.alu.result
        
    def signal_latch_sp(self):
        self.sp = self.alu.result
        
    def signal_latch_ps(self):
        self.ps['N'] = self.alu.n_flag
        self.ps['Z'] = self.alu.z_flag
        
    def signal_enable_interrupts(self):
        self.ps['INT_EN'] = True
        
    def signal_disable_interrupts(self):
        self.ps['INT_EN'] = False
        
    def signal_latch_ac(self, sel):
        assert sel in {Selectors.FROM_INPUT, Selectors.FROM_ALU}, f"Unknown selector '{sel}'"
        if sel == Selectors.FROM_ALU:
            self.ac = self.alu.result
        else:
            self.ac = ord(self.input_buffer[0]['symbol'])
        
    def signal_output(self):
        symbol = chr(self.ac)
        logging.info("output: %s << %s", repr("".join(self.output_buffer)), repr(symbol))
        self.output_buffer.append(symbol)
        
    def signal_wr(self):
        self.memory[self.addr] = {"index" : self.addr, "opcode": Opcode.NOP, "value": self.to_mem, "is_indirect": False}
    
    def signal_execute_alu_op(self, operation, right_sel = None, side_sel = None):
        src_a = None
        src_b = None
        if not(right_sel is None):
            assert right_sel in {Selectors.FROM_DR, Selectors.FROM_PC, Selectors.FROM_SP}, f"Unknown selector '{right_sel}'"
            if right_sel == Selectors.FROM_DR:
                src_b = self.dr
            elif right_sel == Selectors.FROM_PC:
                src_b = self.pc
            else:
                src_b = self.sp
                
        if not(side_sel is None):
            assert side_sel in {Selectors.LEFT_SIDE, Selectors.RIGHT_SIDE}, f"Unknown side selector '{side_sel}' in alu operation"
            if side_sel == Selectors.LEFT_SIDE:
                src_a = self.ac
                src_b = None
        else:
            src_a = self.ac
            
        self.alu.set_details(src_a, src_b, operation)
        self.alu.calc()
    
    def get_info(self):
        return self.ir, self.ps

class ControlUnit:
    
    data_path = None
    
    instruction_counter = None
    
    _tick = None
    
    mode = None
    
    def __init__(self, program, data_path : DataPath):
        self.mode = Program_Mode.NORMAL
        self.instruction_counter = 0
        self.data_path = data_path
        self._tick = 0
        data_path.signal_fill_memory(program)
        
    def tick(self):
        self._tick += 1

    def current_tick(self):
        return self._tick
    
    def instr_fetch(self):
        self.data_path.signal_execute_alu_op(ALU_Opcode.SKIP_B, Selectors.FROM_PC)
        self.data_path.signal_latch_addr()
        self.tick()
        
        self.data_path.signal_execute_alu_op(ALU_Opcode.INC, Selectors.FROM_PC, Selectors.RIGHT_SIDE)
        self.data_path.signal_latch_pc()
        self.data_path.signal_latch_ir()
        self.data_path.signal_latch_dr()
        self.tick()
    
    def execute(self):
        ir, ps = self.data_path.get_info()
        opcode, value, is_indirect = ir['opcode'], ir['value'], ir['is_indirect']
        
        if opcode == Opcode.NOP:
            self.tick()
            return
        
        if is_indirect:
            self.data_path.signal_execute_alu_op(ALU_Opcode.SKIP_B, Selectors.FROM_DR)
            self.data_path.signal_latch_addr()
            self.tick()
            self.data_path.signal_latch_dr()
            self.tick()
        
        if opcode in nullar_instructions:
            self.execute_nullar(opcode)
        elif opcode in onear_instructions:
            self.execute_onear(opcode, value)
        else:
            self.execute_branch(opcode, ps)

    def execute_nullar(self, opcode):
        if opcode == Opcode.INC:
            self.data_path.signal_execute_alu_op(ALU_Opcode.INC, side_sel=Selectors.LEFT_SIDE)
            self.data_path.signal_latch_ac(Selectors.FROM_ALU)
            self.tick()
        elif opcode == Opcode.DEC:
            self.data_path.signal_execute_alu_op(ALU_Opcode.DEC, side_sel=Selectors.LEFT_SIDE)
            self.data_path.signal_latch_ac(Selectors.FROM_ALU)
            self.tick()
        elif opcode == Opcode.HALT:
            raise Halt(f"Met {Opcode.HALT}")
        elif opcode == Opcode.EI:
            self.data_path.signal_enable_interrupts()
            self.tick()
        elif opcode == Opcode.DI:
            self.data_path.signal_disable_interrupts()
            self.tick()
        elif opcode == Opcode.PUSH:
            self.data_path.signal_execute_alu_op(ALU_Opcode.DEC, Selectors.FROM_SP, Selectors.RIGHT_SIDE)
            self.data_path.signal_latch_sp()
            self.data_path.signal_latch_addr()
            self.tick()
            self.data_path.signal_execute_alu_op(ALU_Opcode.SKIP_A)
            self.data_path.signal_latch_to_mem()
            self.data_path.signal_wr()
            self.tick()
        elif opcode == Opcode.POP:
            self.data_path.signal_execute_alu_op(ALU_Opcode.SKIP_B, Selectors.FROM_SP)
            self.data_path.signal_latch_addr()
            self.tick()
            self.data_path.signal_execute_alu_op(ALU_Opcode.INC, Selectors.FROM_SP, Selectors.RIGHT_SIDE)
            self.data_path.signal_latch_sp()
            self.data_path.signal_latch_dr()
            self.tick()
            self.data_path.signal_execute_alu_op(ALU_Opcode.SKIP_B, Selectors.FROM_DR)
            self.data_path.signal_latch_ac(Selectors.FROM_ALU)
            self.tick()
        elif opcode == Opcode.IRET:
            pass
    
    def execute_onear(self, opcode, value):
        if opcode == Opcode.LOAD:
            self.data_path.signal_execute_alu_op(ALU_Opcode.SKIP_B, Selectors.FROM_DR)
            self.data_path.signal_latch_addr()
            self.tick()
            self.data_path.signal_latch_dr()
            self.data_path.signal_execute_alu_op(ALU_Opcode.SKIP_B, Selectors.FROM_DR)
            self.data_path.signal_latch_ac(Selectors.FROM_ALU)
            self.tick()
        elif opcode == Opcode.STORE:
            self.data_path.signal_execute_alu_op(ALU_Opcode.SKIP_B, Selectors.FROM_DR)
            self.data_path.signal_latch_addr()
            self.tick()
            self.data_path.signal_execute_alu_op(ALU_Opcode.SKIP_A)
            self.data_path.signal_latch_to_mem()
            self.data_path.signal_wr()
            self.tick()
        elif opcode == Opcode.ADD:
            self.data_path.signal_execute_alu_op(ALU_Opcode.ADD, Selectors.FROM_DR)
            self.data_path.signal_latch_ac(Selectors.FROM_ALU)
            self.tick()
        elif opcode == Opcode.CMP:
            self.data_path.signal_execute_alu_op(ALU_Opcode.CMP, Selectors.FROM_DR)
            self.tick()
        elif opcode == Opcode.TEST:
            self.data_path.signal_execute_alu_op(ALU_Opcode.TEST, Selectors.FROM_DR)
            self.tick()
        elif opcode == Opcode.OUT:
            self.data_path.signal_output()
            self.tick()
        elif opcode == Opcode.IN:
            pass
        
    
    def execute_branch(self, opcode, ps):
        if opcode == Opcode.JG:
            if not ps['N']:
                self.data_path.signal_execute_alu_op(ALU_Opcode.SKIP_B, Selectors.FROM_DR)
                self.data_path.signal_latch_pc() 
        
        elif opcode == Opcode.JZ:
            if ps['Z']:
                self.data_path.signal_execute_alu_op(ALU_Opcode.SKIP_B, Selectors.FROM_DR)
                self.data_path.signal_latch_pc() 
        
        elif opcode == Opcode.JNZ:
            if not ps['Z']:
                self.data_path.signal_execute_alu_op(ALU_Opcode.SKIP_B, Selectors.FROM_DR)
                self.data_path.signal_latch_pc() 
        
        elif opcode == Opcode.JMP:
            self.data_path.signal_execute_alu_op(ALU_Opcode.SKIP_B, Selectors.FROM_DR)
            self.data_path.signal_latch_pc() 
        
        self.tick()
        
    def go_to_interrupt(self):
        
        
    def check_for_interruptions(self):
        while len(self.data_path.input_buffer) > 0:
            schedule = self.data_path.input_buffer[0]
            if (self.current_tick() < schedule['tick']):
                break
            self.mode = Program_Mode.INTERRUPT
            sched = schedule.pop(0)
        
    def decode_and_execute_instruction(self):
        self.instr_fetch()
        self.execute()
        self.data_path.signal_latch_ps()
        self.check_for_interruptions()
    
    def __repr__(self):
        return "TICK: {:3} | AC: {:3} | PC: {:3} | IR: {:5} | DR: {:3} | SP: {:3} | Addr: {:3} | ToMem: {:3} | N: {:1} | Z: {:1} | INT_EN: {:1} | mem[Addr]: {:3} | mode: {}".format(
            self.current_tick(),
            self.data_path.ac,
            self.data_path.pc,
            self.data_path.ir['opcode'],
            self.data_path.dr,
            self.data_path.sp,
            self.data_path.addr,
            self.data_path.to_mem,
            (1 if self.data_path.ps['N'] else 0),
            (1 if self.data_path.ps['Z'] else 0),
            (1 if self.data_path.ps['INT_EN'] else 0),
            self.data_path.memory[self.data_path.addr]['opcode'],
            self.mode
        )


def simulation(_start, code, input_tokens, memory_size, limit):
    data_path = DataPath(_start, memory_size, input_tokens)
    control_unit = ControlUnit(code, data_path)
    instr_counter = 0

    logging.info("%s", control_unit)
    try:
        while instr_counter < limit:
            control_unit.decode_and_execute_instruction()
            instr_counter += 1
            logging.info("%s", control_unit)
    except Halt:
        pass

    if instr_counter >= limit:
        logging.warning("Limit exceeded!")
    logging.info("output_buffer: %s", repr("".join(data_path.output_buffer)))
    return "".join(data_path.output_buffer), instr_counter, control_unit.current_tick()

def parse_to_tokens(input_file):
    tokens = []
    with open(input_file, encoding="utf-8") as file:
        input_text = file.read()
        if not input_text:
            input_token = []
        else:
            input_token = eval(input_text)
    
    if len(input_token) > 0:
        for tick, symbol in input_token:
            tokens.append({"tick" : tick, "symbol": symbol})
    return tokens

def main(code_file, input_file):
    _start, code = read_code(code_file)
    input_token = parse_to_tokens(input_file)
    
    output, instr_counter, ticks = simulation(
        _start,
        code,
        input_tokens=input_token,
        memory_size=100,
        limit=1000,
    )

    print("".join(output))
    print("instr_counter: ", instr_counter, "ticks:", ticks)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    assert len(sys.argv) == 3, "Wrong arguments: machine.py <code_file> <input_file>"
    _, code_file, input_file = sys.argv
    main(code_file, input_file)
