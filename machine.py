import logging
import sys
from typing import ClassVar

from isa import ALUOpcode, Opcode, ProgramMode, Selectors, nullar_instructions, onear_instructions, read_code


class HaltError(Exception):
    def __init__(self, opcode):
        self.message = f"Met {opcode}"
        super().__init__(self.message)


class ALU:
    alu_operations: ClassVar = [
        ALUOpcode.INC_A,
        ALUOpcode.INC_B,
        ALUOpcode.DEC_A,
        ALUOpcode.DEC_B,
        ALUOpcode.ADD,
        ALUOpcode.CMP,
        ALUOpcode.TEST,
        ALUOpcode.SKIP_A,
        ALUOpcode.SKIP_B,
    ]
    result: ClassVar = None
    src_a: ClassVar = None
    src_b: ClassVar = None
    operation: ClassVar = None
    n_flag: ClassVar = None
    z_flag: ClassVar = None

    def __init__(self):
        self.result = 0
        self.src_a = None
        self.src_b = None
        self.operation = None
        self.set_flags()

    def calc(self):
        tmp_result = None
        if self.operation == ALUOpcode.INC_A:
            self.result = self.src_a + 1
        elif self.operation == ALUOpcode.INC_B:
            self.result = self.src_b + 1
        elif self.operation == ALUOpcode.DEC_A:
            self.result = self.src_a - 1
        elif self.operation == ALUOpcode.DEC_B:
            self.result = self.src_b - 1
        elif self.operation == ALUOpcode.ADD:
            self.result = self.src_a + self.src_b
        elif self.operation == ALUOpcode.CMP:
            tmp_result = self.src_a - self.src_b
        elif self.operation == ALUOpcode.TEST:
            tmp_result = self.src_a & self.src_b
        elif self.operation == ALUOpcode.SKIP_A:
            self.result = self.src_a
        elif self.operation == ALUOpcode.SKIP_B:
            self.result = self.src_b
        else:
            raise f"Unknown ALU operation: {self.operation}"
        self.set_flags(tmp_result)

    def set_flags(self, tmp_result=None):
        if tmp_result is None:
            self.n_flag = self.result < 0
            self.z_flag = self.result == 0
        else:
            self.n_flag = tmp_result < 0
            self.z_flag = tmp_result == 0

    def set_details(self, src_a, src_b, operation):
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
    "Регистр адреса следующей команды. Инициализируется нулём."

    sp = None
    "Регистр стека. Инициализируется нулём."

    ps = None
    "Регистр статуса программы. Инициализируется флагами АЛУ. Прерывания запрещены"

    ac = None
    "Аккумулятор. Инициализируется нулём."

    input_buffer = None
    "Буфер входных данных. Инициализируется входными данными конструктора."

    output_symbol_buffer = None
    "Буфер выходных символов. Инициализируется пустым массивом"

    output_numeric_buffer = None
    "Буфер выходных цифр. Инициализируется пустым массивом"

    alu = None
    "АЛУ"

    def __init__(self, memory_size, input_buffer):
        assert memory_size > 0, "memory size should be greater than zero"
        self.alu = ALU()
        self.memory_size = memory_size
        self.memory = [{"opcode": Opcode.NOP.value}] * memory_size
        self.addr = 0
        self.to_mem = 0
        self.ir = {"opcode": Opcode.NOP.value}
        self.dr = 0
        self.pc = 0
        self.sp = 0
        self.ps = {"N": self.alu.n_flag, "Z": self.alu.z_flag, "INT_EN": False}
        self.ac = 0
        self.input_buffer = input_buffer
        self.output_symbol_buffer = []
        self.output_numeric_buffer = []

    def signal_fill_memory(self, program):
        for mem_cell in program:
            index = mem_cell["index"]
            self.memory[index] = mem_cell

    def signal_latch_addr(self):
        self.addr = self.alu.result

    def signal_latch_to_mem(self):
        self.to_mem = self.alu.result

    def signal_latch_ir(self):
        assert self.addr >= 0, "Address below memory limit"
        assert self.addr <= self.memory_size, "Address above memory limit"
        self.ir = self.memory[self.addr]

    def signal_latch_dr(self):
        assert self.addr >= 0, "Address below memory limit"
        assert self.addr <= self.memory_size, "Address above memory limit"
        self.dr = self.memory[self.addr]["value"]

    def signal_latch_pc(self):
        self.pc = self.alu.result % self.memory_size

    def signal_latch_sp(self):
        self.sp = self.alu.result % self.memory_size

    def signal_latch_ps_flags(self):
        self.ps["N"] = self.alu.n_flag
        self.ps["Z"] = self.alu.z_flag

    def signal_latch_ps(self):
        self.alu.n_flag = True if int(self.alu.result / 100) == 1 else False
        self.alu.z_flag = True if int((self.alu.result / 10) % 10) == 1 else False
        self.ps["INT_EN"] = True if self.alu.result % 10 == 1 else False

    def signal_enable_interrupts(self):
        self.ps["INT_EN"] = True

    def signal_disable_interrupts(self):
        self.ps["INT_EN"] = False

    def signal_latch_ac(self, sel):
        assert sel in {Selectors.FROM_INPUT, Selectors.FROM_ALU}, f"Unknown selector '{sel}'"
        if sel == Selectors.FROM_ALU:
            self.ac = self.alu.result
        else:
            symbol = self.input_buffer.pop(0)["symbol"]
            symbol_code = ord(symbol)
            self.ac = symbol_code
            logging.debug("input: %s", repr(symbol))

    def signal_output(self):
        port_num = self.dr
        if port_num == 1:
            symbol = chr(self.ac)
            logging.debug("output_symbol_buffer: %s << %s", repr("".join(self.output_symbol_buffer)), repr(symbol))
            self.output_symbol_buffer.append(symbol)
        elif port_num == 2:
            symbol = self.ac
            logging.debug("output_numeric_buffer: [%s] << %d", ", ".join(map(str, self.output_numeric_buffer)), symbol)
            self.output_numeric_buffer.append(symbol)

    def signal_wr(self):
        self.memory[self.addr] = {
            "index": self.addr,
            "opcode": Opcode.NOP.value,
            "value": self.to_mem,
            "is_indirect": False,
        }

    def signal_execute_alu_op(self, operation, left_sel=None, right_sel=None):
        src_a = None
        src_b = None

        if left_sel is not None:
            assert left_sel in {Selectors.FROM_AC, Selectors.FROM_PS}, f"Unknown left selector '{right_sel}'"
            if left_sel == Selectors.FROM_AC:
                src_a = self.ac
            else:
                n = 1 if self.ps["N"] else 0
                z = 1 if self.ps["Z"] else 0
                int_en = 1 if self.ps["INT_EN"] else 0
                src_a = n * 100 + z * 10 + int_en

        if right_sel is not None:
            assert right_sel in {
                Selectors.FROM_DR,
                Selectors.FROM_PC,
                Selectors.FROM_SP,
            }, f"Unknown right selector '{right_sel}'"
            if right_sel == Selectors.FROM_DR:
                src_b = self.dr
            elif right_sel == Selectors.FROM_PC:
                src_b = self.pc
            else:
                src_b = self.sp

        self.alu.set_details(src_a, src_b, operation)
        self.alu.calc()


class ControlUnit:
    data_path = None

    instruction_counter = None

    _tick = None

    mode = None

    def __init__(self, program, data_path: DataPath):
        self.mode = ProgramMode.NORMAL
        self.instruction_counter = 0
        self.data_path = data_path
        self._tick = 0
        data_path.signal_fill_memory(program)

    def tick(self):
        self._tick += 1

    def current_tick(self):
        return self._tick

    def instr_fetch(self):
        self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_PC)
        self.data_path.signal_latch_addr()
        self.tick()

        self.data_path.signal_execute_alu_op(ALUOpcode.INC_B, right_sel=Selectors.FROM_PC)
        self.data_path.signal_latch_pc()
        self.data_path.signal_latch_ir()
        self.data_path.signal_latch_dr()
        self.tick()

    def execute(self):
        ir, ps = self.data_path.ir, self.data_path.ps
        opcode, is_indirect = ir["opcode"], ir["is_indirect"]

        if opcode == Opcode.NOP:
            self.tick()
            return

        if is_indirect:
            self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_DR)
            self.data_path.signal_latch_addr()
            self.tick()
            self.data_path.signal_latch_dr()
            self.tick()

        if opcode in nullar_instructions:
            self.execute_nullar(opcode)
        elif opcode in onear_instructions:
            self.execute_onear(opcode)
        else:
            self.execute_branch(opcode, ps)

    def execute_nullar(self, opcode):
        if opcode == Opcode.INC:
            self.data_path.signal_execute_alu_op(ALUOpcode.INC_A, left_sel=Selectors.FROM_AC)
            self.data_path.signal_latch_ac(Selectors.FROM_ALU)
            self.tick()
        elif opcode == Opcode.DEC:
            self.data_path.signal_execute_alu_op(ALUOpcode.DEC_A, left_sel=Selectors.FROM_AC)
            self.data_path.signal_latch_ac(Selectors.FROM_ALU)
            self.tick()
        elif opcode == Opcode.HALT:
            raise HaltError(Opcode.HALT)
        elif opcode == Opcode.EI:
            self.data_path.signal_enable_interrupts()
            self.tick()
        elif opcode == Opcode.DI:
            self.data_path.signal_disable_interrupts()
            self.tick()
        elif opcode == Opcode.PUSH:
            self.data_path.signal_execute_alu_op(ALUOpcode.DEC_B, right_sel=Selectors.FROM_SP)
            self.data_path.signal_latch_sp()
            self.data_path.signal_latch_addr()
            self.tick()
            self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_A, left_sel=Selectors.FROM_AC)
            self.data_path.signal_latch_to_mem()
            self.data_path.signal_wr()
            self.tick()
        elif opcode == Opcode.POP:
            self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_SP)
            self.data_path.signal_latch_addr()
            self.tick()
            self.data_path.signal_execute_alu_op(ALUOpcode.INC_B, right_sel=Selectors.FROM_SP)
            self.data_path.signal_latch_sp()
            self.data_path.signal_latch_dr()
            self.tick()
            self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_DR)
            self.data_path.signal_latch_ac(Selectors.FROM_ALU)
            self.tick()
        elif opcode == Opcode.IRET:
            #  Восстанавливаем PC
            self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_SP)
            self.data_path.signal_latch_addr()
            self.tick()
            self.data_path.signal_execute_alu_op(ALUOpcode.INC_B, right_sel=Selectors.FROM_SP)
            self.data_path.signal_latch_sp()
            self.data_path.signal_latch_dr()
            self.tick()
            self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_DR)
            self.data_path.signal_latch_pc()
            self.tick()
            #  Восстанавливаем PS
            self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_SP)
            self.data_path.signal_latch_addr()
            self.tick()
            self.data_path.signal_execute_alu_op(ALUOpcode.INC_B, right_sel=Selectors.FROM_SP)
            self.data_path.signal_latch_sp()
            self.data_path.signal_latch_dr()
            self.tick()
            self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_DR)
            self.data_path.signal_latch_ps()
            self.tick()
            self.mode = ProgramMode.NORMAL

    def execute_onear(self, opcode):
        if opcode == Opcode.LOAD:
            self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_DR)
            self.data_path.signal_latch_addr()
            self.tick()
            self.data_path.signal_latch_dr()
            self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_DR)
            self.data_path.signal_latch_ac(Selectors.FROM_ALU)
            self.tick()
        elif opcode == Opcode.STORE:
            self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_DR)
            self.data_path.signal_latch_addr()
            self.tick()
            self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_A, left_sel=Selectors.FROM_AC)
            self.data_path.signal_latch_to_mem()
            self.data_path.signal_wr()
            self.tick()
        elif opcode == Opcode.ADD:
            self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_DR)
            self.data_path.signal_latch_addr()
            self.tick()
            self.data_path.signal_latch_dr()
            self.data_path.signal_execute_alu_op(ALUOpcode.ADD, left_sel=Selectors.FROM_AC, right_sel=Selectors.FROM_DR)
            self.data_path.signal_latch_ac(Selectors.FROM_ALU)
            self.tick()
        elif opcode == Opcode.CMP:
            self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_DR)
            self.data_path.signal_latch_addr()
            self.tick()
            self.data_path.signal_latch_dr()
            self.data_path.signal_execute_alu_op(ALUOpcode.CMP, left_sel=Selectors.FROM_AC, right_sel=Selectors.FROM_DR)
            self.tick()
        elif opcode == Opcode.TEST:
            self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_DR)
            self.data_path.signal_latch_addr()
            self.tick()
            self.data_path.signal_latch_dr()
            self.data_path.signal_execute_alu_op(
                ALUOpcode.TEST, left_sel=Selectors.FROM_AC, right_sel=Selectors.FROM_DR
            )
            self.tick()
        elif opcode == Opcode.OUT:
            self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_DR)
            self.data_path.signal_latch_addr()
            self.tick()
            self.data_path.signal_latch_dr()
            self.data_path.signal_output()
            self.tick()
        elif opcode == Opcode.IN:
            self.data_path.signal_latch_ac(Selectors.FROM_INPUT)
            self.tick()

    def execute_branch(self, opcode, ps):
        if opcode == Opcode.JG:
            if not ps["N"]:
                self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_DR)
                self.data_path.signal_latch_pc()

        elif opcode == Opcode.JZ:
            if ps["Z"]:
                self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_DR)
                self.data_path.signal_latch_pc()

        elif opcode == Opcode.JNZ:
            if not ps["Z"]:
                self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_DR)
                self.data_path.signal_latch_pc()

        elif opcode == Opcode.JMP:
            self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_DR)
            self.data_path.signal_latch_pc()

        self.tick()

    def go_to_interrupt(self):
        #  Сохраняем на стеке PS и PC
        self.data_path.signal_execute_alu_op(ALUOpcode.DEC_B, right_sel=Selectors.FROM_SP)
        self.data_path.signal_latch_sp()
        self.data_path.signal_latch_addr()
        self.tick()
        self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_A, left_sel=Selectors.FROM_PS)
        self.data_path.signal_latch_to_mem()
        self.data_path.signal_wr()
        self.tick()
        self.data_path.signal_execute_alu_op(ALUOpcode.DEC_B, right_sel=Selectors.FROM_SP)
        self.data_path.signal_latch_sp()
        self.data_path.signal_latch_addr()
        self.tick()
        self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_PC)
        self.data_path.signal_latch_to_mem()
        self.data_path.signal_wr()
        self.tick()
        #  Перемещаем в PC адрес подпрограммы обработки прерывания
        self.data_path.dr = 1
        self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_DR)
        self.data_path.signal_latch_addr()
        self.tick()
        self.data_path.signal_latch_dr()
        self.data_path.signal_execute_alu_op(ALUOpcode.SKIP_B, right_sel=Selectors.FROM_DR)
        self.data_path.signal_latch_pc()

    def check_for_interruptions(self, enabled=False):
        position = 0
        for index, val in enumerate(self.data_path.input_buffer):
            if val["tick"] > self.current_tick():
                position = index
                break
        self.data_path.input_buffer = self.data_path.input_buffer[0 if position == 0 else position - 1 :]
        if not self.data_path.input_buffer:
            return
        schedule = self.data_path.input_buffer[0]
        if not enabled or self.current_tick() < schedule["tick"]:
            return
        self.mode = ProgramMode.INTERRUPT
        self.go_to_interrupt()

    def decode_and_execute_instruction(self):
        self.instr_fetch()
        self.execute()
        self.data_path.signal_latch_ps_flags()
        self.check_for_interruptions(self.data_path.ps["INT_EN"])

    def __repr__(self):
        return "TICK: {:4} | AC: {:4} | PC: {:3} | IR: {:5} | DR: {:7} | SP: {:3} | Addr: {:3} | ToMem: {:7} | N: {:1} | Z: {:1} | INT_EN: {:1} | mem[Addr]: {:7} | mode: {}".format(
            self.current_tick(),
            self.data_path.ac,
            self.data_path.pc,
            self.data_path.ir["opcode"],
            self.data_path.dr,
            self.data_path.sp,
            self.data_path.addr,
            self.data_path.to_mem,
            (1 if self.data_path.ps["N"] else 0),
            (1 if self.data_path.ps["Z"] else 0),
            (1 if self.data_path.ps["INT_EN"] else 0),
            self.data_path.memory[self.data_path.addr]["value"],
            self.mode,
        )


def simulation(code, input_tokens, memory_size, limit):
    data_path = DataPath(memory_size, input_tokens)
    control_unit = ControlUnit(code, data_path)
    instr_counter = 0

    logging.debug("%s", control_unit)
    try:
        while instr_counter < limit:
            control_unit.decode_and_execute_instruction()
            instr_counter += 1
            logging.debug("%s", control_unit)
    except HaltError:
        pass

    if instr_counter >= limit:
        logging.warning("Limit exceeded!")
    logging.info("output_symbol_buffer: %s", repr("".join(data_path.output_symbol_buffer)))
    logging.info("output_numeric_buffer: [%s]", ", ".join(str(x) for x in data_path.output_numeric_buffer))
    symbols = data_path.output_symbol_buffer
    numbers = data_path.output_numeric_buffer
    return symbols, numbers, instr_counter, control_unit.current_tick()


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
            tokens.append({"tick": tick, "symbol": symbol})
    return tokens


def main(code_file, input_file):
    code = read_code(code_file)
    input_token = parse_to_tokens(input_file)

    output_symbols, output_numbers, instr_counter, ticks = simulation(
        code,
        input_tokens=input_token,
        memory_size=200,
        limit=5000,
    )

    print("".join(output_symbols))
    print(output_numbers)
    print("instr_counter: ", instr_counter, "ticks:", ticks)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    assert len(sys.argv) == 3, "Wrong arguments: machine.py <code_file> <input_file>"
    _, code_file, input_file = sys.argv
    main(code_file, input_file)
