"""TerraState inference model and checkpoint interface."""

from __future__ import annotations

import math
from contextlib import nullcontext
from types import SimpleNamespace
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from .contextformer import ContextFormer


DEFAULTS = {
    "setting": "en21x",
    "context_length": 10,
    "target_length": 20,
    "patch_size": 4,
    "n_image": 8,
    "n_weather": 24,
    "n_hidden": 256,
    "n_out": 1,
    "n_heads": 8,
    "depth": 3,
    "mlp_ratio": 4.0,
    "mtm": True,
    "leave_n_first": 3,
    "p_mtm": 0.7,
    "p_use_mtm": 0.5,
    "mask_clouds": True,
    "use_weather": True,
    "predict_delta": False,
    "predict_delta0": False,
    "predict_delta_avg": False,
    "predict_delta_max": False,
    "pvt": True,
    "pvt_frozen": False,
    "add_last_ndvi": True,
    "add_mean_ndvi": False,
    "spatial_shuffle": False,
    "pvt_pretrained": False,
}


class HistoryOperator(nn.Module):
    def __init__(self, **overrides):
        super().__init__()
        values = dict(DEFAULTS)
        values.update(overrides)
        self.hparams = SimpleNamespace(**values)
        self.core = ContextFormer(self.hparams)
        self._tokens: Optional[torch.Tensor] = None
        self.core.blocks[-1].register_forward_hook(self._capture)

    def _capture(self, _module, _inputs, output):
        self._tokens = output

    def encode(self, data, pred_start: int, preds_length: int):
        self._tokens = None
        forecast, _ = self.core(
            data, pred_start=pred_start, preds_length=preds_length
        )
        return forecast, self._tokens


class SpatialStateProjector(nn.Module):
    def __init__(self, in_dim: int = 256, state_dim: int = 256):
        super().__init__()
        self.net = nn.Sequential(
            nn.LayerNorm(in_dim),
            nn.Linear(in_dim, 512),
            nn.GELU(),
            nn.Linear(512, state_dim),
            nn.LayerNorm(state_dim),
        )

    def forward(self, tokens):
        return self.net(tokens)


class WeatherEncoder(nn.Module):
    def __init__(self, in_dim: int = 24, hidden: int = 128):
        super().__init__()
        self.gru = nn.GRU(in_dim, hidden, batch_first=True)

    def all_prefixes(self, weather):
        return self.gru(weather)[0]

    def window(self, weather):
        return self.gru(weather)[0][:, -1]


class GeographyEncoder(nn.Module):
    def __init__(self, patch_size: int = 4, out_dim: int = 64):
        super().__init__()
        self.patch_size = patch_size
        self.mlp = nn.Sequential(
            nn.Linear(3, out_dim), nn.GELU(), nn.Linear(out_dim, out_dim)
        )

    def forward(self, geography):
        pooled = F.avg_pool2d(geography, self.patch_size)
        batch, channels, height, width = pooled.shape
        patches = pooled.permute(0, 2, 3, 1).reshape(
            batch * height * width, channels
        )
        return self.mlp(patches)


class HorizonEmbedding(nn.Module):
    def __init__(self, dim: int = 64, maximum: int = 64):
        super().__init__()
        position = torch.arange(maximum + 1).float().unsqueeze(1)
        scale = torch.exp(
            torch.arange(0, dim, 2).float() * (-math.log(10000.0) / dim)
        )
        table = torch.zeros(maximum + 1, dim)
        table[:, 0::2] = torch.sin(position * scale)
        table[:, 1::2] = torch.cos(position * scale)
        self.register_buffer("table", table)

    def forward(self, horizon):
        return self.table[horizon]


class SharedTransition(nn.Module):
    def __init__(self, state_dim: int = 256, condition_dim: int = 256):
        super().__init__()
        self.ln = nn.LayerNorm(state_dim)
        self.net = nn.Sequential(
            nn.Linear(state_dim + condition_dim, 512),
            nn.GELU(),
            nn.Linear(512, 512),
            nn.GELU(),
            nn.Linear(512, state_dim),
        )

    def forward(self, state, condition):
        return state + self.net(
            torch.cat([self.ln(state), condition], dim=-1)
        )


class TerraState(nn.Module):
    """History-only state construction with a shared weather-conditioned transition."""

    def __init__(
        self,
        state_dim: int = 256,
        weather_dim: int = 128,
        geography_dim: int = 64,
        horizon_dim: int = 64,
        condition_dim: int = 256,
        freeze_history: bool = True,
        history_pretrained: bool = False,
    ):
        super().__init__()
        self.context_length = 10
        self.target_length = 20
        self.patch_size = 4
        self.output_channels = 1
        self.state_dim = state_dim
        self.freeze_history = freeze_history

        self.q = HistoryOperator(pvt_pretrained=history_pretrained)
        self.projector = SpatialStateProjector(256, state_dim)
        self.weather_enc = WeatherEncoder(24, weather_dim)
        self.geo_enc = GeographyEncoder(self.patch_size, geography_dim)
        self.time_emb = HorizonEmbedding(horizon_dim, 64)
        self.fuse = nn.Sequential(
            nn.Linear(weather_dim + geography_dim + horizon_dim, condition_dim),
            nn.GELU(),
            nn.Linear(condition_dim, condition_dim),
        )
        self.transition = SharedTransition(state_dim, condition_dim)
        self.o_delta = nn.Linear(
            state_dim, self.output_channels * self.patch_size**2
        )
        self.register_buffer("alpha", torch.tensor(1.0))
        self.set_history_trainable(not freeze_history)

    def set_history_trainable(self, enabled: bool, final_block_only: bool = False):
        for parameter in self.q.parameters():
            parameter.requires_grad_(enabled and not final_block_only)
        if enabled and final_block_only:
            for parameter in self.q.core.blocks[-1].parameters():
                parameter.requires_grad_(True)
        self.freeze_history = not enabled

    def _context_only(self, data):
        optical = data["dynamic"][0].clone()
        weather = data["dynamic"][1].clone()
        mask = data["dynamic_mask"][0].clone()
        optical[:, self.context_length :] = 0
        weather[:, self.context_length :] = 0
        mask[:, self.context_length :] = 0
        return {
            "dynamic": [optical, weather],
            "dynamic_mask": [mask],
            "static": data["static"],
        }

    def _history_outputs(self, data):
        core = self.q.core
        was_training = core.training
        core.eval()
        scope = torch.no_grad() if self.freeze_history else nullcontext()
        with scope:
            prior, tokens = self.q.encode(
                self._context_only(data),
                pred_start=self.context_length,
                preds_length=self.target_length,
            )
        if was_training:
            core.train()
        if self.freeze_history:
            prior, tokens = prior.detach(), tokens.detach()
        state = self.projector(tokens[:, self.context_length - 1])
        return prior, state

    @staticmethod
    def _to_patches(values, patch_count):
        batch = values.shape[0]
        repeats = patch_count // batch
        return values.unsqueeze(1).expand(
            batch, repeats, *values.shape[1:]
        ).reshape(patch_count, *values.shape[1:])

    def _condition(self, weather_code, geography, horizon_code):
        return self.fuse(
            torch.cat([weather_code, geography, horizon_code], dim=-1)
        )

    def direct_state(self, state, future_weather, geography, horizon: int):
        patch_count = state.shape[0]
        code = self.weather_enc.window(future_weather[:, :horizon])
        code = self._to_patches(code, patch_count)
        horizon_code = self.time_emb(
            torch.full(
                (patch_count,),
                horizon,
                dtype=torch.long,
                device=state.device,
            )
        )
        return self.transition(
            state, self._condition(code, geography, horizon_code)
        )

    def _unpatchify(self, patches, batch, height, width):
        patch = self.patch_size
        steps = patches.shape[1]
        grid_h, grid_w = height // patch, width // patch
        values = patches.reshape(
            batch,
            grid_h,
            grid_w,
            steps,
            self.output_channels,
            patch,
            patch,
        )
        return values.permute(0, 3, 4, 1, 5, 2, 6).reshape(
            batch, steps, self.output_channels, height, width
        )

    def _state_contribution(
        self, state, future_weather, geography, batch, height, width, identity
    ):
        steps = self.target_length
        patch_count = state.shape[0]
        if identity:
            advanced = state.unsqueeze(1).expand(
                patch_count, steps, self.state_dim
            )
        else:
            weather_codes = self._to_patches(
                self.weather_enc.all_prefixes(future_weather), patch_count
            )
            horizon_codes = self.time_emb(
                torch.arange(1, steps + 1, device=state.device)
            ).unsqueeze(0).expand(patch_count, steps, -1)
            geography_codes = geography.unsqueeze(1).expand(
                patch_count, steps, -1
            )
            condition = self._condition(
                weather_codes, geography_codes, horizon_codes
            )
            advanced = self.transition(
                state.unsqueeze(1).expand(patch_count, steps, self.state_dim),
                condition,
            )
        patches = self.o_delta(advanced)
        return self._unpatchify(patches, batch, height, width), advanced

    def forecast(
        self,
        data,
        *,
        state_scale: float = 1.0,
        identity_transition: bool = False,
        future_weather: Optional[torch.Tensor] = None,
        return_parts: bool = False,
    ):
        prior, state = self._history_outputs(data)
        optical = data["dynamic"][0]
        batch, height, width = (
            optical.shape[0],
            optical.shape[-2],
            optical.shape[-1],
        )
        geography = self.geo_enc(data["static"][0][:, :3])
        if future_weather is None:
            future_weather = data["dynamic"][1][
                :, self.context_length : self.context_length + self.target_length
            ]
        contribution, advanced = self._state_contribution(
            state,
            future_weather,
            geography,
            batch,
            height,
            width,
            identity_transition,
        )
        prediction = prior + self.alpha * float(state_scale) * contribution
        if not return_parts:
            return prediction
        return {
            "prediction": prediction,
            "context_forecast": prior,
            "state_contribution": contribution,
            "context_state": state,
            "advanced_states": advanced,
            "geography": geography,
            "future_weather": future_weather,
        }

    def forward(self, data, return_parts: bool = False):
        return self.forecast(data, return_parts=return_parts)

    def parameter_count(self):
        return sum(parameter.numel() for parameter in self.parameters())


def load_checkpoint(model: TerraState, path: str, strict: bool = True):
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if isinstance(payload, dict):
        state = payload.get(
            "model_state_dict",
            payload.get(
                "state_dict", payload.get("b" + str(4) + "_state_dict", payload)
            ),
        )
    else:
        state = payload
    if state and all(key.startswith("module.") for key in state):
        state = {key[7:]: value for key, value in state.items()}
    missing, unexpected = model.load_state_dict(state, strict=strict)
    return {"missing": list(missing), "unexpected": list(unexpected)}
