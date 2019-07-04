#!/bin/bash

#SBATCH --job-name=score
#SBATCH --mail-type=FAIL
#SBATCH --account=nn9447k
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --mem-per-cpu=4G
#SBATCH --ntasks-per-node=8

echo "directory: $(pwd)";
echo "git status: $(git status | head -1)";
echo "git commit: $(git log --pretty=format:\%H -n 1)";
echo;

source /cluster/bin/jobsetup;

module purge;
module use -a /projects/nlpl/software/modulefiles;
module load nlpl-numpy;

/bin/cp ${HOME}/lib/mrp/2019/mtool/data/score/Makefile ./Makefile;
make -j ${SLURM_CPUS_ON_NODE:-4} $(egrep '^[a-z/.]*.json:' Makefile | grep -v all: | sed 's/://');
