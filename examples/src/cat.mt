org 1
vector:
    .word interrupt

org 10
in_port:
    .word 0
out_port:
    .word 1
flag:
    .word 0
line_feed:
    .word 10

_start:
    ei
    spin_loop:
        load flag
        jz spin_loop
    halt

interrupt:
    di
    in in_port
    out out_port
    cmp line_feed
    jnz returning
    load flag
    inc
    store flag
    returning:
        iret
