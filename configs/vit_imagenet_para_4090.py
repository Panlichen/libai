from libai.config import LazyCall
from .common.models.vit.vit_base_patch16_224 import model #from .common.models.vit.vit_large_patch16_224 import model
from .common.models.graph import graph
from .common.train import train
from .common.optim import optim
from .common.data.imagenet import dataloader

from flowvision.data import Mixup
from flowvision.loss.cross_entropy import SoftTargetCrossEntropy


import os
host = os.getenv("HOST")


dataloader.train.dataset[0].root = "/HOME/scw6cab/run/OCCL/ImageNet"
dataloader.test[0].dataset.root = "/HOME/scw6cab/run/OCCL/ImageNet"

# Refine model cfg for vit training on imagenet
model.cfg.num_classes = 1000
model.cfg.loss_func = SoftTargetCrossEntropy()

# Add Mixup Func
dataloader.train.mixup_func = LazyCall(Mixup)(
    mixup_alpha=0.8,
    cutmix_alpha=1.0,
    prob=1.0,
    switch_prob=0.5,
    mode="batch",
    num_classes=model.cfg.num_classes,
)

# Refine optimizer cfg for vit model
optim.lr = 1e-3  # 5e-4 * 1024 (batchsize) / 512
optim.eps = 1e-8
optim.weight_decay = 0.05
optim.params.clip_grad_max_norm = None
optim.params.clip_grad_norm_type = None
optim.params.overrides = {"pos_embed": {"weight_decay": 0.0}, "cls_token": {"weight_decay": 0.0}}

# Refine train cfg for vit model
train.train_micro_batch_size = 128
train.test_micro_batch_size = 128
# train.train_epoch = 300
train.train_epoch = 0
train.train_iter = int(os.getenv("NUM_ITER_ENV"))
train.warmup_ratio = 5 / 300
train.evaluation.enabled = False
# train.evaluation.eval_period = 100
train.log_period = 1

# Scheduler
train.scheduler.warmup_factor = 0.001
train.scheduler.alpha = 0.01
train.scheduler.warmup_method = "linear"

# Set fp16 ON
train.amp.enabled = True

# zero
train.zero_optimization.enabled = False
train.zero_optimization.stage = 1

# Distributed Settings
train.dist.pipeline_num_layers = model.cfg.depth
train.dist.data_parallel_size = 2
train.dist.tensor_parallel_size = 2
train.dist.pipeline_parallel_size = 2
