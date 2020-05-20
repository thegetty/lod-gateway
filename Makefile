CIRCLE_BUILD_NUM := ${CIRCLE_BUILD_NUM}
SHORT_SHA1 := $(shell git rev-parse --short HEAD)
CIRCLE_PROJECT_REPONAME := ${CIRCLE_PROJECT_REPONAME}
getty_ecr = ${ECR_ACCOUNT_URL}
ecr_prefix = jpgt-
image_name := $(ecr_prefix)$(CIRCLE_PROJECT_REPONAME)
ecr_profile = getty

define confirm_image
aws ecr list-images --repository-name $(1) --profile $(2) --region ${ECR_REGION}
endef

define setup_ecr_profile
aws configure set aws_access_key_id ${ECR_ACCESS_KEY_ID} --profile $(1)
aws configure set aws_secret_access_key ${ECR_SECRET_ACCESS_KEY} --profile $(1)
aws configure set region ${ECR_REGION} --profile $(1)
aws configure list --profile $(1)
endef

ecr_profile:
	$(call setup_ecr_profile,$(ecr_profile))

image_confirmation:
	$(call confirm_image,$(image_name),$(ecr_profile))