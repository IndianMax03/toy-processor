org 10
limit:
    .word 4000000
prev:
    .word 1
cur:
    .word 2
tmp:
    .word 0
result:
    .word 0
out_port:
    .word 1

_start:
    loop:
        load cur
        cmp limit
        jg end
        test 1
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
        jmp loop
    end:
        load limit
        out out_port
    halt