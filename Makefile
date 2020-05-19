CIRCLE_BUILD_NUM := ${CIRCLE_BUILD_NUM}
SHORT_SHA1 := $(shell git rev-parse --short HEAD)
CIRCLE_PROJECT_REPONAME := ${CIRCLE_PROJECT_REPONAME}
getty_ecr = 964273422046.dkr.ecr.us-west-2.amazonaws.com
ecr_prefix := jpgt-
image_name := $(ecr_prefix)$(CIRCLE_PROJECT_REPONAME)
dockerfile_path := .

define tag_image
docker tag \
	$(1):latest \
	$(getty_ecr)/$(image_name):$(2)-$(3)
endef

tags:
	$(call tag_image,lod-gateway-web-service,$(CIRCLE_BUILD_NUM),$(SHORT_SHA1))