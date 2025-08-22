# $1:core number, $2:benchmark, $3:checkpoints number

cd ..
GEM5=$(pwd)

cd Checkpoints

CORE_PATH=""$GEM5"/Checkpoints/$1_core"

echo "we are ready to preapre the checkpoints in core number of $1"

echo "Finished"

echo "################# run run run ###################"
cd $CORE_PATH/$2

echo "run to get the overall tick of this benchmark"
echo "need to open another terminal and input port like "telnet localhost ""

M5OUT=$CORE_PATH/$2/m5out

if [ -d "$M5OUT" ]; then
    rm -rf $M5OUT
fi

$GEM5/build/X86/gem5.opt $GEM5/configs/deprecated/example/fs.py \
    -n $1 --mem-size=4GB --disk-image=$GEM5/x86-ubuntu \
    --kernel=$GEM5/vmlinux-5.4.49 --cpu-type=X86KvmCPU \
    --script=./run.rcS >> first.txt

echo "Finished overall tick get"

echo "############## get tick from file"
START=$(basename "$(find $M5OUT -maxdepth 1 -type d ! -path .)" | cut -d'.' -f2)
echo "start tick is $START"
FILE=$CORE_PATH/$2/first.txt
END=$(awk '/Exiting @ tick [0-9]+/ { for(i=1;i<=NF;i++) if($i=="tick") print $(i+1); exit }' "$FILE")
echo "end tick is $END"
Y=$(awk "BEGIN {print($END - $START)/20}")
X=$(awk "BEGIN {print($START + $Y)}")

#MEM=$(expr 4 \* "$1")

echo "create the other checkpoints"
$GEM5/build/X86/gem5.opt $GEM5/configs/deprecated/example/fs.py \
    -n $1 --mem-size=4GB --disk-image=$GEM5/x86-ubuntu \
    --kernel=$GEM5/vmlinux-5.4.49 --cpu-type=X86KvmCPU \
    --restore-with-cpu=X86KvmCPU --script=./run.rcS \
    -r 1 --take-checkpoints $Y,$Y --max-checkpoints 20

echo "Finished !!!!!"