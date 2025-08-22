cleanup(){
	echo "removing the task"
	pkill -P $$
	echo "remove all"
}
trap cleanup EXIT INT TERM

cd ..
HOME=$(pwd)
cd Checkpoints

STORE=$HOME/test_results/stats
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
	cd $HOME/Checkpoints/$BENCH
	COUNT=$(ls -d m5out/*/ | wc -l)
	for I in $(seq 1 $COUNT)
	do

	if [ ! -d "$STORE/NoPF" ]; then
        mkdir -p "$STORE/NoPF"
    fi
	if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 \
		--mem-size=4GB --cpu-type=X86O3CPU -r $I --maxinsts=5000000 --pl2sl3cache --standard-switch 50000000 \
		 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		cat m5out/stats.txt >> $STORE/NoPF/$BENCH.txt
    else
    	echo "gem5 error :NoPF $BENCH $I" >&2
    fi

    if [ ! -d "$STORE/triverse" ]; then
        mkdir -p "$STORE/triverse"
    fi
	if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 \
		--mem-size=4GB --cpu-type=X86O3CPU -r $I --maxinsts=5000000 --pl2sl3cache --standard-switch 50000000 \
		 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 --triverse >> stdout$STATS.txt 2>&1 ; then
		cat m5out/stats.txt >> $STORE/triverse/$BENCH.txt
    else
    	echo "gem5 error :triverse $BENCH $I" >&2
    fi


    if [ ! -d "$STORE/triversebloom" ]; then
        mkdir -p "$STORE/triversebloom"
    fi
	if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 \
		--mem-size=4GB --cpu-type=X86O3CPU -r $I --maxinsts=5000000 --pl2sl3cache --standard-switch 50000000 \
		 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 --triverse_bloom >> stdout$STATS.txt 2>&1 ; then
		cat m5out/stats.txt >> $STORE/triversebloom/$BENCH.txt
    else
    	echo "gem5 error :triversebloom $BENCH $I" >&2
    fi

	done
  echo >&5
	)&
done
	echo "Waiting for runs to finish. Check local stdout files in each folder for progress..."
	wait
  exec 5>&-
	echo "Finished!"
cd $HOME/run_scripts
