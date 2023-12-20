org 10
message:
    .word 13, 'Hello, World!'
pointer:
    .word message
cycles:
    .word 0
out_port:
    .word 1

_start:
    load message
    jz end
    store cycles
    loop:
        load pointer
        inc
        store pointer
        load (pointer)
        out out_port
        load cycles
        dec
        store cycles
        jnz loop
    end:
        halt
