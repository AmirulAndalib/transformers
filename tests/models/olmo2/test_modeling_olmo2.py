# Copyright 2024 The HuggingFace Inc. team. All rights reserved.
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
"""Testing suite for the PyTorch OLMo2 model."""

import unittest

from packaging import version
from parameterized import parameterized

from transformers import Olmo2Config, is_torch_available, set_seed
from transformers.generation.configuration_utils import GenerationConfig
from transformers.models.auto.tokenization_auto import AutoTokenizer
from transformers.testing_utils import (
    Expectations,
    cleanup,
    require_tokenizers,
    require_torch,
    slow,
    torch_device,
)

from ...generation.test_utils import GenerationTesterMixin
from ...test_configuration_common import ConfigTester
from ...test_modeling_common import ModelTesterMixin, ids_tensor
from ...test_pipeline_mixin import PipelineTesterMixin


if is_torch_available():
    import torch

    from transformers import (
        Olmo2ForCausalLM,
        Olmo2Model,
    )


class Olmo2ModelTester:
    def __init__(
        self,
        parent,
        batch_size=13,
        seq_length=7,
        is_training=True,
        use_input_mask=True,
        use_token_type_ids=False,
        use_labels=True,
        vocab_size=99,
        hidden_size=32,
        num_hidden_layers=2,
        num_attention_heads=4,
        intermediate_size=37,
        hidden_act="silu",
        hidden_dropout_prob=0.1,
        attention_probs_dropout_prob=0.1,
        max_position_embeddings=512,
        type_vocab_size=16,
        type_sequence_label_size=2,
        initializer_range=0.02,
        num_labels=3,
        num_choices=4,
        pad_token_id=0,
        scope=None,
    ):
        self.parent = parent
        self.batch_size = batch_size
        self.seq_length = seq_length
        self.is_training = is_training
        self.use_input_mask = use_input_mask
        self.use_token_type_ids = use_token_type_ids
        self.use_labels = use_labels
        self.vocab_size = vocab_size
        self.hidden_size = hidden_size
        self.num_hidden_layers = num_hidden_layers
        self.num_attention_heads = num_attention_heads
        self.intermediate_size = intermediate_size
        self.hidden_act = hidden_act
        self.hidden_dropout_prob = hidden_dropout_prob
        self.attention_probs_dropout_prob = attention_probs_dropout_prob
        self.max_position_embeddings = max_position_embeddings
        self.type_vocab_size = type_vocab_size
        self.type_sequence_label_size = type_sequence_label_size
        self.initializer_range = initializer_range
        self.num_labels = num_labels
        self.num_choices = num_choices
        self.pad_token_id = pad_token_id
        self.scope = scope

    def prepare_config_and_inputs(self):
        input_ids = ids_tensor([self.batch_size, self.seq_length], self.vocab_size)

        input_mask = None
        if self.use_input_mask:
            input_mask = torch.tril(torch.ones_like(input_ids).to(torch_device))

        token_type_ids = None
        if self.use_token_type_ids:
            token_type_ids = ids_tensor([self.batch_size, self.seq_length], self.type_vocab_size)

        sequence_labels = None
        token_labels = None
        choice_labels = None
        if self.use_labels:
            sequence_labels = ids_tensor([self.batch_size], self.type_sequence_label_size)
            token_labels = ids_tensor([self.batch_size, self.seq_length], self.num_labels)
            choice_labels = ids_tensor([self.batch_size], self.num_choices)

        config = self.get_config()

        return config, input_ids, token_type_ids, input_mask, sequence_labels, token_labels, choice_labels

    def get_config(self):
        return Olmo2Config(
            vocab_size=self.vocab_size,
            hidden_size=self.hidden_size,
            num_hidden_layers=self.num_hidden_layers,
            num_attention_heads=self.num_attention_heads,
            intermediate_size=self.intermediate_size,
            hidden_act=self.hidden_act,
            hidden_dropout_prob=self.hidden_dropout_prob,
            attention_probs_dropout_prob=self.attention_probs_dropout_prob,
            max_position_embeddings=self.max_position_embeddings,
            type_vocab_size=self.type_vocab_size,
            is_decoder=False,
            initializer_range=self.initializer_range,
            pad_token_id=self.pad_token_id,
        )

    def create_and_check_model(
        self, config, input_ids, token_type_ids, input_mask, sequence_labels, token_labels, choice_labels
    ):
        model = Olmo2Model(config=config)
        model.to(torch_device)
        model.eval()
        result = model(input_ids, attention_mask=input_mask)
        result = model(input_ids)
        self.parent.assertEqual(result.last_hidden_state.shape, (self.batch_size, self.seq_length, self.hidden_size))

    def prepare_config_and_inputs_for_common(self):
        config_and_inputs = self.prepare_config_and_inputs()
        (
            config,
            input_ids,
            token_type_ids,
            input_mask,
            sequence_labels,
            token_labels,
            choice_labels,
        ) = config_and_inputs
        inputs_dict = {"input_ids": input_ids, "attention_mask": input_mask}
        return config, inputs_dict


@require_torch
class Olmo2ModelTest(ModelTesterMixin, GenerationTesterMixin, PipelineTesterMixin, unittest.TestCase):
    all_model_classes = (Olmo2Model, Olmo2ForCausalLM) if is_torch_available() else ()
    pipeline_model_mapping = (
        {
            "feature-extraction": Olmo2Model,
            "text-generation": Olmo2ForCausalLM,
        }
        if is_torch_available()
        else {}
    )
    test_pruning = False
    fx_compatible = False

    # Need to use `0.8` instead of `0.9` for `test_cpu_offload`
    # This is because we are hitting edge cases with the causal_mask buffer
    model_split_percents = [0.5, 0.7, 0.8]

    def setUp(self):
        self.model_tester = Olmo2ModelTester(self)
        self.config_tester = ConfigTester(self, config_class=Olmo2Config, hidden_size=37)

    def test_config(self):
        self.config_tester.run_common_tests()

    def test_model(self):
        config_and_inputs = self.model_tester.prepare_config_and_inputs()
        self.model_tester.create_and_check_model(*config_and_inputs)

    @unittest.skip(reason="OLMo2 does not support head pruning.")
    def test_headmasking(self):
        pass

    def test_model_various_embeddings(self):
        config_and_inputs = self.model_tester.prepare_config_and_inputs()
        for type in ["absolute", "relative_key", "relative_key_query"]:
            config_and_inputs[0].position_embedding_type = type
            self.model_tester.create_and_check_model(*config_and_inputs)

    @parameterized.expand([("linear",), ("dynamic",)])
    def test_model_rope_scaling(self, scaling_type):
        config, _ = self.model_tester.prepare_config_and_inputs_for_common()
        short_input = ids_tensor([1, 10], config.vocab_size)
        long_input = ids_tensor([1, int(config.max_position_embeddings * 1.5)], config.vocab_size)

        set_seed(42)  # Fixed seed at init time so the two models get the same random weights
        original_model = Olmo2Model(config)
        original_model.to(torch_device)
        original_model.eval()
        original_short_output = original_model(short_input).last_hidden_state
        original_long_output = original_model(long_input).last_hidden_state

        set_seed(42)  # Fixed seed at init time so the two models get the same random weights
        config.rope_scaling = {"type": scaling_type, "factor": 10.0}
        scaled_model = Olmo2Model(config)
        scaled_model.to(torch_device)
        scaled_model.eval()
        scaled_short_output = scaled_model(short_input).last_hidden_state
        scaled_long_output = scaled_model(long_input).last_hidden_state

        # Dynamic scaling does not change the RoPE embeddings until it receives an input longer than the original
        # maximum sequence length, so the outputs for the short input should match.
        if scaling_type == "dynamic":
            torch.testing.assert_close(original_short_output, scaled_short_output, rtol=1e-5, atol=1e-5)
        else:
            self.assertFalse(torch.allclose(original_short_output, scaled_short_output, atol=1e-5))

        # The output should be different for long inputs
        self.assertFalse(torch.allclose(original_long_output, scaled_long_output, atol=1e-5))


@require_torch
class Olmo2IntegrationTest(unittest.TestCase):
    def setUp(self):
        cleanup(torch_device, gc_collect=True)

    def tearDown(self):
        cleanup(torch_device, gc_collect=True)

    @slow
    def test_model_1b_logits_bfloat16(self):
        input_ids = [[1, 306, 4658, 278, 6593, 310, 2834, 338]]
        model = Olmo2ForCausalLM.from_pretrained("allenai/OLMo-2-0425-1B").to(torch_device, torch.bfloat16)
        out = model(torch.tensor(input_ids, device=torch_device)).logits.float()
        # Expected mean on dim = -1
        expectations = Expectations(
            {
                ("cuda", 8): [[-5.6700, -6.5557, -3.1545, -2.7418, -5.5887, -4.5179, -4.9077, -4.6530]],
            }
        )
        EXPECTED_MEAN = torch.tensor(expectations.get_expectation(), device=torch_device)
        torch.testing.assert_close(out.mean(-1), EXPECTED_MEAN, rtol=1e-2, atol=1e-2)

        # slicing logits[0, 0, 0:30]
        expectations = Expectations(
            {
                ("cuda", 8): [2.65625, -5.25, -4.9375, -4.53125, -6.5, -3.828125, -4.15625, -4.1875, -7.0625, -4.71875, -3.609375, -3.09375, -4.59375, -2.640625, -5.25, 0.39453125, 1.3828125, 1.2265625, 1.0078125, 0.57421875, 0.330078125, -0.287109375, -0.3671875, 0.1943359375, -0.0732421875, -6.6875, -4.75, -6.4375, -0.625, -2.625],
            }
        )  # fmt: skip
        EXPECTED_SLICE = torch.tensor(expectations.get_expectation(), device=torch_device)
        torch.testing.assert_close(out[0, 0, :30], EXPECTED_SLICE, rtol=1e-2, atol=1e-2)

    @slow
    def test_model_7b_logits(self):
        input_ids = [[1, 306, 4658, 278, 6593, 310, 2834, 338]]
        model = Olmo2ForCausalLM.from_pretrained("shanearora/OLMo2-7B-1124-hf").to(torch_device, dtype=torch.bfloat16)
        out = model(torch.tensor(input_ids, device=torch_device)).logits.float()
        # Expected mean on dim = -1
        expectations = Expectations(
            {
                ("cuda", 8): [[-13.0518, -13.8897, -11.7999, -11.3222, -12.3441, -12.3884, -15.4874, -12.7365]],
            }
        )
        EXPECTED_MEAN = torch.tensor(expectations.get_expectation(), device=torch_device)
        torch.testing.assert_close(out.mean(-1), EXPECTED_MEAN, rtol=1e-2, atol=1e-2)
        # slicing logits[0, 0, 0:30]
        expectations = Expectations(
            {
                ("cuda", 8): [-5.5, -14.4375, -13.8125, -14.875, -14.125, -13.4375, -13.8125, -12.25, -9.5, -12.9375, -11.6875, -6.09375, -12.1875, -6.5, -11.3125, -7.34375, -6.5625, -6.71875, -7.375, -7.96875, -8.0625, -8.1875, -8.75, -8.75, -8.875, -9.9375, -8.1875, -12.875, -7.84375, -11.625],
            }
        )  # fmt: skip
        EXPECTED_SLICE = torch.tensor(expectations.get_expectation(), device=torch_device)
        torch.testing.assert_close(out[0, 0, :30], EXPECTED_SLICE, rtol=1e-2, atol=1e-2)

    @slow
    def test_model_7b_greedy_generation(self):
        EXPECTED_TEXT_COMPLETION = """Simply put, the theory of relativity states that 1) the speed of light is constant, 2) the speed of light is the fastest speed possible, and 3) the speed of light is the same for all observers, regardless of their relative motion. The theory of relativity is based on the idea that the speed of light is constant. This means that"""
        prompt = "Simply put, the theory of relativity states that "
        tokenizer = AutoTokenizer.from_pretrained("shanearora/OLMo2-7B-1124-hf", device_map="auto")
        model = Olmo2ForCausalLM.from_pretrained("shanearora/OLMo2-7B-1124-hf", device_map="auto")
        input_ids = tokenizer.encode(prompt, return_tensors="pt").to(model.device)

        # greedy generation outputs
        generated_ids = model.generate(input_ids, max_new_tokens=64, top_p=None, temperature=1, do_sample=False)
        text = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
        self.assertEqual(EXPECTED_TEXT_COMPLETION, text)

    @require_tokenizers
    def test_simple_encode_decode(self):
        rust_tokenizer = AutoTokenizer.from_pretrained("shanearora/OLMo2-7B-1124-hf")

        self.assertEqual(rust_tokenizer.encode("This is a test"), [2028, 374, 264, 1296])
        self.assertEqual(rust_tokenizer.decode([2028, 374, 264, 1296], skip_special_tokens=True), "This is a test")

        # bytefallback showcase
        self.assertEqual(rust_tokenizer.encode("生活的真谛是"), [21990, 76706, 9554, 89151, 39013, 249, 21043])  # fmt: skip
        self.assertEqual(
            rust_tokenizer.decode([21990, 76706, 9554, 89151, 39013, 249, 21043], skip_special_tokens=True),
            "生活的真谛是",
        )

        # Inner spaces showcase
        self.assertEqual(rust_tokenizer.encode("Hi  Hello"), [13347, 220, 22691])
        self.assertEqual(rust_tokenizer.decode([13347, 220, 22691], skip_special_tokens=True), "Hi  Hello")

        self.assertEqual(rust_tokenizer.encode("Hi   Hello"), [13347, 256, 22691])
        self.assertEqual(rust_tokenizer.decode([13347, 256, 22691], skip_special_tokens=True), "Hi   Hello")

        self.assertEqual(rust_tokenizer.encode(""), [])

        self.assertEqual(rust_tokenizer.encode(" "), [220])

        self.assertEqual(rust_tokenizer.encode("  "), [256])

        self.assertEqual(rust_tokenizer.encode(" Hello"), [22691])

    @slow
    def test_export_static_cache(self):
        if version.parse(torch.__version__) < version.parse("2.4.0"):
            self.skipTest(reason="This test requires torch >= 2.4 to run.")

        from transformers.integrations.executorch import (
            TorchExportableModuleWithStaticCache,
            convert_and_export_with_cache,
        )

        olmo2_model = "shanearora/OLMo2-7B-1124-hf"

        tokenizer = AutoTokenizer.from_pretrained(olmo2_model, pad_token="</s>", padding_side="right")
        EXPECTED_TEXT_COMPLETION = [
            "Simply put, the theory of relativity states that 1) the speed of light is constant, 2) the speed of light",
        ]
        max_generation_length = tokenizer(EXPECTED_TEXT_COMPLETION, return_tensors="pt", padding=True)[
            "input_ids"
        ].shape[-1]

        # Load model
        device = "cpu"  # TODO (joao / export experts): should be on `torch_device`, but causes GPU OOM
        dtype = torch.bfloat16
        cache_implementation = "static"
        attn_implementation = "sdpa"
        batch_size = 1
        generation_config = GenerationConfig(
            use_cache=True,
            cache_implementation=cache_implementation,
            max_length=max_generation_length,
            cache_config={
                "batch_size": batch_size,
                "max_cache_len": max_generation_length,
            },
        )
        model = Olmo2ForCausalLM.from_pretrained(
            olmo2_model,
            device_map=device,
            torch_dtype=dtype,
            attn_implementation=attn_implementation,
            generation_config=generation_config,
        )

        prompts = ["Simply put, the theory of relativity states that "]
        prompt_tokens = tokenizer(prompts, return_tensors="pt", padding=True).to(model.device)
        prompt_token_ids = prompt_tokens["input_ids"]
        max_new_tokens = max_generation_length - prompt_token_ids.shape[-1]

        # Static Cache + eager
        eager_generated_ids = model.generate(
            **prompt_tokens, max_new_tokens=max_new_tokens, do_sample=False, cache_implementation=cache_implementation
        )
        eager_generated_text = tokenizer.batch_decode(eager_generated_ids, skip_special_tokens=True)
        self.assertEqual(EXPECTED_TEXT_COMPLETION, eager_generated_text)

        # Static Cache + export
        exported_program = convert_and_export_with_cache(model)
        ep_generated_ids = TorchExportableModuleWithStaticCache.generate(
            exported_program=exported_program, prompt_token_ids=prompt_token_ids, max_new_tokens=max_new_tokens
        )
        ep_generated_text = tokenizer.batch_decode(ep_generated_ids, skip_special_tokens=True)
        self.assertEqual(EXPECTED_TEXT_COMPLETION, ep_generated_text)
