org 10
limit:
    .word 4000000
odd:
    .word 1
prev:
    .word 1
cur:
    .word 2
tmp:
    .word 0
result:
    .word 0
out_port:
    .word 2

_start:
    load cur
    cmp limit
    jg end
    test odd
    jnz finally
    if_even:
        load result
        add cur
        store result
    finally:
        load cur
        store tmp
        add prev
        store cur
        load tmp
        store prev
    jmp _start
    end:
        load result
        out out_port
    halt
