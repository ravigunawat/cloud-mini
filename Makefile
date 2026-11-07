.RECIPEPREFIX = >
SUBSET ?= 0

.PHONY: train up down test lint upload-model

train:
> python training/train.py --config training/config.yaml --subset $(SUBSET)

# usage: make upload-model DIR=model_out/v1 VERSION=v1
upload-model:
> python scripts/upload_model.py $(DIR) $(VERSION)

test:
> python -m pytest -q tests

lint:
> ruff check worker service training scripts tests

up:
> bash scripts/up.sh

down:
> k3d cluster delete cloudmini
