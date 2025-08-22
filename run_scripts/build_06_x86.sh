cd ..
BASE=$(pwd)
mkdir specmnt
mkdir spec06_x86
sudo mount -o loop cpu2006-1.2.iso specmnt
cd specmnt
./install.sh -d ../spec06_x86
cd ..
sudo umount specmnt
rm -r specmnt
cp spec_confs/x86_64_06.cfg spec06_x86/config
cd spec06_x86
. ./shrc   
runspec --config=x86_64_06.cfg --action=build all -I
runspec --config=x86_64_06.cfg --action=run --size=ref all -n 1 -I
cd $BASE/run_scripts
