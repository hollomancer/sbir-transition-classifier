"""
Model training CLI (lazy-loads heavy ML dependencies).

This script intentionally performs lazy imports of heavy libraries (xgboost, scikit-learn)
only when the `train` command is executed. If those libraries are not installed, the
command provides a clear, actionable message instead of failing at import time.

Usage:
    python scripts/train_model.py train
"""

import click
from typing import Any


@click.group()
def cli() -> None:
    """Training-related CLI commands."""
    pass


@cli.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Run checks and report environment without training.",
)
def train(dry_run: bool) -> None:
    """Trains the XGBoost scoring model (if dependencies are available)."""

    click.echo("Starting model training process...")

    # Lazy import of heavy ML libraries so the package can be used without them.
    try:
        import xgboost as xgb  # type: ignore
    except Exception as exc:  # ImportError or binary load errors
        msg = (
            "xgboost is not available in this environment.\n"
            "Model training requires xgboost (and usually scikit-learn).\n\n"
            "Options:\n"
            "  1) Install the optional dependencies locally (recommended for training):\n"
            "       pip install xgboost scikit-learn\n"
            "  2) Use a pre-built wheel for your platform or refer to the project's docs for\n"
            "     installation tips if you encounter build errors (GPU builds / compiler toolchains).\n\n"
            f"Underlying error: {exc}\n\n"
        )
        click.echo(msg)
        if dry_run:
            click.echo("Dry-run: exiting without performing training.")
            return
        # Fall back to placeholder behavior to avoid hard crash
        click.echo("Skipping actual training due to missing dependency.")
        click.echo("Model training script complete (placeholder).")
        return

    # scikit-learn is optional but commonly used for splitting and evaluation
    try:
        from sklearn.model_selection import train_test_split  # type: ignore
    except Exception as exc:
        click.echo(
            "scikit-learn is not available. You can still train with xgboost directly,\n"
            "but utilities like train_test_split will be unavailable.\n"
            f"Underlying error: {exc}\n"
        )
        if dry_run:
            click.echo("Dry-run: dependencies partially available; exiting.")
            return

    # At this point heavy deps are available — proceed with a minimal placeholder flow.
    click.echo(
        "All required ML dependencies are available. Running a minimal training flow (placeholder)."
    )

    # Placeholder logic — in a real run replace these with your data loading and training code.
    # 1) Load labeled data (user-supplied code needed here)
    click.echo("Loading labeled data (placeholder)...")
    # features_df = load_and_featurize_data()
    # labels = features_df['is_transition']
    # X = features_df.drop('is_transition', axis=1)

    # 2) Split data (if scikit-learn available)
    try:
        from sklearn.model_selection import train_test_split  # type: ignore

        # Example placeholders (replace with real data variables)
        # X_train, X_test, y_train, y_test = train_test_split(X, labels, test_size=0.2, random_state=42)
        click.echo("Data split (placeholder) — replace with real dataset.")
    except Exception:
        click.echo(
            "Skipping train/test split (scikit-learn unavailable or placeholder)."
        )

    # 3) Train XGBoost model (placeholder)
    click.echo("Training XGBoost model (placeholder)...")
    # Example (replace with real training code):
    # xgb_model = xgb.XGBClassifier(objective="binary:logistic", n_estimators=100, learning_rate=0.1)
    # xgb_model.fit(X_train, y_train)

    # 4) Evaluate & save (placeholder)
    # accuracy = xgb_model.score(X_test, y_test)
    # click.echo(f"Model accuracy (placeholder): {accuracy}")
    # xgb_model.save_model("model.xgb")

    click.echo("Model training script complete (placeholder).")
    click.echo("A trained model file 'model.xgb' would be saved in a real run.")


if __name__ == "__main__":
    cli()
