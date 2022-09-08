# coding=utf-8
# Copyright 2021 The OneFlow Authors. All rights reserved.
# Copyright (c) Facebook, Inc. and its affiliates.
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

"""
Unittests followed
https://github.com/facebookresearch/detectron2/blob/main/tests/config/test_lazy_config.py
"""
import os
import unittest
import tempfile
from itertools import count

from libai.config import LazyConfig, LazyCall
from omegaconf import DictConfig


class TestLazyPythonConfig(unittest.TestCase):
    def setUp(self):
        self.root_filename = os.path.join(os.path.dirname(__file__), "root_cfg.py")

    def test_load(self):
        cfg = LazyConfig.load(self.root_filename)

        self.assertEqual(cfg.dir1a_dict.a, "modified")
        self.assertEqual(cfg.dir1b_dict.a, 1)
        self.assertEqual(cfg.lazyobj.x, "base_a_1")

        cfg.lazyobj.x = "new_x"
        # reload
        cfg = LazyConfig.load(self.root_filename)
        self.assertEqual(cfg.lazyobj.x, "base_a_1")

    def test_save_load(self):
        cfg = LazyConfig.load(self.root_filename)
        with tempfile.TemporaryDirectory(prefix="detectron2") as d:
            fname = os.path.join(d, "test_config.yaml")
            LazyConfig.save(cfg, fname)
            cfg2 = LazyConfig.load(fname)

        self.assertEqual(cfg2.lazyobj._target_, "itertools.count")
        self.assertEqual(cfg.lazyobj._target_, count)
        cfg2.lazyobj.pop("_target_")
        cfg.lazyobj.pop("_target_")
        # the rest are equal
        self.assertEqual(cfg, cfg2)

    def test_failed_save(self):
        cfg = DictConfig({"x": lambda: 3}, flags={"allow_objects": True})
        with tempfile.TemporaryDirectory(prefix="detectron2") as d:
            fname = os.path.join(d, "test_config.yaml")
            LazyConfig.save(cfg, fname)
            self.assertTrue(os.path.exists(fname))
            self.assertTrue(os.path.exists(fname + ".pkl"))

    def test_overrides(self):
        cfg = LazyConfig.load(self.root_filename)
        LazyConfig.apply_overrides(cfg, ["lazyobj.x=123", 'dir1b_dict.a="123"'])
        self.assertEqual(cfg.dir1b_dict.a, "123")
        self.assertEqual(cfg.lazyobj.x, 123)

    def test_invalid_overrides(self):
        cfg = LazyConfig.load(self.root_filename)
        with self.assertRaises(KeyError):
            LazyConfig.apply_overrides(cfg, ["lazyobj.x.xxx=123"])

    def test_to_py(self):
        cfg = LazyConfig.load(self.root_filename)
        cfg.lazyobj.x = {
            "a": 1,
            "b": 2,
            "c": LazyCall(count)(x={"r": "a", "s": 2.4, "t": [1, 2, 3, "z"]}),
        }
        cfg.list = ["a", 1, "b", 3.2]
        py_str = LazyConfig.to_py(cfg)
        expected = """cfg.dir1a_dict.a = "modified"
cfg.dir1a_dict.b = 2
cfg.dir1b_dict.a = 1
cfg.dir1b_dict.b = 2
cfg.lazyobj = itertools.count(
    x={
        "a": 1,
        "b": 2,
        "c": itertools.count(x={"r": "a", "s": 2.4, "t": [1, 2, 3, "z"]}),
    },
    y="base_a_1_from_b",
)
cfg.list = ["a", 1, "b", 3.2]
"""
        self.assertEqual(py_str, expected)
