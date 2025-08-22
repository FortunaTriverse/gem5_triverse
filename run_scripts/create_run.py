import os
import shutil

path = os.getcwd()


store_path='../test_results/stats'


file_path = path + '/run_1.sh'

prefetchers = ['ampm','dcpt','isb','sbooe','spp','slim','stride','tagged']
prefetchers += ['xsberti','xsbop','xsopt','xsstream']
prefetchers += ['triangel','triage','triverse','triverse_bloom']

title = 'cleanup(){\n	echo \"removing the task\"\n	pkill -P $$\n	echo \"remove all\"\n}\ntrap cleanup EXIT INT TERM\n\n'
title += 'cd ..\nHOME=$(pwd)\nSTATS=$(date -I)\ncd Checkpoints\n\n'
title += f'STORE={store_path}\n'
title += 'if [ ! -d \"$STORE\" ]; then\n  mkdir -p \"$STORE\"\nfi\n'
title += '\nMAX_JOBS=55\nfifo=$(mktemp -u)\nmkfifo \"$fifo\"\nexec 5<>\"$fifo\"\nrm -f \"$fifo\"\nfor ((i=0;i<MAX_JOBS;i++));do echo;done >&5\n\n'
title += 'for BENCH in *\ndo\n	read -u5\n	(\n	cd $HOME/Checkpoints/$BENCH\n\n'
title += '	COUNT=$(ls -d m5out/*/ | wc -l)\n	for I in $(seq 1 $COUNT)\n'
title += '	do\n'
title += f'    if [ ! -d \"$STORE/NoPF\" ]; then\n        mkdir -p \"$STORE/NoPF\"\n      fi\n'
title += f'	    (\n		if $HOME/build/X86/gem5.opt --stats-file=NoPF.txt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU -r $I --maxinsts=5000000 --pl2sl3cache --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32  >> stdout$STATS.txt 2>&1 ; then\n'
title += f'		cat m5out/stats.txt >> $STORE/NoPF/$BENCH.txt\n'
title += f'    	else\n    	  echo "gem5 error :NoPF $BENCH $I" >&2\n    	fi\n	    )&\n'

f = open(file_path,'w')
f.write(title)
f.close()

for prefetcher in prefetchers:
  f = open(file_path,'a')
  data  = f'    if [ ! -d \"$STORE/{prefetcher}\" ]; then\n        mkdir -p \"$STORE/{prefetcher}\"\n      fi\n'
  data += f'	    (\n		if $HOME/build/X86/gem5.opt --stats-file={prefetcher}.txt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --{prefetcher} -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then\n'
  data += f'		  cat m5out/{prefetcher}.txt >> $STORE/{prefetcher}/$BENCH.txt\n'
  data += f'    	else\n    	  echo "gem5 error :{prefetcher} $BENCH $I" >&2\n    	fi\n	    )&\n'
  f.write(data)
  f.close()

f = open(file_path,'a')
data  = f'    if [ ! -d \"$STORE/triangelBloom\" ]; then\n        mkdir -p \"$STORE/triangelBloom\"\n      fi\n'
data += f'	    (\n		if $HOME/build/X86/gem5.opt --stats-file=triangelBloom.txt $HOME/configs/deprecated/example/fs.py --disk-image=$HOME/x86-ubuntu --kernel=$HOME/vmlinux-5.4.49 -n 1 --mem-size=4GB --cpu-type=X86O3CPU --triangel --triangelbloom -r $I --maxinsts=5000000 --pl2sl3cache  --standard-switch 50000000 --warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 >> stdout$STATS.txt 2>&1 ; then\n'
data += f'		  cat m5out/triangelBloom.txt >> $STORE/triangelBloom/$BENCH.txt\n'
data += f'    	else\n    	   echo "gem5 error :triangelBloom $BENCH $I" >&2\n    	fi\n	    )&\n'
f.write(data)
f.close()



