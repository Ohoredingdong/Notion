"""Preregistered two-stage challenger. Never trains on evaluation-period labels."""
from __future__ import annotations
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

RECIPE = {
    'name': 'movement_then_direction', 'version': 1,
    'movement_C': .10, 'direction_C': .10,
    'class_weight': 'balanced', 'max_iter': 1000,
    'purpose': 'Separate material-movement detection from up/down classification',
    'fixed_before_forward_evaluation': True,
    'historical_score_is_not_promotion': True,
}

class MovementThenDirection(ClassifierMixin, BaseEstimator):
    """P(flat)=1-P(move); P(up/down)=P(move)*P(up/down | move).

    This candidate may overpredict moves. Separate chronological calibration and
    the same forward precision/recall gates as all other candidates still apply.
    """
    def __init__(self, movement_C=.10, direction_C=.10):
        self.movement_C = movement_C
        self.direction_C = direction_C

    def fit(self, X, y):
        y = np.asarray(y, dtype=int)
        if set(y.tolist()) != {0, 1, 2}:
            raise ValueError('cascade_requires_all_three_classes')
        if min(np.bincount(y, minlength=3)) < 10:
            raise ValueError('cascade_class_samples_short')
        values = np.asarray(X, dtype=float)
        if values.ndim != 2 or len(values) != len(y) or not np.isfinite(values).all():
            raise ValueError('cascade_bad_training_values')
        def estimator(C):
            return make_pipeline(StandardScaler(), LogisticRegression(
                C=C, class_weight='balanced', solver='lbfgs', max_iter=1000))
        moved = y != 1
        self.movement_ = estimator(self.movement_C).fit(values, moved.astype(int))
        self.direction_ = estimator(self.direction_C).fit(values[moved], (y[moved] == 2).astype(int))
        self.classes_ = np.array([0, 1, 2])
        self.n_features_in_ = values.shape[1]
        return self

    def predict_proba(self, X):
        values = np.asarray(X, dtype=float)
        if values.ndim != 2 or values.shape[1] != self.n_features_in_ or not np.isfinite(values).all():
            raise ValueError('cascade_bad_prediction_values')
        move = self.movement_.predict_proba(values)[:, 1]
        up = self.direction_.predict_proba(values)[:, 1]
        p = np.column_stack([move*(1-up), 1-move, move*up])
        return np.maximum(p, 1e-12)/np.maximum(p, 1e-12).sum(axis=1, keepdims=True)

    def predict(self, X):
        return self.classes_[self.predict_proba(X).argmax(axis=1)]
