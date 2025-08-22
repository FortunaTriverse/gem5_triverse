cleanup(){
	echo "removing the task"
	pkill -P $$
	echo "remove all"
}
trap cleanup EXIT INT TERM

cd ..
HOME=$(pwd)
STATS=$(date -I)
cd Checkpoints

STORE=/home/fanqingxin/Desktop/gem5-23/test_results/stats/$STATS
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
    if [ ! -d "$STORE/t1_bloom_v3" ]; then
        mkdir -p "$STORE/t1_bloom_v3"
      fi
		if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --t1_bloom --stride_mode=2 --filter_size=64 --monitor_accuracy=0 --dec_stride_thre=40 --dynamic_mode=2 --stream_degree=3 -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		  cat m5out/stats.txt >> $STORE/t1_bloom_v3/$BENCH-stride_mode=2-filter_size=64-monitor_accuracy=0-dec_stride_thre=40.txt
    	else
    	   echo "gem5 error :stride_mode=2-filter_size=64-maxstride=64-monitor_accuracy=0 $BENCH $I" >&2
    	fi
		if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --t1_bloom --stride_mode=2 --filter_size=64 --monitor_accuracy=1 --dec_stride_thre=40 --dynamic_mode=2 --stream_degree=3 -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		  cat m5out/stats.txt >> $STORE/t1_bloom_v3/$BENCH-stride_mode=2-filter_size=64-monitor_accuracy=1-dec_stride_thre=40.txt
    	else
    	   echo "gem5 error :stride_mode=2-filter_size=64-maxstride=64-monitor_accuracy=1 $BENCH $I" >&2
    	fi
		if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --t1_bloom --stride_mode=2 --filter_size=64 --monitor_accuracy=0 --dec_stride_thre=50 --dynamic_mode=2 --stream_degree=3 -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		  cat m5out/stats.txt >> $STORE/t1_bloom_v3/$BENCH-stride_mode=2-filter_size=64-monitor_accuracy=0-dec_stride_thre=50.txt
    	else
    	   echo "gem5 error :stride_mode=2-filter_size=64-maxstride=64-monitor_accuracy=0 $BENCH $I" >&2
    	fi
		if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --t1_bloom --stride_mode=2 --filter_size=64 --monitor_accuracy=1 --dec_stride_thre=50 --dynamic_mode=2 --stream_degree=3 -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		  cat m5out/stats.txt >> $STORE/t1_bloom_v3/$BENCH-stride_mode=2-filter_size=64-monitor_accuracy=1-dec_stride_thre=50.txt
    	else
    	   echo "gem5 error :stride_mode=2-filter_size=64-maxstride=64-monitor_accuracy=1 $BENCH $I" >&2
    	fi
		if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --t1_bloom --stride_mode=2 --filter_size=64 --monitor_accuracy=0 --dec_stride_thre=60 --dynamic_mode=2 --stream_degree=3 -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		  cat m5out/stats.txt >> $STORE/t1_bloom_v3/$BENCH-stride_mode=2-filter_size=64-monitor_accuracy=0-dec_stride_thre=60.txt
    	else
    	   echo "gem5 error :stride_mode=2-filter_size=64-maxstride=64-monitor_accuracy=0 $BENCH $I" >&2
    	fi
		if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --t1_bloom --stride_mode=2 --filter_size=64 --monitor_accuracy=1 --dec_stride_thre=60 --dynamic_mode=2 --stream_degree=3 -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		  cat m5out/stats.txt >> $STORE/t1_bloom_v3/$BENCH-stride_mode=2-filter_size=64-monitor_accuracy=1-dec_stride_thre=60.txt
    	else
    	   echo "gem5 error :stride_mode=2-filter_size=64-maxstride=64-monitor_accuracy=1 $BENCH $I" >&2
    	fi
		if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --t1_bloom --stride_mode=2 --filter_size=128 --monitor_accuracy=0 --dec_stride_thre=40 --dynamic_mode=2 --stream_degree=3 -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		  cat m5out/stats.txt >> $STORE/t1_bloom_v3/$BENCH-stride_mode=2-filter_size=128-monitor_accuracy=0-dec_stride_thre=40.txt
    	else
    	   echo "gem5 error :stride_mode=2-filter_size=128-maxstride=64-monitor_accuracy=0 $BENCH $I" >&2
    	fi
		if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --t1_bloom --stride_mode=2 --filter_size=128 --monitor_accuracy=1 --dec_stride_thre=40 --dynamic_mode=2 --stream_degree=3 -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		  cat m5out/stats.txt >> $STORE/t1_bloom_v3/$BENCH-stride_mode=2-filter_size=128-monitor_accuracy=1-dec_stride_thre=40.txt
    	else
    	   echo "gem5 error :stride_mode=2-filter_size=128-maxstride=64-monitor_accuracy=1 $BENCH $I" >&2
    	fi
		if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --t1_bloom --stride_mode=2 --filter_size=128 --monitor_accuracy=0 --dec_stride_thre=50 --dynamic_mode=2 --stream_degree=3 -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		  cat m5out/stats.txt >> $STORE/t1_bloom_v3/$BENCH-stride_mode=2-filter_size=128-monitor_accuracy=0-dec_stride_thre=50.txt
    	else
    	   echo "gem5 error :stride_mode=2-filter_size=128-maxstride=64-monitor_accuracy=0 $BENCH $I" >&2
    	fi
		if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --t1_bloom --stride_mode=2 --filter_size=128 --monitor_accuracy=1 --dec_stride_thre=50 --dynamic_mode=2 --stream_degree=3 -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		  cat m5out/stats.txt >> $STORE/t1_bloom_v3/$BENCH-stride_mode=2-filter_size=128-monitor_accuracy=1-dec_stride_thre=50.txt
    	else
    	   echo "gem5 error :stride_mode=2-filter_size=128-maxstride=64-monitor_accuracy=1 $BENCH $I" >&2
    	fi
		if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --t1_bloom --stride_mode=2 --filter_size=128 --monitor_accuracy=0 --dec_stride_thre=60 --dynamic_mode=2 --stream_degree=3 -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		  cat m5out/stats.txt >> $STORE/t1_bloom_v3/$BENCH-stride_mode=2-filter_size=128-monitor_accuracy=0-dec_stride_thre=60.txt
    	else
    	   echo "gem5 error :stride_mode=2-filter_size=128-maxstride=64-monitor_accuracy=0 $BENCH $I" >&2
    	fi
		if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --t1_bloom --stride_mode=2 --filter_size=128 --monitor_accuracy=1 --dec_stride_thre=60 --dynamic_mode=2 --stream_degree=3 -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		  cat m5out/stats.txt >> $STORE/t1_bloom_v3/$BENCH-stride_mode=2-filter_size=128-monitor_accuracy=1-dec_stride_thre=60.txt
    	else
    	   echo "gem5 error :stride_mode=2-filter_size=128-maxstride=64-monitor_accuracy=1 $BENCH $I" >&2
    	fi
		if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --t1_bloom --stride_mode=2 --filter_size=256 --monitor_accuracy=0 --dec_stride_thre=40 --dynamic_mode=2 --stream_degree=3 -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		  cat m5out/stats.txt >> $STORE/t1_bloom_v3/$BENCH-stride_mode=2-filter_size=256-monitor_accuracy=0-dec_stride_thre=40.txt
    	else
    	   echo "gem5 error :stride_mode=2-filter_size=256-maxstride=64-monitor_accuracy=0 $BENCH $I" >&2
    	fi
		if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --t1_bloom --stride_mode=2 --filter_size=256 --monitor_accuracy=1 --dec_stride_thre=40 --dynamic_mode=2 --stream_degree=3 -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		  cat m5out/stats.txt >> $STORE/t1_bloom_v3/$BENCH-stride_mode=2-filter_size=256-monitor_accuracy=1-dec_stride_thre=40.txt
    	else
    	   echo "gem5 error :stride_mode=2-filter_size=256-maxstride=64-monitor_accuracy=1 $BENCH $I" >&2
    	fi
		if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --t1_bloom --stride_mode=2 --filter_size=256 --monitor_accuracy=0 --dec_stride_thre=50 --dynamic_mode=2 --stream_degree=3 -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		  cat m5out/stats.txt >> $STORE/t1_bloom_v3/$BENCH-stride_mode=2-filter_size=256-monitor_accuracy=0-dec_stride_thre=50.txt
    	else
    	   echo "gem5 error :stride_mode=2-filter_size=256-maxstride=64-monitor_accuracy=0 $BENCH $I" >&2
    	fi
		if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --t1_bloom --stride_mode=2 --filter_size=256 --monitor_accuracy=1 --dec_stride_thre=50 --dynamic_mode=2 --stream_degree=3 -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		  cat m5out/stats.txt >> $STORE/t1_bloom_v3/$BENCH-stride_mode=2-filter_size=256-monitor_accuracy=1-dec_stride_thre=50.txt
    	else
    	   echo "gem5 error :stride_mode=2-filter_size=256-maxstride=64-monitor_accuracy=1 $BENCH $I" >&2
    	fi
		if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --t1_bloom --stride_mode=2 --filter_size=256 --monitor_accuracy=0 --dec_stride_thre=60 --dynamic_mode=2 --stream_degree=3 -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		  cat m5out/stats.txt >> $STORE/t1_bloom_v3/$BENCH-stride_mode=2-filter_size=256-monitor_accuracy=0-dec_stride_thre=60.txt
    	else
    	   echo "gem5 error :stride_mode=2-filter_size=256-maxstride=64-monitor_accuracy=0 $BENCH $I" >&2
    	fi
		if $HOME/build/X86/gem5.opt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --t1_bloom --stride_mode=2 --filter_size=256 --monitor_accuracy=1 --dec_stride_thre=60 --dynamic_mode=2 --stream_degree=3 -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then
		  cat m5out/stats.txt >> $STORE/t1_bloom_v3/$BENCH-stride_mode=2-filter_size=256-monitor_accuracy=1-dec_stride_thre=60.txt
    	else
    	   echo "gem5 error :stride_mode=2-filter_size=256-maxstride=64-monitor_accuracy=1 $BENCH $I" >&2
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
