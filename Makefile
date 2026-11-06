.RECIPEPREFIX = >
SUBSET ?= 0

train:
> python training/train.py --config training/config.yaml --subset $(SUBSET)
