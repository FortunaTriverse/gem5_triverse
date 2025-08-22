  
cd ..
BASE=$(pwd)
mkdir spec06_riscv
mkdir spec06mnt_riscv
sudo mount cpu2006-1.2.iso spec06mnt_riscv
cd spec06mnt_riscv
./install.sh -d ../spec06_riscv
cd ..
sudo umount spec06mnt_riscv
rm -r spec06mnt_riscv
cp spec_confs/riscv_06.cfg spec06_riscv/config
cd spec06_riscv
. ./shrc
runspec --config=riscv_06.cfg --size=ref --noreportable --tune=base --iterations=1 all




