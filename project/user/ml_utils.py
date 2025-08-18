import os
import logging
import pickle
from functools import lru_cache

import joblib
import numpy as np

from django.conf import settings

logger = logging.getLogger(__name__)

# Optional: scipy for sparse hstack if using multiple vectorizers
try:
    from scipy.sparse import hstack, csr_matrix
except Exception:
    hstack = None
    csr_matrix = None


# Config: where to place your model files (default: <BASE_DIR>/ml_models)
ML_MODELS_DIR = getattr(settings, "ML_MODELS_DIR", os.path.join(settings.BASE_DIR, "ml_models"))

MODEL_FILENAME = getattr(settings, "ML_MODEL_FILENAME", "ridge_model.pkl")
VECTORIZER_FILENAME = getattr(settings, "VECTORIZER_FILENAME", "tfidf_vectorizers.pkl")
MODEL_RESULTS_FILENAME = getattr(settings, "MODEL_RESULTS_FILENAME", "model_results.pkl")


class MLModelError(Exception):
    pass


def _safe_load(path):
    """Try joblib.load then pickle.load, raise FileNotFoundError/MLModelError accordingly."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Model file not found: {path}")

    # First try joblib (works for sklearn pipelines)
    try:
        return joblib.load(path)
    except Exception:
        pass

    # Fallback to pickle
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        raise MLModelError(f"Failed to load {path}: {e}")


@lru_cache(maxsize=1)
def load_model():
    path = os.path.join(ML_MODELS_DIR, MODEL_FILENAME)
    try:
        model = _safe_load(path)
        logger.info("Loaded model from %s", path)
        return model
    except FileNotFoundError as e:
        logger.error(e)
        raise
    except MLModelError as e:
        logger.error(e)
        raise


@lru_cache(maxsize=1)
def load_vectorizer():
    path = os.path.join(ML_MODELS_DIR, VECTORIZER_FILENAME)
    try:
        vec = _safe_load(path)
        logger.info("Loaded vectorizer from %s", path)
        return vec
    except FileNotFoundError as e:
        logger.error(e)
        raise
    except MLModelError as e:
        logger.error(e)
        raise


@lru_cache(maxsize=1)
def load_model_results():
    """Optional: load model_results if you have RMSE or other metrics saved."""
    path = os.path.join(ML_MODELS_DIR, MODEL_RESULTS_FILENAME)
    if not os.path.exists(path):
        return None
    try:
        res = _safe_load(path)
        logger.info("Loaded model_results from %s", path)
        return res
    except Exception as e:
        logger.warning("Could not load model_results: %s", e)
        return None


def _text_from_inputs(title: str, abstract: str, keywords: str) -> str:
    parts = []
    if title:
        parts.append(title.strip())
    if abstract:
        parts.append(abstract.strip())
    if keywords:
        parts.append(keywords.strip())
    return " ".join(parts)


def _transform_text_to_features(vectorizer, title, abstract, keywords):
    """
    Support two vectorizer shapes:
    - single sklearn vectorizer/pipeline: call .transform([text])
    - dict of vectorizers: {'title': vec_t, 'abstract': vec_a, 'keywords': vec_k}
      -> transform separately and hstack (requires scipy)
    """
    # Case 1: single vectorizer/pipeline
    if not isinstance(vectorizer, dict):
        text = _text_from_inputs(title, abstract, keywords)
        try:
            X = vectorizer.transform([text])
        except Exception as e:
            logger.error("Vectorizer transform failed: %s", e)
            raise MLModelError(f"Vectorizer transform failed: {e}")
        return X

    # Case 2: dict of vectorizers
    # Expect keys like 'title', 'abstract', 'keywords' or whatever was used during training
    features = []
    for key in sorted(vectorizer.keys()):  # deterministic order
        vec = vectorizer[key]
        raw = ""
        if key.lower().startswith("title"):
            raw = title or ""
        elif key.lower().startswith("abstract"):
            raw = abstract or ""
        elif key.lower().startswith("keyword") or key.lower().startswith("key"):
            raw = keywords or ""
        else:
            # fallback: combined
            raw = _text_from_inputs(title, abstract, keywords)

        try:
            part = vec.transform([raw])
        except Exception as e:
            logger.error("Transform failed for sub-vectorizer '%s': %s", key, e)
            raise MLModelError(f"Transform failed for '{key}': {e}")

        features.append(part)

    # ensure scipy available
    if hstack is None:
        raise MLModelError("scipy.sparse.hstack not available; install scipy to combine vectorizers")

    try:
        X = hstack(features)
        return X
    except Exception as e:
        logger.error("Failed to hstack vectorized features: %s", e)
        raise MLModelError(f"Failed to combine vectorized features: {e}")


def predict_from_text(title: str, abstract: str, keywords: str):
    """
    Returns dict: {
      'raw_prediction': float,
      'predicted': int,
      'ci_low': float|None,
      'ci_high': float|None
    }
    """
    # Basic validation
    if not (title or abstract):
        raise ValueError("At least one of title or abstract must be provided for prediction")

    model = load_model()
    vectorizer = load_vectorizer()
    model_results = load_model_results()

    # Transform text to feature vector
    X = _transform_text_to_features(vectorizer, title, abstract, keywords)

    # Check for feature mismatch and pad or truncate if necessary.
    # This handles cases where the model was trained with additional numerical features
    # that are not generated from the text inputs.
    try:
        expected_features = model.n_features_in_
        current_features = X.shape[1]

        if current_features != expected_features:
            logger.warning(
                "Feature mismatch detected. Input has %d features, model expects %d. "
                "Attempting to fix shape. This may affect prediction accuracy.",
                current_features,
                expected_features
            )
            if current_features < expected_features:
                # Pad with zeros if features are missing
                if hstack is None or csr_matrix is None:
                    raise MLModelError("scipy is required to fix feature mismatch but is not installed.")
                
                missing_features_count = expected_features - current_features
                padding = csr_matrix((X.shape[0], missing_features_count), dtype=X.dtype)
                X = hstack([X, padding])
                logger.info("Padded input with %d zero-features.", missing_features_count)
            else:
                # Truncate if there are too many features
                X = X[:, :expected_features]
                logger.info("Truncated input features to %d.", expected_features)

    except AttributeError:
        # This handles older sklearn models that might not have `n_features_in_`
        logger.warning("Could not verify feature count; model does not have 'n_features_in_' attribute.")

    # Predict (ensure we return a scalar)
    try:
        raw_pred = model.predict(X)
    except Exception as e:
        logger.exception("Prediction failed: %s", e)
        raise MLModelError(f"Prediction failed: {e}")

    # raw_pred might be array-like; get first element
    try:
        pred_val = float(raw_pred[0])
    except Exception:
        try:
            pred_val = float(raw_pred)
        except Exception as e:
            logger.error("Unexpected prediction output: %s", e)
            raise MLModelError("Unexpected model prediction output")

    # Post-process: ensure non-negative integer for citation count
    predicted_int = max(0, int(round(pred_val)))

    # Compute simple CI if rmse present in model_results
    ci_low = None
    ci_high = None
    if model_results:
        # Look for commonly used keys
        rmse = None
        for key in ("rmse", "RMSE", "std", "residual_std", "residuals_std"):
            if isinstance(model_results, dict) and key in model_results:
                try:
                    rmse = float(model_results[key])
                    break
                except Exception:
                    continue
        # sometimes model_results is an object with attributes
        if rmse is None:
            try:
                rmse = float(getattr(model_results, "rmse", None) or getattr(model_results, "RMSE", None))
            except Exception:
                rmse = None

        if rmse is not None:
            # 95% CI approx using normal assumption
            margin = 1.96 * rmse
            ci_low = max(0.0, pred_val - margin)
            ci_high = max(0.0, pred_val + margin)

    return {
        "raw_prediction": pred_val,
        "predicted": predicted_int,
        "ci_low": ci_low,
        "ci_high": ci_high,
    }
