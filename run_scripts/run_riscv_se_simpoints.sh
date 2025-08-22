cleanup(){
	echo "removing the task"
	pkill -P $$
	echo "remove all"
}
trap cleanup EXIT INT TERM

cd ..
HOME=$(pwd)
STATS=$(date -I)
cd simpoints_2006

STORE=$HOME/riscv_simpoints_results/stats
if [ ! -d "$STORE" ]; then
  mkdir -p "$STORE"
fi

MAX_JOBS=60
fifo=$(mktemp -u)
mkfifo "$fifo"
exec 5<>"$fifo"
rm -f "$fifo"
for ((i=0;i<MAX_JOBS;i++));do echo;done >&5


for BENCH in *
do
	read -u5
	(
    BENCHPATH=$HOME/simpoints_2006/$BENCH
    if [ -d "$BENCHPATH" ]; then
	    cd $BENCHPATH

        COUNT=$(ls -d m5out/ckpt*/ | wc -l)
        for I in $(seq 1 $COUNT)
	    do

            if [ ! -d "$STORE/NoPF" ]; then
                mkdir -p "$STORE/NoPF"
            fi
		    if $HOME/build/RISCV/gem5.opt $HOME/configs/deprecated/example/se.py --mem-size=4GB \
            	    --cmd=$(find $BENCHPATH -maxdepth 1 -type f -name "*.riscv") \
				    --checkpoint-dir "$BENCHPATH/m5out" --restore-simpoint \
				    --cpu-type RiscvO3CPU --standard-switch 50000000 --warmup-insts 50000000 -I 50000000 \
				    --pl2sl3cache --mem-type=LPDDR5_5500_1x16_BG_BL32 -r $I  >> stdout$STATS.txt 2>&1 ; then
		        cat m5out/stats.txt >> $STORE/NoPF/$BENCH.txt
    	    else
    	        echo "gem5 error :NoPF $BENCH $I" >&2
    	    fi  

            if [ ! -d "$STORE/triverse" ]; then
                mkdir -p "$STORE/triverse"
            fi
		    if $HOME/build/RISCV/gem5.opt $HOME/configs/deprecated/example/se.py --mem-size=4GB \
            	    --cmd=$(find $BENCHPATH -maxdepth 1 -type f -name "*.riscv") \
				    --checkpoint-dir "$BENCHPATH/m5out" --restore-simpoint \
				    --cpu-type RiscvO3CPU --standard-switch 50000000 --warmup-insts 50000000 -I 50000000 \
				    --pl2sl3cache --triverse --mem-type=LPDDR5_5500_1x16_BG_BL32 -r $I  >> stdout$STATS.txt 2>&1 ; then
		        cat m5out/stats.txt >> $STORE/triverse/$BENCH.txt
    	    else
    	        echo "gem5 error :triverse $BENCH $I" >&2
    	    fi  

            if [ ! -d "$STORE/triverse" ]; then
                mkdir -p "$STORE/triverse"
            fi
		    if $HOME/build/RISCV/gem5.opt $HOME/configs/deprecated/example/se.py --mem-size=4GB \
            	    --cmd=$(find $BENCHPATH -maxdepth 1 -type f -name "*.riscv") \
				    --checkpoint-dir "$BENCHPATH/m5out" --restore-simpoint \
				    --cpu-type RiscvO3CPU --standard-switch 50000000 --warmup-insts 50000000 -I 50000000 \
				    --pl2sl3cache --triverse_bloom --mem-type=LPDDR5_5500_1x16_BG_BL32 -r $I  >> stdout$STATS.txt 2>&1 ; then
		        cat m5out/stats.txt >> $STORE/triverse_bloom/$BENCH.txt
    	    else
    	        echo "gem5 error :triverse_bloom $BENCH $I" >&2
    	    fi  			

	    done
        echo >&5
    fi
	)&
done
    echo "Waiting for runs to finish. Check local stdout files in each folder for progress..."
    wait
    exec 5>&-
    echo "Finished!"
cd $HOME/run_scripts