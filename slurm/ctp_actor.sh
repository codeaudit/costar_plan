#!/bin/bash -l
#SBATCH --job-name=actor
#SBATCH --time=0-48:0:0
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --mem=8G
#SBATCH --mail-type=end
#SBATCH --mail-user=cpaxton3@jhu.edu

echo "Running $@ on $SLURMD_NODENAME ..."

module load tensorflow/cuda-8.0/r1.3 

export learning_rate=$1
export dropout=$2
export optimizer=$3
export noise_dim=$4
export loss=$5
export model=actor

export train_multi=true
export train_husky=true

echo $0 $1 $2 $3 $4 $5 $6
echo "[STACK] Training policy $model"
export MODELDIR="$HOME/.costar/stack_$learning_rate$optimizer$dropout$noise_dim$loss"
mkdir $MODELDIR
export DATASET="ctp_dec"
$HOME/costar_plan/costar_models/scripts/ctp_model_tool \
  --features multi \
  -e 100 \
  --model secondary \
  --submodel $model \
  --data_file $HOME/work/$DATASET.h5f \
  --lr $learning_rate \
  --dropout_rate $dropout \
  --model_directory $MODELDIR/ \
  --optimizer $optimizer \
  --steps_per_epoch 500 \
  --noise_dim $noise_dim \
  --loss $loss \
  --success_only \
  --batch_size 64

export MODELDIR="$HOME/.costar/husky_$learning_rate$optimizer$dropout$noise_dim$loss"
export DATASET="husky_data"
$HOME/costar_plan/costar_models/scripts/ctp_model_tool \
  --features husky \
  -e 100 \
  --model secondary \
  --data_file $HOME/work/$DATASET.npz \
  --lr $learning_rate \
  --dropout_rate $dropout \
  --model_directory $MODELDIR/ \
  --optimizer $optimizer \
  --steps_per_epoch 500 \
  --noise_dim $noise_dim \
  --loss $loss \
  --success_only \
  --batch_size 64


