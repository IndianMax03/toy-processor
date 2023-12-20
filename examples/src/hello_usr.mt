org 0
vector:
    .word interrupt

org 10
message:
    .word 18, 'What is your name?'
message_pointer:
    .word message
greeting:
    .word 7, 'Hello, '
greeting_pointer:
    .word greeting
exclamation:
    .word 1, '!'
exclamation_pointer:
    .word exclamation
cycles:
    .word 0
in_port:
    .word 0
out_port:
    .word 1
flag:
    .word 0
line_feed:
    .word 10

_start:
    ; вывод вопрошающего сообщения
    load message
    store cycles
    message_loop:
        load message_pointer
        inc
        store message_pointer
        load (message_pointer)
        out out_port
        load cycles
        dec
        store cycles
        jnz message_loop
    ; ожидание ввода
    ei
    spin_loop:
        load flag
        jz spin_loop
    ; вывод приветствия
    load greeting
    store cycles
    greeting_loop:
        load greeting_pointer
        inc
        store greeting_pointer
        load (greeting_pointer)
        out out_port
        load cycles
        dec
        store cycles
        jnz greeting_loop
    load buffer_len
    store cycles
    name_loop:
        load (buffer_pointer)
        out out_port
        load cycles
        dec
        store cycles
        jnz name_loop
    exclamation_printing:
        load exclamation_pointer
        inc
        load (exclamation_pointer)
        out out_port
    halt
    

interrupt:
    di ; запрет вложенных прерываний
    push ; сохранение аккумулятора
    in in_port ; получение слова из порта ввода
    store (buffer_pointer) ; сохранение в буфер
    load buffer_pointer ; сдвиг указателя
    inc
    store buffer_pointer
    load buffer_len ; увеличение длины
    inc
    store buffer_len
    cmp line_feed
    jnz returning
    load flag
    inc
    store flag
    returning:
        pop
        ei
        iret

buffer_len:
    .word 0
buffer_pointer:
    .worf buffer
buffer:
    .word 0
