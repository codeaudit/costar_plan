#!/usr/bin/env bash
rosrun costar_models ctp_model_tool \
  --model pretrain_image_gan \
  --data_file suturing_data.h5f \
  --lr 0.001 \
  --dropout_rate 0.2 \
  --features dvrk \
  --batch_size 32 $1
