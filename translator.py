import sys

from isa import Opcode, write_code

def symbol_to_opcode(symbol):
    """Отображение операторов исходного кода в коды операций."""
    return {
        "nop": Opcode.NOP,
        "inc": Opcode.INC,
        "dec": Opcode.DEC,
        "halt": Opcode.HALT,
        "ei": Opcode.EI,
        "di": Opcode.DI,
        "push": Opcode.PUSH,
        "pop": Opcode.POP,
        "iret": Opcode.IRET,
        "load": Opcode.LOAD,
        "store": Opcode.STORE,
        "out": Opcode.OUT,
        "in": Opcode.IN,
        "cmp": Opcode.CMP,
        "test": Opcode.TEST,
        "jg": Opcode.JG,
        "jz": Opcode.JZ,
        "jnz": Opcode.JNZ,
        "jmp": Opcode.JMP,
    }.get(symbol, Opcode.NOP)

def read_lines(source_filename: str) -> [str]:
    """Построчно читаем файл, убираем отступы и пустые строки"""
    lines = []
    with open(source_filename) as file:
        for line in file:
            line = line.strip()
            if line != '':
                lines.append(line)
    return lines

def remove_comments(code_lines) -> [str]:
    """Убираем комменарии"""
    without_comments= []
    for line in code_lines:
        index = line.find(';')
        if index == -1:
            without_comments.append(line)
            continue
        line = line[0 : line.find(';')].strip()
        if line != '':
            without_comments.append(line)
    return without_comments

def parse_word(position, word_line, words):
    """Индексация слова данных (в т.ч. разбиение строк по буквам)"""
    char_num = 0
    while char_num < len(word_line):
        if word_line[char_num] == "'":
            char_num += 1
            while word_line[char_num] != "'":
                words[position] = [ord(word_line[char_num])]
                position += 1
                char_num += 1
            char_num += 1
        elif word_line[char_num].isnumeric():
            cur_num = word_line[char_num]
            char_num += 1
            while char_num < len(word_line) and word_line[char_num].isnumeric():
                cur_num += word_line[char_num]
                char_num += 1
            words[position] = [int(cur_num)]
            position += 1
        elif word_line[char_num] == ',' or word_line[char_num] == ' ':
            char_num += 1
        else:
            label = ''
            while char_num < len(word_line) and word_line[char_num] != ',' and word_line[char_num] != ' ':
                label += word_line[char_num]
                char_num += 1
            words[position] = [label]
            position += 1
    return position, words         
    
def lines_to_words_and_labels(code_lines):
    """Трансляция строк кода в операторы (без привязки к языку)"""
    labels = {}
    words = {}
    position = 0
    for line in code_lines:
        if line.startswith('org'):
            position = int(line.split(' ')[1])
        elif line[-1] == ':':
            labels[position] = line[0:-1]
        elif line.startswith('.word'):
            position, words = parse_word(position, line[6:], words)
        else:
            args = line.split(' ')
            kv = [args[0]]
            if len(args) == 2:
                kv.append(args[1])
            words[position] = kv
            position += 1
    return words, labels

def find_program_start(labels):
    counter = 0
    position = None
    for index, label in labels.items():
        if (label == '_start'):
            counter += 1
            position = index
    assert counter == 1, f"Error: got _start label {counter} times"
    return position

def link_labels(words, labels):
    """Подмена меток на индексы + установка вида адресации (True - косвенный)"""
    replaced = {}
    for w_index, word in words.items():
        new_word = []
        indirect = False
        for part in word:
            if (isinstance(part, str) and part.startswith('(')):
                indirect = True
                part = part[1:-1]
            for l_index, label in labels.items():
                if (label == part):
                    part = l_index
            new_word.append(part)
        new_word.append(indirect)
        replaced[w_index] = new_word
    return replaced

def to_machine_code(raw_code):
    code = []
    for index, word in raw_code.items():
        if len(word) == 2:
            code.append({"index" : index, "opcode": symbol_to_opcode(word[0]), "value": word[0] if word[0] not in Opcode._value2member_map_ else None, "is_indirect": word[1]})
        elif len(word) == 3:
            code.append({"index" : index, "opcode": symbol_to_opcode(word[0]), "value": word[1], "is_indirect": word[2]})
        else:
            raise f"Incorrect operands count = {len(word)}"
    return code

def translate(source_filename, debug_mode = False):
    """Многопроходная трансляция программы в машинный код"""
    lines = read_lines(source_filename)
    lines_without_comments = remove_comments(lines)
    words, labels = lines_to_words_and_labels(lines_without_comments)
    _start_position = find_program_start(labels)
    raw_code = link_labels(words, labels)
    code = to_machine_code(raw_code)
    
    if debug_mode:
        print(f"------> TRANSLATOR: DEBUG MODE ON")
        print(f"------> DEBUG: FOUND _start POSITION AT mem({_start_position})")
        print(f"------> DEBUG: FOUND LABELS")
        for index, label in labels.items():
            print(f"mem({index}) -> {label}")
        print(f"------> DEBUG: FOUND WORDS")
        for index, word in words.items():
            print(f"mem({index}) -> {word}")
        print(f"------> DEBUG: RAW CODE")
        for index, raw_opertion in raw_code.items():
            print(f"mem({index}) -> {raw_opertion}")
    
    return code

def main(source_filename, target_filename):
    code = translate(source_filename)
    
    write_code(target_filename, code)

if __name__ == "__main__":
    assert len(sys.argv) == 3, "Wrong arguments: translator.py <input_file> <target_file>"
    _, source_filename, target_filename = sys.argv
    main(source_filename, target_filename)
