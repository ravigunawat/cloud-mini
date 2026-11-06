.RECIPEPREFIX = >
SUBSET ?= 0

train:
> python training/train.py --config training/config.yaml --subset $(SUBSET)

up:
> bash scripts/up.sh

down:
> k3d cluster delete cloudmini
