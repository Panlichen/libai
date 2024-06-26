# coding=utf-8
# Copyright 2021 The OneFlow Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import oneflow as flow
from oneflow import nn

from libai.utils import distributed as dist


class LayerNorm(nn.Module):
    """Applies Layer Normalization over a mini-batch of inputs in 1D parallelism.

    Args:
        normalized_shape: input shape from an expected input of size.
        eps: a value added to the denominator for numerical stability. Defaults to 1e-5.
            elementwise_affine: a boolean value that when set to ``True``, this module
            has learnable per-element affine parameters initialized to ones (for weights)
            and zeros (for biases). Default: ``True``.
        elementwise_affine: a boolean value that when set to ``True``, this module
            has learnable per-element affine parameters initialized to ones (for weights)
            and zeros (for biases). Default: ``True``.
        bias: If set to ``False``, the layer will not learn an additive bias. Defaults to ``True``.
        layer_idx: a layer_idx sign which determines the placement. It will be used in pipeline
            parallelism. Defaults to 0.
    """

    def __init__(
        self, normalized_shape, eps=1e-5, elementwise_affine=True, bias=True, *, layer_idx=0
    ):
        super().__init__()
        if isinstance(normalized_shape, int):
            normalized_shape = (normalized_shape,)
        self.normalized_shape = tuple(normalized_shape)
        self.eps = eps
        self.elementwise_affine = elementwise_affine
        self.layer_idx = layer_idx

        if elementwise_affine:
            self.weight = nn.Parameter(
                flow.ones(
                    normalized_shape,
                    dtype=flow.float32,
                    placement=dist.get_layer_placement(layer_idx),
                    sbp=dist.get_nd_sbp([flow.sbp.broadcast, flow.sbp.broadcast]),
                )
            )
            self.bias = nn.Parameter(
                flow.zeros(
                    normalized_shape,
                    dtype=flow.float32,
                    placement=dist.get_layer_placement(layer_idx),
                    sbp=dist.get_nd_sbp([flow.sbp.broadcast, flow.sbp.broadcast]),
                ),
                requires_grad=bias,
            )
        else:
            self.weight = None
            self.bias = None

    def forward(self, x):
        assert x.shape[-len(self.normalized_shape) :] == self.normalized_shape
        begin_norm_axis = x.ndim - len(self.normalized_shape)
        begin_params_axis = x.ndim - len(self.normalized_shape)
        if self.elementwise_affine:
            y = flow._C.layer_norm_affine(
                x,
                self.weight,
                self.bias,
                begin_norm_axis=begin_norm_axis,
                begin_params_axis=begin_params_axis,
                epsilon=self.eps,
            )
        else:
            y = flow._C.layer_norm(
                x,
                begin_norm_axis=begin_norm_axis,
                begin_params_axis=begin_params_axis,
                epsilon=self.eps,
            )
        return y

    def extra_repr(self) -> str:
        return "{normalized_shape}, eps={eps}, elementwise_affine={elementwise_affine}".format(
            **self.__dict__
        )


class RMSLayerNorm(nn.Module):
    """T5 uses a layer_norm which only scales and doesn't shift, which is also known as
    Root Mean Square Layer Normalization thus varience is calculated w/o mean and
    there is no bias. More details see: https://arxiv.org/abs/1910.07467.

    Args:
        normalized_shape: input shape from an expected input of size.
        eps: a value added to the denominator for numerical stability. Defaults to 1e-5.
            elementwise_affine: a boolean value that when set to ``True``, this module
            has learnable per-element affine parameters initialized to ones (for weights)
            and zeros (for biases). Default: ``True``.
        layer_idx: a layer_idx sign which determines the placement. It will be used in pipeline
            parallelism. Defaults to 0.
    """

    def __init__(self, normalized_shape, eps=1e-6, layer_idx=0):
        super().__init__()
        self.layer_idx = layer_idx
        self.weight = flow.nn.Parameter(
            flow.ones(
                normalized_shape,
                dtype=flow.float32,
                placement=dist.get_layer_placement(layer_idx),
                sbp=dist.get_nd_sbp([flow.sbp.broadcast, flow.sbp.broadcast]),
            )
        )
        self.l2norm_epsilon = eps

    def forward(self, hidden_states):
        return flow._C.rms_layer_norm(hidden_states, self.weight, self.l2norm_epsilon)
