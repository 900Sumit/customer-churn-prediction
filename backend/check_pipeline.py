
import joblib

# 1. Define the saved model paths
model_paths = [
    "models/churn_lr_pipeline.joblib",
    "models/churn_catboost_pipeline.joblib"
]

# 2. Inspect fitted imputation strategies
for model_path in model_paths:
    print(f"\n--- {model_path} ---")

    # Load the trained pipeline
    model = joblib.load(model_path)

    # Get the preprocessing component
    preprocessor = model.named_steps["preprocessor"]

    # Inspect numeric and categorical transformers
    for name, transformer, columns in preprocessor.transformers_:

        # Check whether the transformer contains a fitted imputer
        if hasattr(transformer, "named_steps"):
            if "imputer" in transformer.named_steps:

                imputer = transformer.named_steps["imputer"]

                # Display imputation strategy and learned statistics
                print(f"Transformer: {name}")
                print(f"Strategy: {imputer.strategy}")
                print(f"Statistics: {imputer.statistics_}")
