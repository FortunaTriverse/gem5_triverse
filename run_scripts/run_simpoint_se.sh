cleanup(){
	echo "removing the task"
	pkill -P $$
	echo "remove all"
}
trap cleanup EXIT INT TERM

MAX_JOBS=60
fifo=$(mktemp -u)
mkfifo "$fifo"
exec 5<>"$fifo"
rm -f "$fifo"
for ((i=0;i<MAX_JOBS;i++));do echo;done >&5

cd ../


../../build/RISCV/gem5.opt checkpoint_spec.py simpoint_profile

../../SimPoint.3.2/bin/simpoint -maxK 5 \
     -loadFVFile m5out/simpoint.bb.gz -inputVectorsGzipped \
     -saveSimpoints m5out/simpoints.txt \
     -saveSimpointWeights m5out/weights.txt

../../build/RISCV/gem5.opt checkpoint_spec.py take_simpoint_checkpoints


