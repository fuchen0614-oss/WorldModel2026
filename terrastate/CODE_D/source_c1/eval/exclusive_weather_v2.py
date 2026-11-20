"""CandidateC/Exclusive prediction adapters, no scoring or eligibility changes."""
import torch

def replace_weather(model, recipient_condition, weather):
    model._validate_future_condition(recipient_condition)
    if weather.ndim != 3 or weather.shape[-1] != model.driver_dim or weather.shape[:2] != recipient_condition.shape[:2]:
        raise ValueError("replacement must be raw weather matching recipient [B,T,driver_dim]")
    out = torch.cat((weather.to(recipient_condition), recipient_condition[..., -2:]), dim=-1)
    model._validate_future_condition(out)
    return out

def mean_weather(model, recipient_condition):
    return replace_weather(model, recipient_condition, torch.zeros_like(recipient_condition[..., :model.driver_dim]))

def donor_weather(model, recipient_condition, donor_raw_weather):
    # Donor dates are never transplanted to the receiving forecast.
    return replace_weather(model, recipient_condition, donor_raw_weather)

def predict_with_weather(model, data, raw_weather=None, *, mean=False):
    prior, z = model._prior_state(data)
    geo, condition = model._geo_weather(data)
    if mean and raw_weather is not None:
        raise ValueError("choose mean OR donor weather")
    if mean:
        condition = mean_weather(model, condition)
    elif raw_weather is not None:
        condition = donor_weather(model, condition, raw_weather)
    image = data['dynamic'][0]
    residual = model._direct_residual(z, condition, geo, image.shape[0], image.shape[-2], image.shape[-1])
    return prior + model.alpha * residual
