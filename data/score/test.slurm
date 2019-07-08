#!/bin/bash

#SBATCH --job-name=score
#SBATCH --mail-type=FAIL
#SBATCH --account=nn9447k
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --mem-per-cpu=4G
#SBATCH --ntasks-per-node=8

commit="$(git log --pretty=format:\%H -n 1)";
echo "directory: $(pwd)";
echo "git status: $(git status | head -1)";
echo "git commit: ${commit}";
echo;

source /cluster/bin/jobsetup;

module purge;
module use -a /projects/nlpl/software/modulefiles;
module load nlpl-python-candy/201902/3.7 nlpl-numpy/1.16.3/3.7;

/bin/cp ${HOME}/lib/mrp/2019/mtool/data/score/Makefile ./Makefile;
make -j ${SLURM_CPUS_ON_NODE:-4} $(egrep '^[a-z/.]*.json:' Makefile | grep -v all: | sed 's/://');
if [ -d ./../../../etc/ ]; then
  target=../../../../etc/${commit};
  [ -d ${target} ] || mkdir ${target};
  cp -va *.json *.log ${target};
fi
