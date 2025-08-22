cleanup(){
	echo "removing the task"
	pkill -P $$
	echo "remove all"
}
trap cleanup EXIT INT TERM

cd ..
HOME=$(pwd)
STATS=$(date -I)
cd 2_core

STORE=$HOME/test_results/stats/$STATS
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
	cd $HOME/2_core/$BENCH

	COUNT=$(ls -d m5out/*/ | wc -l)
	for I in $(seq 1 $COUNT)
	do

    if [ ! -d "$STORE/2cores_triversebloom" ]; then
        mkdir -p "$STORE/2cores_triversebloom"
      fi
	if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu \
		--kernel=$HOME/vmlinux-5.4.49 -n 2 --mem-size=4GB --cpu-type=X86O3CPU  --triverse_bloom \
		--pl2sl3cache --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		cat m5out/stats.txt >> $STORE/2cores_triversebloom/$BENCH.txt
    else
    	echo "gem5 error :2cores_triversebloom $BENCH $I" >&2
    fi

$HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/2_core/x86-ubuntu \
  --kernel=../../vmlinux-5.4.49 -n 2 --mem-size=4GB --cpu-type=X86O3CPU -r 3 \
  --maxinsts=5000000 --pl2sl3cache --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32


	done
  echo >&5
	)&
done
	echo "Waiting for runs to finish. Check local stdout files in each folder for progress..."
	wait
  exec 5>&-
	echo "Finished!"
cd $HOME/run_scripts
