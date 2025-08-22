Artefact Evaluation for the Triverse Temporal Prefetcher
==================================================


Hardware pre-requisities
========================
* A native (non-virtualized) x86-64 system preferably with sudo access (to install dependencies and enable KVM if disabled, the latter only if you are generating new checkpoints).

Software pre-requisites
=======================

* Linux operating system (We used Ubuntu 22.04)
* A SPEC CPU2006 iso, if you are creating new checkpoints, placed in the root directory of the repository (We used v1.2).
* For RISC-V experiments, install the RISC-V toolchain (validated with v10).

Installation and Building
========================

You can install this repository as follows:

```
git clone https://github.com/FortunaTriverse/gem5-triverse
```

All scripts from here onwards are assumed to be run from the run_scripts directory, from the root of the repository:

```
cd gem5-triverse
cd run_scripts
```

To install software package dependencies, run

```
./dependencies.sh
```

Then, in the scripts folder, to compile the Triangel gem5 simulator, run

```
./build_opt.sh {ISA}
```

Example for x86-64:

```
./build_opt.sh X86
```

Generating x86-64 Full-System (FS) Checkpoints
========================
Regardless of whether you create equidistant FS checkpoints or SimPoint-based SE checkpoints, SPEC must first be compiled.
Place the SPEC CPU2006 ISO in the repository root and run:

```
cd run_scripts
./build_06_x86.sh
```

Compiled benchmarks will appear in spec06_x86/

* Build the Ubuntu disk image and supporting tools

```
cd util/m5
scons build/x86/out/m5
cd ../../disk-image
./build.sh
```

Upon completion the image is located in disk-image/x86-ubuntu-image/.

Enable KVM for gem5:

```
sudo sh -c 'echo 1 >/proc/sys/kernel/perf_event_paranoid'
```

* Generate checkpoints for a benchmark
e.g., gcc_166:

```
mkdir Checkpoints
cd Checkpoints
mkdir gcc_166
../../build/X86/gem5.opt ../../configs/deprecated/example/fs.py -n 1 --mem-size=4GB --disk-image=../../x86-ubuntu --kernel=../../vmlinux-5.4.49 --cpu-type=X86KvmCPU --script=../../spec-bootcfgs/X86/gcc_166.rcS
```

The terminal will display a port number:

```
system.platform.terminal: Listening for connections on port 3456
```

In a second terminal:

```
telnetl localhost 3456
m5 readfile > /tmp/script;chmod 755 /tmp/script;/tmp/script
```

A first checkpoint is written to m5out/. Extract the tick range:

```
Writing checkpoint
src/sim/simulate.cc:194: info: Entering event queue @ 113102979477600.  Starting simulation...
src/dev/x86/pc.cc:117: warn: Don't know what interrupt to clear for console.
Exiting @ tick 134199564886000 because m5_exit instruction encountered
src/cpu/kvm/base.cc:570: hack: Pretending totalOps is equivalent to totalInsts()
```

Generate the remaining 19 checkpoints:

```
../../build/X86/gem5.opt ../../configs/deprecated/example/fs.py -n 1 --mem-size=4GB --disk-image=../../x86-ubuntu --kernel=../../vmlinux-5.4.49 --cpu-type=X86KvmCPU --script=../../configs/boot/xalan.rcS -r 1 --take-checkpoints=1054829270420,1054829270420 --max-checkpoints=20
```

Post-process all checkpoints:

```
sed -i 's/system\.switch_cpus/system\.cpu/g' m5out/*/m5.cpt
```

Troubleshooting: If a checkpoint records fewer than 5 M instructions executed or simulates for only a fraction of a second, the workload was idle. Our scripts discard such outliers to avoid skewing total execution time. Delete affected checkpoints and continue.
Repeat the procedure for additional benchmarks.
The same flow applies to RISC-V FS checkpoints; however, KVM is unavailable for RISC-V and simulations are extremely slow.

Running x86-64 Full-System Experiments
========================
Prerequisites:
* x86-ubuntu image in the repository root
* Valid checkpoint directories (m5out/cpt*) under Checkpoints/<benchmark>

Restore from a checkpoint and execute 5 M instructions with an out-of-order (O3) CPU:

```
../../build/X86/gem5.opt ../../configs/deprecated/example/fs.py --disk-image=../../x86-ubuntu --kernel=../../vmlinux-5.4.49 -n 1 \
		--mem-size=4GB --cpu-type=X86O3CPU -r 2 --maxinsts=5000000 --pl2sl3cache --standard-switch 50000000 \
		--warmup=50000000 --mem-type=LPDDR5_5500_1x16_BG_BL32 --triverse_bloom 
```

-n: number of simulated cores.
-r: checkpoint index to restore.
--triverse_bloom: enables the Triverse-Bloom prefetcher on the L2 cache.
Replace with --ampm, --dcpt, etc., for alternative prefetchers.

Batch execution

```
cd run_scripts
./run_x86-fs.sh
```

The script evaluates Triverse_SetDueller and Triverse_Bloom. Runtime is 2–3 h on a modern server. Progress is logged to stdout.txt.
Results are aggregated in ../test_results/<prefetcher>/.
The script launches jobs in parallel; reduce MAX_JOBS in run_x86-fs.sh if your machine becomes unresponsive:

```
MAX_JOBS=60
fifo=$(mktemp -u)
mkfifo "$fifo"
exec 5<>"$fifo"
rm -f "$fifo"
for ((i=0;i<MAX_JOBS;i++));do echo;done >&5
```

To evaluate additional prefetchers or benchmarks, edit create_run.py:

```
prefetchers = ['ampm','dcpt','isb','sbooe','spp','slim','stride','tagged']
prefetchers += ['xsberti','xsbop','xsopt','xsstream']
prefetchers += ['triangel','triage','triverse_bloom','triverse']
```

Generate and run:

```
python3 create_run.py
./run_1.sh
```

Post-process results:

```
cd run_scripts
cp run_1.sh ../test_results/
cd ../test_results
python3 score.py
```

Annotated results appear in result/

Generating RISC-V SE SimPoints
===============================
Full-system simulation for RISC-V is prohibitively slow; we therefore use SE mode with SimPoints.
1. Build the RISC-V SPEC2006 binaries (may report “format error” on non-RISC-V hosts—ignore):

```
cd run_scripts
./build_06_riscv.sh
```

2. Prepare the simulation environment:

```
python3 create_riscv_simpoint.py
```

The directory riscv_simpoints/<benchmark>/ is created for each workload.

3. Install SimPoint 3.2 into the gem5 root (see official instructions:
https://cseweb.ucsd.edu/~calder/simpoint/simpoint-3-0.htm）

4. Generate SimPoints for each benchmark (example: gcc_166):

```
../../build/RISCV/gem5.opt checkpoint_spec.py simpoint_profile --benchmark=gcc_166

../../SimPoint.3.2/bin/simpoint -maxK 20 \
     -loadFVFile m5out/simpoint.bb.gz -inputVectorsGzipped \
     -saveSimpoints m5out/simpoints.txt \
     -saveSimpointWeights m5out/weights.txt

../../build/RISCV/gem5.opt checkpoint_spec.py take_simpoint_checkpoints --benchmark=gcc_166

```

5. Run the simulations:

```
cd run_scripts
./run_riscv_se_simpoints.sh
```



