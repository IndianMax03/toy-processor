# Игрушечный процессор

## Детали выполненной работы

### Автор

 > Тучков Максим Русланович, P33121
 
### Вариант

 > asm | acc | neum | hw | instr | struct | trap | port | pstr | prob2 | spi
 >
 > Без усложнения

 ### Описание варианта

- **asm** -- синтаксис ассемблера. Необходима поддержка label-ов.
- **acc** -- система команд должна быть выстроена вокруг аккумулятора.
    - Инструкции -- изменяют значение, хранимое в аккумуляторе.
    - Ввод-вывод осуществляется через аккумулятор.
- **neum** -- фон Неймановская архитектура.
- **hw (hardwired)** -- ContolUnit реализуется как часть модели.
- **instr** -- процессор необходимо моделировать с точностью до каждой инструкции (наблюдается состояние после каждой инструкции).
- **struct** -- машинный код в виде высокоуровневой структуры данных. Считается, что одна инструкция укладывается в одно машинное слово.
- **trap** -- ввод-вывод осуществляется токенами через систему прерываний.
- **port (port-mapped)** -- (специальные инструкции для ввода-вывода).
    - адресация портов ввода-вывода должна присутствовать.
- **pstr (Length-prefixed / Pascal string)** -- перед строкой указывается её длина
- **prob2** -- Even Fibonacci numbers (сумма четных чисел Фибонначи, не превышающих 4 млн).
- **spi** -- ввод-вывод реализуется через интерфейс SPI (один канал на отправку и получение).
    - необходима визуализация передачи данных через SPI.


## Язык программирования

### Форма Бэкуса-Наура

```ebnf
<program> ::= <program_line> | <program_line> <end_of_line> <program>

<program_line> ::= <code_line> | <comment> | <code_line> <comment>

<code_line> ::= <data_definition> | <address_definition> | <label_definition> | <directive>

<address_definition> ::= "org" <non_neg_number>

<label_definition> ::= <label> ":"

<data_definition> ::= <label> ":" <end_of_line> <data>

<data> ::= ".word" <operand> | ".word" <non_neg_number> "," <string>

<operand> ::= <number> | <label>

<directive> ::= <onear_instruction> <address_link> | <branch_instruction> <address_link> | <nullar_instruction>

<address_link> = <label> | "(" <label> ")"

<label> ::= <word>

<string> ::= "'" <text> "'"

<comment> ::= ";" <text>

<text> ::= <word> | <word> <text>

<word> ::= <letter> | <letter> <word>

<number> ::= [-]<non_neg_number>

<non_neg_number> ::= <digit> | <digit> <non_neg_number>

<nullar_instruction> ::= "inc" | "dec" | "halt" | "ei" | "di" | "push" | "pop" | "iret"

<branch_instruction> ::= "jg" | "jz" | "jnz" | "jmp"

<onear_instruction> ::= "load" | "store" | "add" | "out" | "in" | "cmp" | "test"

<letter> ::= "a" | "b" | "c" | ... | "z" | "A" | "B" | "C" | ... | "Z" | <digit>

<end_of_line> ::= "\n" | "\r\n"

<digit> ::= "0" | "1" | "2" |  ... | "9"
```

### Краткое описание

Любая непустая строка -- это:

- Метка (`<label_definition>`)
    - Последовательность символов с двоеточием на конце
- Опеределение данных = Метка + Данные  (`<data_definition>`)
    - Данные требуют обязательного ключевого слова *.word*
- Определение адреса (`<address_definition>`)
    - Требует ключевого слова *org* с последующим указанием адреса
- Директива = инструкция + метка (`<directive>`)
    - Все инструкции с одним аргументом -- адресные
- Комментарий -- это любая последовательность символов после *;*

### Семантика

- Глобальная видимость данных
- Поддерживаются целочисленные литералы (без ограничений на размер)
- Поддерживаются строковые литералы в виде Length-prefixed
    - Пример объявления строковых данных: `.word 7, 'Penskoi'`
- Код выполняется последовательно
- Точка входа в программу -- метка `_start` (метка не может повторяться или отсутствовать)
- Название метки не должно:
    - совпадать с названием команды
    - начинаться с цифры
    - совпадать с ключевыми словами `org` или `.word`
- Метки располагаются на строке, предшествующей строке с командой, операнды находятся на одной строке с командами
- Пробельные символы в конце и в начале строки игнорируются
- Любой текст, расположенный в конце строки после символа `;` трактуется как комментарий

Память выделяется статически, при запуске модели.

## Организация памяти

```text
               Registers
+------------------------------------+
| AC - аккумулятор                   |
+------------------------------------+
| IR - регистр инструкции            |
+------------------------------------+
| DR - регистр данных                |
+------------------------------------+
| PC - счётчик команд                |
+------------------------------------+
| SP - указатель стека               |
+------------------------------------+
| Addr - адрес записи в память       |
+------------------------------------+
| ToMem - данные при записи в память |
+------------------------------------+
| PS - состояние программы           |
+------------------------------------+

            Instruction & Data memory
+-----------------------------------------------+
|    0    :  jmp _start                         |  <-- PC, SP
|    1    :  interruption vector address (iva)  |
|        ...                                    |
| _start  :  program start                      |
|        ...                                    |
|   iva   :  interruption handler               |
|        ...                                    |
+-----------------------------------------------+
```

- Память данных и команд общая (фон Нейман)
- Размер машинного слова не определен (достаточно, чтобы влезало число для `prob2`)
- Размер памяти не определен (определяется при симуляции)
- Адрес `0` зарезервирован для перехода к началу программы
- Адрес `1` зарезервирован для указания адреса подпрограммы обработки прерывания ввода
- Виды адресации:
    - абсолютная
    - косвенная
- Назначение регистров
    - AC -- главный регистр (аккумуляторная архитектура), содержит результаты всех операций, подключен к портам ввода-вывода
    - IR -- содержит текущую выполняемую инструкцию
    - DR -- содержит временные данные для выполнения операций
    - PC -- содержит адрес следующей инструкции, которая должна быть выполнена
    - SP -- при операциях push и pop уменьшается и увеличивается соответственно (стек растет снизу вверх)
    - Addr -- содержит адрес, по которому произойдет запись в память (при we)
    - ToMem -- содержит данные, которые должны быть записаны в память (при we)
    - PS -- хранит состояние флагов (N, Z) и разрешение прерывания

## Система команд

### Особенности процессора (всё необходимое для понимания системы команд):

- типы данных и машинных слов;
- устройство памяти и регистров, адресации;
- устройство ввода-вывода;
- поток управления и системы прерываний;
- и т.п.


### Набор инструкций.
- Способ кодирования инструкций:
    - по умолчанию можно использовать современные структуры данных;
    - требование бинарного кодирования -- особенность конкретного варианта.


### Описания системы команд должно быть достаточно для её классификации (CISC, RISC, Acc, Stack).

текст

## Транслятор

Раздел подразумевает разработку консольного приложения:

### Входные данные

- Имя файла с исходным кодом в текстовом виде.
- Имя файла для сохранения полученного машинного кода.
- Другие аргументы командной строки (ключи, настройки, и т.п.).

### Выходные данные

- Имя выходного файла для машинного кода.



> Раздел должен включать описание:
>
> Интерфейса командной строки.
>
> Принципов работы разработанного транслятора (этапы, правила и т.п.).

## Модель процессора

Раздел подразумевает разработку консольного приложения:


### Входные данные:

- Имя файла для чтения машинного кода.
- Имя файла с данными для имитации ввода в процессор.

### Выходные данные:

- Вывод данных из процессора.
- Журнал состояний процессора, включающий:
    - состояния регистров процессора;
    - выполняемые инструкции (возможно, микрокод) и соответствующие им исходные коды;
    - ввод/вывод из процессора.

> Раздел должен включать:
>
> Схемы DataPath и ControlUnit, описание сигналов и флагов
>
> Особенности реализации процесса моделирования.

## Тестирование

- Краткое описание разработанных тестов.

- Описание работы настроенного CI.

- Реализацию следующих алгоритмов (должны проверяться в рамках интеграционных тестов)

- Необходимо показать работу разработанных алгоритмов.

> Кроме того, в конце отчёта необходимо привести следующий текст для трёх реализованных алгоритмов (необходимо для сбора общей аналитики по проекту):
>
> | ФИО | <алг> | <LoC> | <code байт> | <code инстр.> | <инстр.> | <такт.> | <вариант> |
>
> где:
>
> алг. -- название алгоритма (hello, cat, или как в варианте)
>
> прог. LoC -- кол-во строк кода в реализации алгоритма
>
> code байт -- кол-во байт в машинном коде (если бинарное представление)
>
> code инстр. -- кол-во инструкций в машинном коде
>
> инстр. -- кол-во инструкций, выполненных при работе алгоритма
>
> такт. -- кол-во тактов, которое заняла работа алгоритма
