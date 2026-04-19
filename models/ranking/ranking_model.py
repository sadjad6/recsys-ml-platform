"""
RecSys ML Platform — Ranking Model.

Stage 2 of the recommendation pipeline. Uses LightGBM to score
candidate item pairs using rich user, item, and interaction features.
"""

import os
import json
import joblib
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score

MODELS_DIR = "/app/models/ranking"

class RankingModel:
    def __init__(self):
        self.model = None
        self.features = [
            "total_interactions", "total_clicks", "total_views", "total_ratings",
            "avg_rating_given", "interaction_days", 
            "total_views_item", "total_clicks_item", "click_through_rate",
            "avg_rating_received", "rating_count",
            # ALS embedding dot product would be here if computed in feature engineering
            "interaction_count", "time_since_last_interaction", "user_item_rating"
        ]

    def prepare_data(self, df: pd.DataFrame):
        """Prepare dataframe for LightGBM."""
        # Handle missing values
        X = df[self.features].fillna(0)
        y = df["label"]
        return X, y

    def train(self, training_data_path: str):
        """Train LightGBM model with cross-validation."""
        print(f"Loading training data from {training_data_path}")
        df = pd.read_parquet(training_data_path)
        
        X, y = self.prepare_data(df)
        
        # 5-fold cross validation
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        oof_preds = pd.Series(0, index=X.index)
        
        models = []
        for fold, (train_idx, val_idx) in enumerate(cv.split(X, y)):
            X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
            X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]
            
            model = lgb.LGBMClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42
            )
            
            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                eval_metric="auc"
            )
            
            models.append(model)
            oof_preds.iloc[val_idx] = model.predict_proba(X_val)[:, 1]
            
            fold_auc = roc_auc_score(y_val, oof_preds.iloc[val_idx])
            print(f"Fold {fold} AUC: {fold_auc:.4f}")
            
        overall_auc = roc_auc_score(y, oof_preds)
        print(f"Overall OOF AUC: {overall_auc:.4f}")
        
        # Train final model on all data
        self.model = lgb.LGBMClassifier(n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42)
        self.model.fit(X, y)
        
        # Save model and feature importance
        os.makedirs(MODELS_DIR, exist_ok=True)
        joblib.dump(self.model, f"{MODELS_DIR}/ranking_model.joblib")
        
        importance = dict(zip(self.features, self.model.feature_importances_.tolist()))
        with open(f"{MODELS_DIR}/feature_importance.json", "w") as f:
            json.dump(importance, f, indent=4)
            
        print("Ranking model training complete and saved.")
        return self.model

if __name__ == "__main__":
    ranker = RankingModel()
    import glob
    datasets = sorted(glob.glob("/app/data/training_datasets/v*"))
    if datasets:
        latest = datasets[-1]
        # In this environment, we assume the parquet file can be read directly by pandas
        # Usually pyarrow or fastparquet is required.
        ranker.train(f"{latest}/train.parquet")
    else:
        print("No training datasets found.")
