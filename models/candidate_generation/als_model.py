"""
RecSys ML Platform — ALS Candidate Generation.

Stage 1 of the recommendation pipeline. Uses PySpark MLlib ALS to process
implicit feedback and generate user/item embeddings and candidates.
"""

import os
import mlflow
from pyspark.sql import SparkSession
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator

MODELS_DIR = "/app/models/candidate_generation"

MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(MLFLOW_URI)
mlflow.set_experiment("candidate-generation")

class ALSCandidateGenerator:
    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.model = None

    def train(self, training_data_path: str):
        """Train ALS model on historical interaction data."""
        df = self.spark.read.parquet(training_data_path)
        
        # ALS requires numeric IDs. In a real system, we string-indexer the user/item IDs.
        # We assume the dataset has numeric `user_index` and `item_index` or we create them.
        from pyspark.ml.feature import StringIndexer
        
        # Index users
        user_indexer = StringIndexer(inputCol="user_id", outputCol="user_index", handleInvalid="keep")
        user_indexer_model = user_indexer.fit(df)
        df = user_indexer_model.transform(df)
        
        # Index items
        item_indexer = StringIndexer(inputCol="item_id", outputCol="item_index", handleInvalid="keep")
        item_indexer_model = item_indexer.fit(df)
        df = item_indexer_model.transform(df)

        with mlflow.start_run() as run:
            als = ALS(
                rank=64,
                maxIter=15,
                regParam=0.1,
                implicitPrefs=True,
                userCol="user_index",
                itemCol="item_index",
                ratingCol="label", # binary label from prepare_training_data
                coldStartStrategy="drop"
            )
            
            mlflow.log_params({
                "rank": als.getRank(),
                "maxIter": als.getMaxIter(),
                "regParam": als.getRegParam(),
                "implicitPrefs": als.getImplicitPrefs(),
            })
            
            print("Training ALS model...")
            self.model = als.fit(df)
            
            # Log the model to MLflow
            import mlflow.spark
            mlflow.spark.log_model(self.model, "als_model")
            
            # Save models and indexers locally
            os.makedirs(MODELS_DIR, exist_ok=True)
            self.model.write().overwrite().save(f"{MODELS_DIR}/als_model")
            user_indexer_model.write().overwrite().save(f"{MODELS_DIR}/user_indexer")
            item_indexer_model.write().overwrite().save(f"{MODELS_DIR}/item_indexer")
            
            # Save embeddings locally
            self.model.userFactors.write.mode("overwrite").parquet(f"{MODELS_DIR}/embeddings/user_factors")
            self.model.itemFactors.write.mode("overwrite").parquet(f"{MODELS_DIR}/embeddings/item_factors")
            print("ALS training complete and artifacts saved.")
            
        return self.model

if __name__ == "__main__":
    spark = SparkSession.builder.appName("RecSys_ALS_Training").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    
    generator = ALSCandidateGenerator(spark)
    # Use latest training dataset if provided
    import glob
    datasets = sorted(glob.glob("/app/data/training_datasets/v*"))
    if datasets:
        latest = datasets[-1]
        generator.train(f"{latest}/train.parquet")
    else:
        print("No training datasets found.")
