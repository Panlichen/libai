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

from enum import Enum
from typing import Optional

import oneflow as flow
from oneflow import nn


class Activation(str, Enum):
    SquaredReLU = "squared_relu"
    GeLU = "gelu"
    GeLUTanh = "gelu_tanh"
    LeakyReLU = "leaky_relu"
    ReLU = "relu"
    Tanh = "tanh"
    QuickGELU = "quick_gelu"


# For unit testing / parity comparisons, probably not the fastest way
class SquaredReLU(nn.Module):
    def __init__(self) -> None:
        super().__init__()

    def forward(self, x: flow.Tensor) -> flow.Tensor:
        x_ = flow._C.relu(x)
        return x_ * x_


class Passthrough(nn.Module):
    def __init__(self) -> None:
        super().__init__()

    def forward(self, x: flow.Tensor) -> flow.Tensor:
        return x


class GeLUTanh(nn.Module):
    def __init__(self) -> None:
        super().__init__()

    def forward(self, x: flow.Tensor) -> flow.Tensor:
        """When the approximate argument is 'tanh', Gelu is estimated with:
        0.5 * x * (1.0 + flow.tanh(math.sqrt(2.0 / math.pi) * (x + 0.044715 * flow.pow(x, 3.0))))
        """
        return flow.nn.functional.gelu(x, approximate="tanh")


class QuickGELU(nn.Module):
    def __init__(self) -> None:
        super().__init__()

    def forward(self, x: flow.Tensor) -> flow.Tensor:
        return x * flow.sigmoid(1.702 * x)


def build_activation(activation: Optional[Activation]):
    """
    Fetching activation layers by name, e.g.,
    ``build_activation("gelu")`` returns ``nn.GELU()`` module.
    """
    if not activation:
        return Passthrough()

    return {
        Activation.ReLU: nn.ReLU,
        Activation.GeLU: nn.GELU,
        Activation.GeLUTanh: GeLUTanh,
        Activation.LeakyReLU: nn.LeakyReLU,
        Activation.SquaredReLU: SquaredReLU,
        Activation.Tanh: nn.Tanh,
        Activation.QuickGELU: QuickGELU,
    }[activation]()
