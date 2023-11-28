echo "T;C;equ;noimp;steps;last_change;last_improve;sat_cnt;clause_cnt;init_sat_cnt" > out.txt
for T in 20 100 500 1000
do
    for C in 0.9 0.95 0.99 0.999
    do
        for equ in 1 10 100
        do
            for noimp in 1000 2000 5000
            do
                for i in {1..10}
                do
                    echo -n "$T;$C;$equ;$noimp;" >> out.txt
                    cat uf100-430/uf100-01.cnf | ./sasat -T $T -c $C -n $equ -b $noimp -e 2>> out.txt
                done
            done
        done
    done
done

